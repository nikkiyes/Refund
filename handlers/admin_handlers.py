"""
Admin Handlers — Pareeksha Gurukul Refund Bot
Admin panel, request management, plan management, broadcast, analytics.
"""

import logging
import io
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery, InputFile

from config.config import States, ADMIN_GROUP_ID
from database import db
from keyboards.keyboards import (
    admin_main_menu_kb, admin_back_menu_kb, admin_plans_kb, admin_plan_actions_kb,
    admin_request_kb, admin_confirm_approve_kb, admin_confirm_decline_kb,
    admin_confirm_ban_kb, admin_send_confirmation_kb, admin_settings_kb,
    admin_admins_kb, paginate_requests_kb, request_detail_kb, search_type_kb,
)
from utils.messages import (
    admin_request_card, admin_stats_card,
    user_approved_msg, user_declined_msg, status_detail,
)

logger = logging.getLogger(__name__)
PARSE = "Markdown"

# ── In-memory state for admin actions (keyed by admin_id) ────────────────────
_admin_pending: dict[int, dict] = {}


def register_admin_handlers(bot: AsyncTeleBot):

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN GUARD
    # ──────────────────────────────────────────────────────────────────────────
    async def guard(user_id: int, call_or_msg) -> bool:
        if not await db.is_admin(user_id):
            if hasattr(call_or_msg, "id"):
                await bot.answer_callback_query(call_or_msg.id, "🚫 Not authorised!")
            else:
                await bot.send_message(call_or_msg.chat.id, "🚫 You are not an admin.")
            return False
        return True

    # ──────────────────────────────────────────────────────────────────────────
    #  /admin COMMAND
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["admin"])
    async def cmd_admin(msg: Message):
        if not await guard(msg.from_user.id, msg):
            return
        await bot.send_message(
            msg.chat.id,
            f"👑 *Admin Panel — Pareeksha Gurukul*\n\nWelcome, {msg.from_user.first_name}!\nSelect an action:",
            parse_mode=PARSE,
            reply_markup=admin_main_menu_kb(),
        )

    @bot.message_handler(commands=["stats"])
    async def cmd_stats(msg: Message):
        if not await guard(msg.from_user.id, msg):
            return
        stats = await db.get_stats()
        await bot.send_message(msg.chat.id, admin_stats_card(stats), parse_mode=PARSE, reply_markup=admin_back_menu_kb())

    @bot.message_handler(commands=["plans"])
    async def cmd_plans(msg: Message):
        if not await guard(msg.from_user.id, msg):
            return
        plans = await db.get_all_plans()
        await bot.send_message(msg.chat.id, "📚 *Manage Plans*", parse_mode=PARSE, reply_markup=admin_plans_kb(plans))

    @bot.message_handler(commands=["export"])
    async def cmd_export(msg: Message):
        if not await guard(msg.from_user.id, msg):
            return
        await _do_export(bot, msg.chat.id)

    @bot.message_handler(commands=["broadcast"])
    async def cmd_broadcast(msg: Message):
        if not await guard(msg.from_user.id, msg):
            return
        _admin_pending[msg.from_user.id] = {"action": "broadcast"}
        await db.set_session(msg.from_user.id, States.A_BROADCAST, {})
        await bot.send_message(msg.chat.id, "📢 *Broadcast Message*\n\nEnter the message to send to all users:", parse_mode=PARSE)

    @bot.message_handler(commands=["requests"])
    async def cmd_requests(msg: Message):
        if not await guard(msg.from_user.id, msg):
            return
        await bot.send_message(
            msg.chat.id,
            "📋 *View Requests*\nSelect category:",
            parse_mode=PARSE,
            reply_markup=admin_main_menu_kb(),
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN MAIN MENU CALLBACK
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_menu")
    async def cb_admin_menu(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        await bot.edit_message_text(
            f"👑 *Admin Panel — Pareeksha Gurukul*\n\nSelect an action:",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_main_menu_kb()
        )
        await bot.answer_callback_query(call.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  LIST REQUESTS WITH PAGINATION
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("admin_list:"))
    async def cb_admin_list(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        _, status, page_str = call.data.split(":")
        page = int(page_str)
        requests, total = await db.get_requests_by_status(status, page)

        if not requests:
            await bot.answer_callback_query(call.id, f"No {status} requests found.")
            return

        text = f"📋 *{status} Requests* (Page {page+1})\n{'─'*28}\n\n"
        for r in requests:
            text += (
                f"🎫 `{r['ticket_id']}`\n"
                f"👤 {r['full_name']} · 📱 {r['mobile']}\n"
                f"💰 ₹{r['refund_amount']:.0f} · {r['submitted_at'][:16]}\n\n"
            )

        kb = paginate_requests_kb(status, page, total)
        # Add per-request buttons
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        for r in requests:
            kb.add(InlineKeyboardButton(
                f"📂 {r['ticket_id']}", callback_data=f"req_detail:{r['request_id']}"
            ))

        await bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                     parse_mode=PARSE, reply_markup=kb)
        await bot.answer_callback_query(call.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  REQUEST DETAIL
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("req_detail:"))
    async def cb_req_detail(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Request not found!")
            return
        text = status_detail(dict(req))
        if req["admin_note"]:
            text += f"\n📝 *Admin Note:* {req['admin_note']}"
        await bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                     parse_mode=PARSE, reply_markup=request_detail_kb(request_id, req["status"]))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("back_to_req:"))
    async def cb_back_to_req(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Request not found!")
            return
        await bot.edit_message_text(
            admin_request_card(dict(req), req["ticket_id"]),
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_request_kb(request_id)
        )
        await bot.answer_callback_query(call.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  APPROVE
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("approve:"))
    async def cb_approve(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        _admin_pending[call.from_user.id] = {"action": "approve", "request_id": request_id, "chat_id": call.message.chat.id, "msg_id": call.message.message_id}
        await db.set_session(call.from_user.id, States.A_UTR, {"request_id": request_id})
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            call.message.chat.id,
            f"✅ *Approve Refund*\n\nPlease enter the *UTR / Reference Number* for this refund:\n\n_(Type and send)_",
            parse_mode=PARSE,
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_approve:"))
    async def cb_confirm_approve(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        pending = _admin_pending.get(call.from_user.id, {})
        utr = pending.get("utr")
        if not utr:
            await bot.answer_callback_query(call.id, "UTR not found. Start again.")
            return
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Request not found!")
            return
        await db.approve_request(request_id, utr, call.from_user.id)
        await bot.answer_callback_query(call.id, "✅ Approved!")
        await bot.edit_message_text(
            f"✅ *Refund Approved*\n\nTicket: `{req['ticket_id']}`\nUTR: `{utr}`\n\nUser will be notified.",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_send_confirmation_kb(request_id)
        )
        _admin_pending.pop(call.from_user.id, None)

    # ──────────────────────────────────────────────────────────────────────────
    #  DECLINE
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("decline:"))
    async def cb_decline(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        _admin_pending[call.from_user.id] = {"action": "decline", "request_id": request_id, "chat_id": call.message.chat.id, "msg_id": call.message.message_id}
        await db.set_session(call.from_user.id, States.A_DECLINE_REASON, {"request_id": request_id})
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            call.message.chat.id,
            "❌ *Decline Refund*\n\nPlease enter the *reason/remarks* for declining this request:",
            parse_mode=PARSE,
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_decline:"))
    async def cb_confirm_decline(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        pending = _admin_pending.get(call.from_user.id, {})
        reason = pending.get("reason")
        if not reason:
            await bot.answer_callback_query(call.id, "Reason not found. Start again.")
            return
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Request not found!")
            return
        await db.decline_request(request_id, reason, call.from_user.id)
        await bot.answer_callback_query(call.id, "❌ Declined!")

        # Notify user
        await bot.send_message(req["user_id"], user_declined_msg(reason), parse_mode=PARSE)

        await bot.edit_message_text(
            f"❌ *Refund Declined*\n\nTicket: `{req['ticket_id']}`\nReason: {reason}\n\nUser has been notified.",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_back_menu_kb()
        )
        _admin_pending.pop(call.from_user.id, None)

    # ──────────────────────────────────────────────────────────────────────────
    #  SEND CONFIRMATION TO USER (after approve)
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("send_conf:"))
    async def cb_send_conf(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Request not found!")
            return
        if req["status"] != "Approved":
            await bot.answer_callback_query(call.id, "Request not yet approved!")
            return
        await bot.send_message(
            req["user_id"],
            user_approved_msg(req["refund_amount"], req["utr_number"]),
            parse_mode=PARSE,
        )
        await bot.answer_callback_query(call.id, "✅ Confirmation sent to user!")
        await bot.edit_message_text(
            f"✅ Confirmation sent to user `{req['user_id']}` for ticket `{req['ticket_id']}`.",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_back_menu_kb()
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  ADD NOTE
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("note:"))
    async def cb_note(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        _admin_pending[call.from_user.id] = {"action": "note", "request_id": request_id}
        await db.set_session(call.from_user.id, States.A_NOTE, {"request_id": request_id})
        await bot.answer_callback_query(call.id)
        await bot.send_message(call.message.chat.id, "📝 *Add Internal Note*\n\nEnter your note:", parse_mode=PARSE)

    # ──────────────────────────────────────────────────────────────────────────
    #  VIEW SCREENSHOT
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("screenshot:"))
    async def cb_screenshot(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Not found!")
            return
        await bot.answer_callback_query(call.id)
        await bot.send_photo(
            call.message.chat.id,
            req["screenshot_file_id"],
            caption=f"🖼 Payment Screenshot\nTicket: `{req['ticket_id']}`",
            parse_mode=PARSE,
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  BAN USER
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("ban:"))
    async def cb_ban(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        request_id = int(call.data.split(":")[1])
        req = await db.get_request_by_id(request_id)
        if not req:
            await bot.answer_callback_query(call.id, "Not found!")
            return
        await bot.answer_callback_query(call.id)
        await bot.edit_message_text(
            f"🚫 *Ban User?*\n\nAre you sure you want to ban user `{req['user_id']}`?",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE,
            reply_markup=admin_confirm_ban_kb(req["user_id"], request_id)
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_ban:"))
    async def cb_confirm_ban(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        parts = call.data.split(":")
        user_id = int(parts[1])
        request_id = int(parts[2])
        await db.ban_user(user_id, call.from_user.id)
        await bot.answer_callback_query(call.id, "🚫 User banned!")
        try:
            await bot.send_message(user_id, "🚫 Your account has been restricted. Contact support for help.")
        except Exception:
            pass
        await bot.edit_message_text(
            f"🚫 User `{user_id}` has been banned.",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_back_menu_kb()
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  ANALYTICS
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
    async def cb_stats(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        stats = await db.get_stats()
        await bot.edit_message_text(
            admin_stats_card(stats), call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_back_menu_kb()
        )
        await bot.answer_callback_query(call.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  EXPORT CSV
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_export")
    async def cb_export(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        await bot.answer_callback_query(call.id, "Generating CSV...")
        await _do_export(bot, call.message.chat.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  PLANS MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_plans")
    async def cb_plans(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        plans = await db.get_all_plans()
        await bot.edit_message_text(
            "📚 *Manage Plans*\n\nSelect a plan to edit or add a new one:",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_plans_kb(plans)
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("plan_manage:"))
    async def cb_plan_manage(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        plan_id = int(call.data.split(":")[1])
        plan = await db.get_plan(plan_id)
        if not plan:
            await bot.answer_callback_query(call.id, "Plan not found!")
            return
        text = (
            f"📚 *{plan['plan_name']}*\n"
            f"💰 Original: ₹{plan['original_amount']:.0f}\n"
            f"💸 Refund: ₹{plan['refund_amount']:.0f}\n"
            f"Status: {'🟢 Active' if plan['is_active'] else '🔴 Inactive'}"
        )
        await bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE,
            reply_markup=admin_plan_actions_kb(plan_id, bool(plan["is_active"]))
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "plan_add")
    async def cb_plan_add(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        _admin_pending[call.from_user.id] = {"action": "add_plan"}
        await db.set_session(call.from_user.id, States.A_ADD_PLAN_NAME, {})
        await bot.answer_callback_query(call.id)
        await bot.send_message(call.message.chat.id, "➕ *Add New Plan*\n\nEnter plan name:", parse_mode=PARSE)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("plan_edit:"))
    async def cb_plan_edit(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        plan_id = int(call.data.split(":")[1])
        _admin_pending[call.from_user.id] = {"action": "edit_plan", "plan_id": plan_id}
        await db.set_session(call.from_user.id, States.A_EDIT_PLAN_NAME, {"plan_id": plan_id})
        await bot.answer_callback_query(call.id)
        await bot.send_message(call.message.chat.id, f"✏️ *Edit Plan*\n\nEnter new plan name:", parse_mode=PARSE)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("plan_activate:") or c.data.startswith("plan_deactivate:"))
    async def cb_plan_toggle(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        action, plan_id_str = call.data.split(":")
        plan_id = int(plan_id_str)
        activate = action == "plan_activate"
        await db.toggle_plan(plan_id, activate)
        await bot.answer_callback_query(call.id, "Plan updated!")
        plans = await db.get_all_plans()
        await bot.edit_message_text(
            "📚 *Manage Plans*", call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_plans_kb(plans)
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("plan_delete:"))
    async def cb_plan_delete(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        plan_id = int(call.data.split(":")[1])
        await db.delete_plan(plan_id)
        await bot.answer_callback_query(call.id, "Plan deleted!")
        plans = await db.get_all_plans()
        await bot.edit_message_text(
            "📚 *Manage Plans*", call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_plans_kb(plans)
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  BROADCAST
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
    async def cb_broadcast(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        _admin_pending[call.from_user.id] = {"action": "broadcast"}
        await db.set_session(call.from_user.id, States.A_BROADCAST, {})
        await bot.answer_callback_query(call.id)
        await bot.edit_message_text(
            "📢 *Broadcast Message*\n\nEnter the message to send to all users:",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE,
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  SETTINGS
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_settings")
    async def cb_settings(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        await bot.edit_message_text(
            "⚙️ *Bot Settings*\n\nSelect a setting to change:",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_settings_kb()
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("setting_"))
    async def cb_setting_edit(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        key_map = {
            "setting_welcome": ("welcome_message", States.A_WELCOME_MSG, "Welcome Message"),
            "setting_support": ("support_message", States.A_SUPPORT_MSG, "Support Message"),
            "setting_working_days": ("working_days", States.A_WORKING_DAYS, "Working Days (number)"),
        }
        cfg = key_map.get(call.data)
        if not cfg:
            return
        db_key, state, label = cfg
        _admin_pending[call.from_user.id] = {"action": "setting", "setting_key": db_key}
        await db.set_session(call.from_user.id, state, {"setting_key": db_key})
        await bot.answer_callback_query(call.id)
        await bot.send_message(call.message.chat.id, f"✏️ Enter new *{label}*:", parse_mode=PARSE)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_refund:"))
    async def cb_toggle_refund(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        value = call.data.split(":")[1]
        await db.set_setting("refund_enabled", value)
        status = "enabled 🔓" if value == "1" else "disabled 🔒"
        await bot.answer_callback_query(call.id, f"Refund requests {status}!")
        await bot.edit_message_text(
            f"⚙️ *Settings*\n\nRefund requests are now *{status}*.",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_settings_kb()
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMINS MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "admin_admins")
    async def cb_admins(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        admins = await db.get_all_admins()
        await bot.edit_message_text(
            "👥 *Manage Admins*\n\nTap an admin to remove them:",
            call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_admins_kb(admins)
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "add_admin")
    async def cb_add_admin(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        _admin_pending[call.from_user.id] = {"action": "add_admin"}
        await db.set_session(call.from_user.id, States.A_ADD_ADMIN, {})
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            call.message.chat.id,
            "➕ *Add Admin*\n\nForward a message from the user you want to add as admin, or type their Telegram ID:",
            parse_mode=PARSE,
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("remove_admin:"))
    async def cb_remove_admin(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        admin_id = int(call.data.split(":")[1])
        from config.config import ADMIN_IDS
        if admin_id in ADMIN_IDS:
            await bot.answer_callback_query(call.id, "Cannot remove super admin!")
            return
        await db.remove_admin(admin_id, call.from_user.id)
        await bot.answer_callback_query(call.id, "Admin removed!")
        admins = await db.get_all_admins()
        await bot.edit_message_text(
            "👥 *Manage Admins*", call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=admin_admins_kb(admins)
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  SEARCH
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("search:"))
    async def cb_search_type(call: CallbackQuery):
        if not await guard(call.from_user.id, call):
            return
        search_type = call.data.split(":")[1]
        _admin_pending[call.from_user.id] = {"action": "search", "search_type": search_type}
        await db.set_session(call.from_user.id, States.A_SEARCH, {"search_type": search_type})
        labels = {"ticket": "Ticket ID", "mobile": "Mobile Number", "name": "Name"}
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            call.message.chat.id,
            f"🔍 *Search by {labels[search_type]}*\n\nEnter search query:",
            parse_mode=PARSE,
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN TEXT MESSAGE HANDLER
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(content_types=["text"])
    async def handle_admin_text(msg: Message):
        """Intercepts admin FSM states."""
        if not await db.is_admin(msg.from_user.id):
            return  # Fall through to user handler (already registered)

        state, data = await db.get_session(msg.from_user.id)
        pending = _admin_pending.get(msg.from_user.id, {})

        if state == States.A_UTR:
            utr = msg.text.strip()
            if not utr:
                await bot.send_message(msg.chat.id, "❗ Please enter a valid UTR number.")
                return
            request_id = data.get("request_id") or pending.get("request_id")
            _admin_pending[msg.from_user.id]["utr"] = utr
            await db.set_session(msg.from_user.id, "idle", {})
            await bot.send_message(
                msg.chat.id,
                f"✅ UTR `{utr}` received.\n\nConfirm approval?",
                parse_mode=PARSE,
                reply_markup=admin_confirm_approve_kb(request_id),
            )

        elif state == States.A_DECLINE_REASON:
            reason = msg.text.strip()
            if not reason:
                await bot.send_message(msg.chat.id, "❗ Please enter a reason.")
                return
            request_id = data.get("request_id") or pending.get("request_id")
            _admin_pending[msg.from_user.id]["reason"] = reason
            await db.set_session(msg.from_user.id, "idle", {})
            await bot.send_message(
                msg.chat.id,
                f"❌ Reason: _{reason}_\n\nConfirm decline?",
                parse_mode=PARSE,
                reply_markup=admin_confirm_decline_kb(request_id),
            )

        elif state == States.A_NOTE:
            note = msg.text.strip()
            request_id = data.get("request_id") or pending.get("request_id")
            await db.set_admin_note(request_id, note, msg.from_user.id)
            await db.set_session(msg.from_user.id, "idle", {})
            await bot.send_message(msg.chat.id, "📝 Note saved!", reply_markup=admin_back_menu_kb())
            _admin_pending.pop(msg.from_user.id, None)

        elif state == States.A_BROADCAST:
            broadcast_text = msg.text.strip()
            if not broadcast_text:
                await bot.send_message(msg.chat.id, "❗ Message cannot be empty.")
                return
            await db.set_session(msg.from_user.id, "idle", {})
            _admin_pending.pop(msg.from_user.id, None)
            users = await db.get_all_users()
            sent = 0
            failed = 0
            progress = await bot.send_message(msg.chat.id, f"📢 Broadcasting to {len(users)} users...")
            for uid in users:
                try:
                    await bot.send_message(uid, broadcast_text, parse_mode=PARSE)
                    sent += 1
                except Exception:
                    failed += 1
            await bot.edit_message_text(
                f"📢 *Broadcast Complete*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
                msg.chat.id, progress.message_id, parse_mode=PARSE, reply_markup=admin_back_menu_kb()
            )

        elif state == States.A_SEARCH:
            query = msg.text.strip()
            results = await db.search_requests(query)
            await db.set_session(msg.from_user.id, "idle", {})
            if not results:
                await bot.send_message(msg.chat.id, "🔍 No results found.", reply_markup=admin_back_menu_kb())
                return
            text = f"🔍 *Search Results* ({len(results)} found)\n{'─'*28}\n\n"
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup()
            for r in results:
                text += f"🎫 `{r['ticket_id']}` · {r['status']}\n👤 {r['full_name']} · 📱 {r['mobile']}\n\n"
                kb.add(InlineKeyboardButton(f"📂 {r['ticket_id']}", callback_data=f"req_detail:{r['request_id']}"))
            kb.row(InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu"))
            await bot.send_message(msg.chat.id, text, parse_mode=PARSE, reply_markup=kb)

        elif state == States.A_ADD_PLAN_NAME:
            data["plan_name"] = msg.text.strip()
            await db.set_session(msg.from_user.id, States.A_ADD_PLAN_ORIG, data)
            await bot.send_message(msg.chat.id, f"💰 Enter *original amount* for _{data['plan_name']}_:", parse_mode=PARSE)

        elif state == States.A_ADD_PLAN_ORIG:
            try:
                data["original_amount"] = float(msg.text.strip())
            except ValueError:
                await bot.send_message(msg.chat.id, "❗ Enter a valid number.")
                return
            await db.set_session(msg.from_user.id, States.A_ADD_PLAN_REF, data)
            await bot.send_message(msg.chat.id, "💸 Enter *refundable amount*:", parse_mode=PARSE)

        elif state == States.A_ADD_PLAN_REF:
            try:
                data["refund_amount"] = float(msg.text.strip())
            except ValueError:
                await bot.send_message(msg.chat.id, "❗ Enter a valid number.")
                return
            plan_id = await db.add_plan(data["plan_name"], data["original_amount"], data["refund_amount"])
            await db.set_session(msg.from_user.id, "idle", {})
            _admin_pending.pop(msg.from_user.id, None)
            await bot.send_message(
                msg.chat.id,
                f"✅ Plan *{data['plan_name']}* added!\n💰 ₹{data['original_amount']:.0f} → 💸 ₹{data['refund_amount']:.0f}",
                parse_mode=PARSE, reply_markup=admin_back_menu_kb()
            )

        elif state == States.A_EDIT_PLAN_NAME:
            data["new_name"] = msg.text.strip()
            await db.set_session(msg.from_user.id, States.A_EDIT_PLAN_ORIG, data)
            await bot.send_message(msg.chat.id, "💰 Enter new *original amount*:", parse_mode=PARSE)

        elif state == States.A_EDIT_PLAN_ORIG:
            try:
                data["original_amount"] = float(msg.text.strip())
            except ValueError:
                await bot.send_message(msg.chat.id, "❗ Enter a valid number.")
                return
            await db.set_session(msg.from_user.id, States.A_EDIT_PLAN_REF, data)
            await bot.send_message(msg.chat.id, "💸 Enter new *refundable amount*:", parse_mode=PARSE)

        elif state == States.A_EDIT_PLAN_REF:
            try:
                data["refund_amount"] = float(msg.text.strip())
            except ValueError:
                await bot.send_message(msg.chat.id, "❗ Enter a valid number.")
                return
            plan_id = data.get("plan_id") or pending.get("plan_id")
            await db.update_plan(plan_id, data["new_name"], data["original_amount"], data["refund_amount"])
            await db.set_session(msg.from_user.id, "idle", {})
            _admin_pending.pop(msg.from_user.id, None)
            await bot.send_message(
                msg.chat.id,
                f"✅ Plan updated to *{data['new_name']}*!",
                parse_mode=PARSE, reply_markup=admin_back_menu_kb()
            )

        elif state in (States.A_WELCOME_MSG, States.A_SUPPORT_MSG, States.A_WORKING_DAYS):
            setting_key = data.get("setting_key") or pending.get("setting_key")
            await db.set_setting(setting_key, msg.text.strip())
            await db.set_session(msg.from_user.id, "idle", {})
            _admin_pending.pop(msg.from_user.id, None)
            await bot.send_message(msg.chat.id, "✅ Setting updated!", reply_markup=admin_back_menu_kb())

        elif state == States.A_ADD_ADMIN:
            new_admin_id_str = msg.text.strip()
            try:
                new_admin_id = int(new_admin_id_str)
            except ValueError:
                await bot.send_message(msg.chat.id, "❗ Invalid Telegram ID. Enter a number.")
                return
            await db.add_admin(new_admin_id, "", msg.from_user.id)
            await db.set_session(msg.from_user.id, "idle", {})
            _admin_pending.pop(msg.from_user.id, None)
            await bot.send_message(
                msg.chat.id,
                f"✅ Admin `{new_admin_id}` added!",
                parse_mode=PARSE, reply_markup=admin_back_menu_kb()
            )


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFY ADMIN GROUP — Called after user submits request
# ══════════════════════════════════════════════════════════════════════════════
async def notify_admin_group(bot: AsyncTeleBot, request_id: int, data: dict, ticket_id: str, tg_user):
    """Send new refund request details to admin group."""
    if not ADMIN_GROUP_ID:
        logger.warning("ADMIN_GROUP_ID not set — skipping admin notification")
        return

    card_text = admin_request_card(data, ticket_id)
    try:
        # Send text card
        card_msg = await bot.send_message(
            ADMIN_GROUP_ID, card_text, parse_mode="Markdown",
            reply_markup=admin_request_kb(request_id)
        )
        # Store admin message ID for later editing
        await db.set_admin_msg_id(request_id, card_msg.message_id)

        # Send screenshot separately
        await bot.send_photo(
            ADMIN_GROUP_ID,
            data["screenshot_file_id"],
            caption=f"📸 Payment Screenshot\n🎫 Ticket: `{ticket_id}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Failed to notify admin group: %s", e)


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _do_export(bot: AsyncTeleBot, chat_id: int):
    csv_data = await db.export_csv()
    file_bytes = csv_data.encode("utf-8")
    file_obj = io.BytesIO(file_bytes)
    file_obj.name = f"refunds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    await bot.send_document(
        chat_id,
        InputFile(file_obj, file_name=file_obj.name),
        caption="📥 *Refund Requests Export*",
        parse_mode="Markdown",
    )

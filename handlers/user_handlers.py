"""
User Handlers — Pareeksha Gurukul Refund Bot
Handles all user-facing commands and conversation steps.
"""

import logging
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery

from config.config import States, UPI_PATTERN
from database import db
from keyboards.keyboards import (
    main_menu_kb, back_cancel_kb, cancel_home_kb,
    plan_selection_kb, confirm_kb, back_home_kb, status_list_kb,
)
from utils.messages import (
    welcome_text, STEP_NAME, STEP_MOBILE, STEP_PLAN, STEP_SCREENSHOT,
    STEP_UPI, INVALID_NAME, INVALID_MOBILE, INVALID_UPI, INVALID_IMAGE,
    confirmation_preview, submission_success, status_detail,
    CANCELLED, ALREADY_HAS_REQUEST, REFUND_DISABLED, BANNED_MSG, HELP_TEXT,
)

logger = logging.getLogger(__name__)

PARSE = "Markdown"


def register_user_handlers(bot: AsyncTeleBot):

    # ──────────────────────────────────────────────────────────────────────────
    #  /start
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["start", "help"])
    async def cmd_start(msg: Message):
        user = msg.from_user
        await db.upsert_user(user.id, user.username or "", user.first_name or "", user.last_name or "")
        await db.clear_session(user.id)

        if await db.is_banned(user.id):
            await bot.send_message(msg.chat.id, BANNED_MSG, parse_mode=PARSE)
            return

        text = await welcome_text()
        await bot.send_message(msg.chat.id, text, parse_mode=PARSE, reply_markup=main_menu_kb())

    # ──────────────────────────────────────────────────────────────────────────
    #  /cancel
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["cancel"])
    async def cmd_cancel(msg: Message):
        await db.clear_session(msg.from_user.id)
        await bot.send_message(msg.chat.id, CANCELLED, parse_mode=PARSE, reply_markup=main_menu_kb())

    # ──────────────────────────────────────────────────────────────────────────
    #  /status — user checks their own requests
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["status"])
    async def cmd_status(msg: Message):
        await _show_status(msg.chat.id, msg.from_user.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  /refund — alias to start refund flow
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["refund"])
    async def cmd_refund(msg: Message):
        await _begin_refund(bot, msg.chat.id, msg.from_user.id)

    # ──────────────────────────────────────────────────────────────────────────
    #  CALLBACK QUERIES
    # ──────────────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "home")
    async def cb_home(call: CallbackQuery):
        await db.clear_session(call.from_user.id)
        text = await welcome_text()
        await bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=main_menu_kb()
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "refund_start")
    async def cb_refund_start(call: CallbackQuery):
        await bot.answer_callback_query(call.id)
        await _begin_refund(bot, call.message.chat.id, call.from_user.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data == "check_status")
    async def cb_check_status(call: CallbackQuery):
        await bot.answer_callback_query(call.id)
        await _show_status(call.message.chat.id, call.from_user.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data == "help")
    async def cb_help(call: CallbackQuery):
        await bot.answer_callback_query(call.id)
        await bot.edit_message_text(
            HELP_TEXT, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=back_home_kb("home")
        )

    @bot.callback_query_handler(func=lambda c: c.data == "cancel")
    async def cb_cancel(call: CallbackQuery):
        await bot.answer_callback_query(call.id, "Cancelled")
        await db.clear_session(call.from_user.id)
        await bot.edit_message_text(
            CANCELLED, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=main_menu_kb()
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("plan:"))
    async def cb_plan_selected(call: CallbackQuery):
        plan_id = int(call.data.split(":")[1])
        plan = await db.get_plan(plan_id)
        if not plan:
            await bot.answer_callback_query(call.id, "Plan not found!")
            return
        await bot.answer_callback_query(call.id, f"✅ {plan['plan_name']} selected")

        state, data = await db.get_session(call.from_user.id)
        data.update({
            "plan_id": plan_id,
            "plan_name": plan["plan_name"],
            "original_amount": plan["original_amount"],
            "refund_amount": plan["refund_amount"],
        })
        await db.set_session(call.from_user.id, States.SCREENSHOT, data)

        await bot.edit_message_text(
            STEP_SCREENSHOT, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=back_cancel_kb("back_to_plan")
        )

    @bot.callback_query_handler(func=lambda c: c.data == "back_to_plan")
    async def cb_back_plan(call: CallbackQuery):
        await bot.answer_callback_query(call.id)
        state, data = await db.get_session(call.from_user.id)
        await db.set_session(call.from_user.id, States.PLAN, data)
        kb = await plan_selection_kb()
        await bot.edit_message_text(
            STEP_PLAN, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=kb
        )

    @bot.callback_query_handler(func=lambda c: c.data == "back")
    async def cb_back(call: CallbackQuery):
        await bot.answer_callback_query(call.id)
        state, data = await db.get_session(call.from_user.id)
        await _go_back(bot, call.message.chat.id, call.from_user.id, state, data, call.message.message_id)

    @bot.callback_query_handler(func=lambda c: c.data == "submit_confirm")
    async def cb_submit_confirm(call: CallbackQuery):
        await bot.answer_callback_query(call.id, "Submitting...")
        state, data = await db.get_session(call.from_user.id)

        if not all(k in data for k in ("full_name", "mobile", "plan_id", "upi_id", "screenshot_file_id")):
            await bot.answer_callback_query(call.id, "⚠️ Session expired, please start again.")
            await db.clear_session(call.from_user.id)
            return

        # Check for duplicate active request
        existing = await db.get_active_request_for_user(call.from_user.id)
        if existing:
            await bot.edit_message_text(
                ALREADY_HAS_REQUEST, call.message.chat.id, call.message.message_id,
                parse_mode=PARSE, reply_markup=main_menu_kb()
            )
            return

        request_id, ticket_id = await db.create_request(
            user_id=call.from_user.id,
            full_name=data["full_name"],
            mobile=data["mobile"],
            plan_id=data["plan_id"],
            plan_name=data["plan_name"],
            original_amount=data["original_amount"],
            refund_amount=data["refund_amount"],
            upi_id=data["upi_id"],
            screenshot_file_id=data["screenshot_file_id"],
        )
        await db.clear_session(call.from_user.id)

        # Success message to user
        success_text = await submission_success(data["refund_amount"], ticket_id)
        await bot.edit_message_text(
            success_text, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=main_menu_kb()
        )

        # Notify admin group
        from handlers.admin_handlers import notify_admin_group
        await notify_admin_group(bot, request_id, data, ticket_id, call.from_user)

    @bot.callback_query_handler(func=lambda c: c.data == "edit_details")
    async def cb_edit_details(call: CallbackQuery):
        await bot.answer_callback_query(call.id)
        state, data = await db.get_session(call.from_user.id)
        await db.set_session(call.from_user.id, States.NAME, data)
        await bot.edit_message_text(
            STEP_NAME, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=cancel_home_kb()
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("view_ticket:"))
    async def cb_view_ticket(call: CallbackQuery):
        ticket_id = call.data.split(":")[1]
        req = await db.get_request_by_ticket(ticket_id)
        if not req or req["user_id"] != call.from_user.id:
            await bot.answer_callback_query(call.id, "Ticket not found!")
            return
        await bot.answer_callback_query(call.id)
        text = status_detail(dict(req))
        await bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode=PARSE, reply_markup=back_home_kb("check_status")
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  TEXT MESSAGE ROUTER — FSM
    # ──────────────────────────────────────────────────────────────────────────
    @bot.message_handler(content_types=["text", "photo"])
    async def handle_text_and_photo(msg: Message):
        user_id = msg.from_user.id

        if await db.is_banned(user_id):
            await bot.send_message(msg.chat.id, BANNED_MSG, parse_mode=PARSE)
            return

        state, data = await db.get_session(user_id)

        if state == States.NAME:
            await _handle_name(bot, msg, data)

        elif state == States.MOBILE:
            await _handle_mobile(bot, msg, data)

        elif state == States.SCREENSHOT:
            await _handle_screenshot(bot, msg, data)

        elif state == States.UPI:
            await _handle_upi(bot, msg, data)

        else:
            # Unknown state — show main menu
            text = await welcome_text()
            await bot.send_message(msg.chat.id, text, parse_mode=PARSE, reply_markup=main_menu_kb())


# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════
async def _begin_refund(bot: AsyncTeleBot, chat_id: int, user_id: int, msg_id: int = None):
    """Check pre-conditions then start refund flow."""
    if await db.is_banned(user_id):
        await bot.send_message(chat_id, BANNED_MSG, parse_mode=PARSE)
        return

    refund_enabled = await db.get_setting("refund_enabled")
    if refund_enabled == "0":
        text = REFUND_DISABLED
        if msg_id:
            await bot.edit_message_text(text, chat_id, msg_id, parse_mode=PARSE, reply_markup=main_menu_kb())
        else:
            await bot.send_message(chat_id, text, parse_mode=PARSE, reply_markup=main_menu_kb())
        return

    existing = await db.get_active_request_for_user(user_id)
    if existing:
        text = ALREADY_HAS_REQUEST
        if msg_id:
            await bot.edit_message_text(text, chat_id, msg_id, parse_mode=PARSE, reply_markup=main_menu_kb())
        else:
            await bot.send_message(chat_id, text, parse_mode=PARSE, reply_markup=main_menu_kb())
        return

    await db.set_session(user_id, States.NAME, {})
    if msg_id:
        await bot.edit_message_text(STEP_NAME, chat_id, msg_id, parse_mode=PARSE, reply_markup=cancel_home_kb())
    else:
        await bot.send_message(chat_id, STEP_NAME, parse_mode=PARSE, reply_markup=cancel_home_kb())


async def _handle_name(bot: AsyncTeleBot, msg: Message, data: dict):
    name = (msg.text or "").strip()
    if len(name) < 3:
        await bot.send_message(msg.chat.id, INVALID_NAME, parse_mode=PARSE, reply_markup=cancel_home_kb())
        return
    data["full_name"] = name
    await db.set_session(msg.from_user.id, States.MOBILE, data)
    await bot.send_message(msg.chat.id, STEP_MOBILE, parse_mode=PARSE, reply_markup=cancel_home_kb())


async def _handle_mobile(bot: AsyncTeleBot, msg: Message, data: dict):
    mobile = (msg.text or "").strip()
    if not mobile.isdigit() or len(mobile) != 10:
        await bot.send_message(msg.chat.id, INVALID_MOBILE, parse_mode=PARSE, reply_markup=cancel_home_kb())
        return
    data["mobile"] = mobile
    await db.set_session(msg.from_user.id, States.PLAN, data)
    kb = await plan_selection_kb()
    await bot.send_message(msg.chat.id, STEP_PLAN, parse_mode=PARSE, reply_markup=kb)


async def _handle_screenshot(bot: AsyncTeleBot, msg: Message, data: dict):
    if not msg.photo:
        await bot.send_message(msg.chat.id, INVALID_IMAGE, parse_mode=PARSE, reply_markup=back_cancel_kb("back_to_plan"))
        return
    file_id = msg.photo[-1].file_id  # largest resolution
    data["screenshot_file_id"] = file_id
    await db.set_session(msg.from_user.id, States.UPI, data)
    await bot.send_message(msg.chat.id, STEP_UPI, parse_mode=PARSE, reply_markup=cancel_home_kb())


async def _handle_upi(bot: AsyncTeleBot, msg: Message, data: dict):
    upi = (msg.text or "").strip()
    if not UPI_PATTERN.match(upi):
        await bot.send_message(msg.chat.id, INVALID_UPI, parse_mode=PARSE, reply_markup=cancel_home_kb())
        return
    data["upi_id"] = upi
    await db.set_session(msg.from_user.id, States.CONFIRM, data)
    preview = confirmation_preview(data)
    await bot.send_message(msg.chat.id, preview, parse_mode=PARSE, reply_markup=confirm_kb())


async def _show_status(bot_or_chat, chat_id: int, user_id: int, msg_id: int = None):
    """Show user's refund requests."""
    if isinstance(bot_or_chat, AsyncTeleBot):
        bot = bot_or_chat
    else:
        bot = bot_or_chat

    # Fetch user's last 5 requests
    from database.db import get_db
    async with await get_db() as conn:
        import aiosqlite
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM refund_requests WHERE user_id=? ORDER BY submitted_at DESC LIMIT 5",
            (user_id,)
        )
        requests = await cur.fetchall()

    if not requests:
        text = "📋 *No Refund Requests Found*\n\nYou haven't submitted any refund requests yet."
        kb = main_menu_kb()
        if msg_id:
            await bot.edit_message_text(text, chat_id, msg_id, parse_mode=PARSE, reply_markup=kb)
        else:
            await bot.send_message(chat_id, text, parse_mode=PARSE, reply_markup=kb)
        return

    text = "📋 *Your Refund Requests*\n\nTap a request to view details:"
    kb = status_list_kb(requests)
    if msg_id:
        await bot.edit_message_text(text, chat_id, msg_id, parse_mode=PARSE, reply_markup=kb)
    else:
        await bot.send_message(chat_id, text, parse_mode=PARSE, reply_markup=kb)


async def _go_back(bot: AsyncTeleBot, chat_id: int, user_id: int, current_state: str, data: dict, msg_id: int = None):
    """Navigate backwards through the flow."""
    transitions = {
        States.MOBILE: (States.NAME, STEP_NAME, cancel_home_kb()),
        States.PLAN: (States.MOBILE, STEP_MOBILE, cancel_home_kb()),
        States.SCREENSHOT: (States.PLAN, None, None),   # plan is callback-based
        States.UPI: (States.SCREENSHOT, STEP_SCREENSHOT, back_cancel_kb("back_to_plan")),
        States.CONFIRM: (States.UPI, STEP_UPI, cancel_home_kb()),
    }
    if current_state not in transitions:
        text = await welcome_text()
        await db.clear_session(user_id)
        if msg_id:
            await bot.edit_message_text(text, chat_id, msg_id, parse_mode=PARSE, reply_markup=main_menu_kb())
        return

    new_state, text, kb = transitions[current_state]

    if current_state == States.SCREENSHOT:
        # Go back to plan selection
        await db.set_session(user_id, States.PLAN, data)
        kb2 = await plan_selection_kb()
        if msg_id:
            await bot.edit_message_text(STEP_PLAN, chat_id, msg_id, parse_mode=PARSE, reply_markup=kb2)
        return

    await db.set_session(user_id, new_state, data)
    if msg_id:
        await bot.edit_message_text(text, chat_id, msg_id, parse_mode=PARSE, reply_markup=kb)
    else:
        await bot.send_message(chat_id, text, parse_mode=PARSE, reply_markup=kb)

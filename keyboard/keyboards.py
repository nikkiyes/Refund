"""
Keyboard Builders — Pareeksha Gurukul Refund Bot
All InlineKeyboardMarkup and ReplyKeyboardMarkup builders live here.
"""

from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from database.db import get_active_plans


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _inline(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Quick builder: pass lists of (text, callback_data) tuples per row."""
    kb = InlineKeyboardMarkup()
    for row in rows:
        kb.row(*[InlineKeyboardButton(text=t, callback_data=c) for t, c in row])
    return kb


def _reply(*labels: str, one_time=False, resize=True) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=resize, one_time_keyboard=one_time)
    for label in labels:
        kb.add(KeyboardButton(label))
    return kb


# ══════════════════════════════════════════════════════════════════════════════
#  USER MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════
def main_menu_kb() -> InlineKeyboardMarkup:
    return _inline(
        [("💸 Apply for Refund", "refund_start")],
        [("🔍 Check Refund Status", "check_status")],
        [("🆘 Help & Support", "help")],
    )


def back_cancel_kb(back_cb: str = "back") -> InlineKeyboardMarkup:
    return _inline(
        [("🔙 Back", back_cb), ("❌ Cancel", "cancel")],
        [("🏠 Home", "home")],
    )


def cancel_home_kb() -> InlineKeyboardMarkup:
    return _inline(
        [("❌ Cancel", "cancel"), ("🏠 Home", "home")],
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return _inline(
        [("✅ Confirm & Submit", "submit_confirm")],
        [("✏️ Edit Details", "edit_details"), ("❌ Cancel", "cancel")],
    )


def status_list_kb(requests: list) -> InlineKeyboardMarkup:
    """Show user's recent requests as buttons."""
    kb = InlineKeyboardMarkup()
    for r in requests[:5]:
        status_icon = {"Pending": "⏳", "Approved": "✅", "Declined": "❌", "Processing": "🔄"}.get(r["status"], "📋")
        kb.add(InlineKeyboardButton(
            f"{status_icon} {r['ticket_id']} — {r['status']}",
            callback_data=f"view_ticket:{r['ticket_id']}",
        ))
    kb.row(InlineKeyboardButton("🏠 Home", callback_data="home"))
    return kb


def back_home_kb(back_cb: str = "back") -> InlineKeyboardMarkup:
    return _inline(
        [("🔙 Back", back_cb), ("🏠 Home", "home")],
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PLAN SELECTION
# ══════════════════════════════════════════════════════════════════════════════
async def plan_selection_kb() -> InlineKeyboardMarkup:
    plans = await get_active_plans()
    kb = InlineKeyboardMarkup()
    for plan in plans:
        kb.add(InlineKeyboardButton(
            f"📚 {plan['plan_name']}  —  ₹{plan['original_amount']:.0f}",
            callback_data=f"plan:{plan['plan_id']}",
        ))
    kb.row(
        InlineKeyboardButton("🔙 Back", callback_data="back"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
    )
    return kb


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN — REQUEST ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
def admin_request_kb(request_id: int) -> InlineKeyboardMarkup:
    rid = str(request_id)
    return _inline(
        [("✅ Approve Refund", f"approve:{rid}"), ("❌ Decline Refund", f"decline:{rid}")],
        [("📝 Add Note", f"note:{rid}"), ("🚫 Ban User", f"ban:{rid}")],
        [("🖼 View Screenshot", f"screenshot:{rid}")],
    )


def admin_confirm_approve_kb(request_id: int) -> InlineKeyboardMarkup:
    rid = str(request_id)
    return _inline(
        [("✅ Yes, Approve", f"confirm_approve:{rid}"), ("🔙 Back", f"back_to_req:{rid}")],
    )


def admin_confirm_decline_kb(request_id: int) -> InlineKeyboardMarkup:
    rid = str(request_id)
    return _inline(
        [("❌ Yes, Decline", f"confirm_decline:{rid}"), ("🔙 Back", f"back_to_req:{rid}")],
    )


def admin_confirm_ban_kb(user_id: int, request_id: int) -> InlineKeyboardMarkup:
    return _inline(
        [("🚫 Yes, Ban User", f"confirm_ban:{user_id}:{request_id}"),
         ("🔙 Cancel", f"back_to_req:{request_id}")],
    )


def admin_send_confirmation_kb(request_id: int) -> InlineKeyboardMarkup:
    return _inline(
        [("📤 Send Refund Confirmation to User", f"send_conf:{request_id}")],
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL MENU
# ══════════════════════════════════════════════════════════════════════════════
def admin_main_menu_kb() -> InlineKeyboardMarkup:
    return _inline(
        [("⏳ Pending Requests", "admin_list:Pending:0"),
         ("✅ Approved Requests", "admin_list:Approved:0")],
        [("❌ Declined Requests", "admin_list:Declined:0"),
         ("🔄 Processing", "admin_list:Processing:0")],
        [("📚 Manage Plans", "admin_plans")],
        [("📊 Analytics", "admin_stats"), ("📢 Broadcast", "admin_broadcast")],
        [("📥 Export CSV", "admin_export"), ("⚙️ Settings", "admin_settings")],
        [("👥 Manage Admins", "admin_admins")],
    )


def admin_back_menu_kb() -> InlineKeyboardMarkup:
    return _inline([("🔙 Admin Menu", "admin_menu")])


def admin_plans_kb(plans: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("➕ Add Plan", callback_data="plan_add"),
    )
    for p in plans:
        status = "🟢" if p["is_active"] else "🔴"
        kb.add(InlineKeyboardButton(
            f"{status} {p['plan_name']} — ₹{p['original_amount']:.0f} / Refund ₹{p['refund_amount']:.0f}",
            callback_data=f"plan_manage:{p['plan_id']}",
        ))
    kb.row(InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu"))
    return kb


def admin_plan_actions_kb(plan_id: int, is_active: bool) -> InlineKeyboardMarkup:
    pid = str(plan_id)
    toggle_text = "🔴 Deactivate" if is_active else "🟢 Activate"
    toggle_cb = f"plan_deactivate:{pid}" if is_active else f"plan_activate:{pid}"
    return _inline(
        [("✏️ Edit Plan", f"plan_edit:{pid}"), (toggle_text, toggle_cb)],
        [("🗑️ Delete Plan", f"plan_delete:{pid}")],
        [("🔙 Back to Plans", "admin_plans")],
    )


def admin_settings_kb() -> InlineKeyboardMarkup:
    return _inline(
        [("📝 Welcome Message", "setting_welcome"), ("🆘 Support Message", "setting_support")],
        [("📅 Working Days Text", "setting_working_days")],
        [("🔓 Enable Refunds", "toggle_refund:1"), ("🔒 Disable Refunds", "toggle_refund:0")],
        [("🔙 Admin Menu", "admin_menu")],
    )


def admin_admins_kb(admins: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Add Admin", callback_data="add_admin"))
    for a in admins:
        uname = a["username"] or str(a["admin_id"])
        kb.add(InlineKeyboardButton(
            f"👤 {uname}", callback_data=f"remove_admin:{a['admin_id']}"
        ))
    kb.row(InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu"))
    return kb


def paginate_requests_kb(status: str, page: int, total: int, per_page: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_list:{status}:{page-1}"))
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_list:{status}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(
        InlineKeyboardButton("🔄 Refresh", callback_data=f"admin_list:{status}:{page}"),
        InlineKeyboardButton("🔙 Menu", callback_data="admin_menu"),
    )
    return kb


def request_detail_kb(request_id: int, status: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    rid = str(request_id)
    if status == "Pending":
        kb.row(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{rid}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline:{rid}"),
        )
    kb.row(
        InlineKeyboardButton("📝 Add Note", callback_data=f"note:{rid}"),
        InlineKeyboardButton("🖼 Screenshot", callback_data=f"screenshot:{rid}"),
    )
    kb.row(InlineKeyboardButton("🔙 Back", callback_data="admin_menu"))
    return kb


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def search_type_kb() -> InlineKeyboardMarkup:
    return _inline(
        [("🎫 By Ticket ID", "search:ticket"), ("📱 By Mobile", "search:mobile")],
        [("👤 By Name", "search:name")],
        [("🔙 Admin Menu", "admin_menu")],
    )

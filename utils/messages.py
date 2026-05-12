"""
Message Templates — Pareeksha Gurukul Refund Bot
All bot messages are defined here for easy editing without touching logic.
"""

from database.db import get_setting

LOGO = "🎓"
BRAND = "Pareeksha Gurukul"


# ── Helpers ───────────────────────────────────────────────────────────────────
def md_escape(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def bold(text: str) -> str:
    return f"*{text}*"


def mono(text: str) -> str:
    return f"`{text}`"


# ── Welcome / Start ───────────────────────────────────────────────────────────
async def welcome_text() -> str:
    custom = await get_setting("welcome_message")
    return custom or (
        f"{LOGO} *Welcome to {BRAND} Refund Support*\n\n"
        "We're here to help you with your refund requests.\n"
        "Our team processes refunds after careful verification.\n\n"
        "Please select an option below:"
    )


# ── User Flow Steps ───────────────────────────────────────────────────────────
STEP_NAME = (
    "📝 *Step 1 of 5 — Full Name*\n\n"
    "Please enter your *full name* as registered in our app.\n\n"
    "_Minimum 3 characters required._"
)

STEP_MOBILE = (
    "📱 *Step 2 of 5 — Mobile Number*\n\n"
    "Enter your *registered mobile number* used on the Pareeksha Gurukul app.\n\n"
    "_Enter 10-digit number only._"
)

STEP_PLAN = (
    "📚 *Step 3 of 5 — Select Your Plan*\n\n"
    "Choose the plan you purchased for which you are requesting a refund:"
)

STEP_SCREENSHOT = (
    "📸 *Step 4 of 5 — Payment Screenshot*\n\n"
    "Please upload your *payment screenshot* as proof of purchase.\n\n"
    "_Only image files are accepted._"
)

STEP_UPI = (
    "💳 *Step 5 of 5 — UPI ID*\n\n"
    "Enter your *UPI ID* where the refund should be credited.\n\n"
    "_Examples:_ `name@paytm` · `9876543210@ybl` · `user@okicici`"
)

INVALID_NAME = "❗ *Invalid Name*\n\nPlease enter a valid name with at least 3 characters."
INVALID_MOBILE = "❗ *Invalid Mobile Number*\n\nPlease enter a valid 10-digit mobile number."
INVALID_UPI = (
    "❗ *Invalid UPI ID*\n\n"
    "Please enter a valid UPI ID.\n"
    "_Example:_ `name@paytm` or `9876543210@ybl`"
)
INVALID_IMAGE = "❗ *Invalid File*\n\nPlease upload a valid *image file* (JPEG or PNG)."


def confirmation_preview(data: dict) -> str:
    return (
        f"✅ *Review Your Refund Request*\n"
        f"{'─' * 30}\n"
        f"👤 *Name:* {data['full_name']}\n"
        f"📱 *Mobile:* {data['mobile']}\n"
        f"📚 *Plan:* {data['plan_name']}\n"
        f"💰 *Original Amount:* ₹{data['original_amount']:.0f}\n"
        f"💸 *Refund Amount:* ₹{data['refund_amount']:.0f}\n"
        f"💳 *UPI ID:* `{data['upi_id']}`\n"
        f"{'─' * 30}\n\n"
        f"Please confirm to submit your request."
    )


async def submission_success(refund_amount: float, ticket_id: str) -> str:
    days = await get_setting("working_days") or "7"
    footer = await get_setting("footer_message") or f"Thank you,\n{BRAND} Support Team 🎓"
    return (
        f"🎉 *Refund Request Submitted Successfully!*\n"
        f"{'─' * 30}\n\n"
        f"Your refund request has been successfully submitted.\n\n"
        f"🎫 *Ticket ID:* `{ticket_id}`\n\n"
        f"Our technical team will verify your details and payment information.\n\n"
        f"⚠️ Refund will be processed after deduction of applicable platform charges and GST.\n\n"
        f"✅ *Approved Refund Amount:* ₹{refund_amount:.0f}\n\n"
        f"⏱ Amount will be credited within *{days} working days* after successful verification.\n\n"
        f"{'─' * 30}\n"
        f"{footer}"
    )


def user_approved_msg(refund_amount: float, utr: str) -> str:
    return (
        f"✅ *Refund Successfully Processed!*\n"
        f"{'─' * 30}\n\n"
        f"Your refund request has been *approved and processed*.\n\n"
        f"💰 *Refund Amount:* ₹{refund_amount:.0f}\n"
        f"🔖 *UTR / Reference Number:* `{utr}`\n\n"
        f"Amount may take some time to reflect in your bank account.\n\n"
        f"{'─' * 30}\n"
        f"Thank you,\nPareeksha Gurukul Support Team 🎓"
    )


def user_declined_msg(reason: str) -> str:
    return (
        f"❌ *Refund Request Declined*\n"
        f"{'─' * 30}\n\n"
        f"We regret to inform you that your refund request has been *declined*.\n\n"
        f"📋 *Reason:*\n{reason}\n\n"
        f"For further support, please contact our admin team.\n\n"
        f"{'─' * 30}\n"
        f"Thank you,\nPareeksha Gurukul Support Team 🎓"
    )


def status_detail(req: dict) -> str:
    status_icon = {"Pending": "⏳", "Approved": "✅", "Declined": "❌", "Processing": "🔄"}.get(req["status"], "📋")
    text = (
        f"📋 *Refund Request Details*\n"
        f"{'─' * 30}\n"
        f"🎫 *Ticket ID:* `{req['ticket_id']}`\n"
        f"📊 *Status:* {status_icon} {req['status']}\n"
        f"👤 *Name:* {req['full_name']}\n"
        f"📚 *Plan:* {req['plan_name']}\n"
        f"💰 *Original:* ₹{req['original_amount']:.0f}\n"
        f"💸 *Refund:* ₹{req['refund_amount']:.0f}\n"
        f"💳 *UPI ID:* `{req['upi_id']}`\n"
        f"🕐 *Submitted:* {req['submitted_at']}\n"
    )
    if req["status"] == "Approved":
        text += f"🔖 *UTR:* `{req['utr_number']}`\n"
        text += f"✅ *Processed:* {req['processed_at']}\n"
    elif req["status"] == "Declined":
        text += f"📝 *Reason:* {req['admin_remarks']}\n"
    return text


# ── Admin Messages ─────────────────────────────────────────────────────────────
def admin_request_card(req: dict, ticket_id: str) -> str:
    return (
        f"🆕 *New Refund Request*\n"
        f"{'═' * 30}\n\n"
        f"🎫 *Ticket ID:* `{ticket_id}`\n"
        f"👤 *Student Name:* {req['full_name']}\n"
        f"📱 *Mobile Number:* `{req['mobile']}`\n"
        f"📚 *Purchased Plan:* {req['plan_name']}\n"
        f"💰 *Original Amount:* ₹{req['original_amount']:.0f}\n"
        f"💸 *Refund Amount:* ₹{req['refund_amount']:.0f}\n"
        f"💳 *UPI ID:* `{req['upi_id']}`\n"
        f"🕐 *Request Time:* {req['submitted_at']}\n"
        f"🆔 *User ID:* `{req['user_id']}`\n"
        f"{'─' * 30}\n"
        f"⏳ *Status:* Pending Review"
    )


def admin_stats_card(stats: dict) -> str:
    total_refund = sum(
        stats[s]["total"] for s in ("Pending", "Approved", "Declined", "Processing")
    )
    return (
        f"📊 *Refund Analytics Dashboard*\n"
        f"{'═' * 30}\n\n"
        f"⏳ *Pending:* {stats['Pending']['count']} requests  |  ₹{stats['Pending']['total']:.0f}\n"
        f"✅ *Approved:* {stats['Approved']['count']} requests  |  ₹{stats['Approved']['total']:.0f}\n"
        f"❌ *Declined:* {stats['Declined']['count']} requests  |  ₹{stats['Declined']['total']:.0f}\n"
        f"🔄 *Processing:* {stats['Processing']['count']} requests  |  ₹{stats['Processing']['total']:.0f}\n"
        f"{'─' * 30}\n"
        f"💰 *Total Refund Value:* ₹{total_refund:.0f}\n"
        f"👥 *Total Users:* {stats['users']}\n"
        f"📚 *Active Plans:* {stats['plans']}\n"
    )


HELP_TEXT = (
    f"🆘 *Pareeksha Gurukul Refund Help*\n"
    f"{'─' * 30}\n\n"
    f"*How to apply for a refund?*\n"
    f"Tap '💸 Apply for Refund' from the main menu and follow the steps.\n\n"
    f"*How to check refund status?*\n"
    f"Tap '🔍 Check Refund Status' from the main menu.\n\n"
    f"*When will I get my refund?*\n"
    f"After approval, refunds are processed within 7 working days.\n\n"
    f"*Note:* Refunds are processed after deducting applicable platform charges and GST."
)

CANCELLED = (
    "🚫 *Request Cancelled*\n\n"
    "Your refund application has been cancelled.\n"
    "Tap the button below to go back to the main menu."
)

ALREADY_HAS_REQUEST = (
    "⚠️ *Active Request Exists*\n\n"
    "You already have an active refund request.\n"
    "Please wait for it to be processed before submitting a new one.\n\n"
    "Use '🔍 Check Refund Status' to see your current request."
)

REFUND_DISABLED = (
    "🔒 *Refund Requests Temporarily Disabled*\n\n"
    "We are currently not accepting refund requests.\n"
    "Please try again later or contact support."
)

BANNED_MSG = (
    "🚫 *Account Restricted*\n\n"
    "Your account has been flagged for suspicious activity.\n"
    "Please contact our support team for assistance."
)

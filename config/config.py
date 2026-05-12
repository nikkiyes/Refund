"""
Pareeksha Gurukul Refund Bot — Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Bot Credentials ──────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ─── Admin IDs (comma-separated in .env) ─────────────────────────────────────
_raw_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw_admins.split(",") if x.strip()]

# Admin group/channel where refund requests are forwarded
ADMIN_GROUP_ID: int = int(os.getenv("ADMIN_GROUP_ID", "0"))

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "data/pg_refund.db")

# ─── Rate Limiting ────────────────────────────────────────────────────────────
RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "5"))

# ─── App Metadata ─────────────────────────────────────────────────────────────
BOT_NAME = "Pareeksha Gurukul Refund Bot"
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@PareekshaGurukul")
VERSION = "1.0.0"

# ─── UPI Validation Pattern ───────────────────────────────────────────────────
import re
UPI_PATTERN = re.compile(r"^[\w.\-]{3,}@[a-zA-Z]{3,}$")

# ─── FSM States (string keys) ─────────────────────────────────────────────────
class States:
    IDLE              = "idle"
    NAME              = "name"
    MOBILE            = "mobile"
    PLAN              = "plan"
    SCREENSHOT        = "screenshot"
    UPI               = "upi"
    CONFIRM           = "confirm"

    # Admin
    A_UTR             = "a_utr"
    A_DECLINE_REASON  = "a_decline_reason"
    A_ADD_PLAN_NAME   = "a_add_plan_name"
    A_ADD_PLAN_ORIG   = "a_add_plan_orig"
    A_ADD_PLAN_REF    = "a_add_plan_ref"
    A_EDIT_PLAN_NAME  = "a_edit_plan_name"
    A_EDIT_PLAN_ORIG  = "a_edit_plan_orig"
    A_EDIT_PLAN_REF   = "a_edit_plan_ref"
    A_BROADCAST       = "a_broadcast"
    A_SEARCH          = "a_search"
    A_NOTE            = "a_note"
    A_WORKING_DAYS    = "a_working_days"
    A_SUPPORT_MSG     = "a_support_msg"
    A_WELCOME_MSG     = "a_welcome_msg"
    A_ADD_ADMIN       = "a_add_admin"

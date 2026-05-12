"""
Pareeksha Gurukul Refund Bot — Main Entry Point
Async polling bot using pyTelegramBotAPI (telebot).

Run: python main.py
"""

import asyncio
import logging
import os
import sys

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Ensure data directory exists ──────────────────────────────────────────────
os.makedirs("data", exist_ok=True)

# ── Imports ───────────────────────────────────────────────────────────────────
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_filters

from config.config import BOT_TOKEN, ADMIN_IDS
from database.db import init_db
from handlers.user_handlers import register_user_handlers
from handlers.admin_handlers import register_admin_handlers


# ══════════════════════════════════════════════════════════════════════════════
#  BOT SETUP
# ══════════════════════════════════════════════════════════════════════════════
def create_bot() -> AsyncTeleBot:
    if not BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN is not set! Please check your .env file.")
        sys.exit(1)

    bot = AsyncTeleBot(BOT_TOKEN, parse_mode=None)
    return bot


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
async def main():
    logger.info("🚀 Starting Pareeksha Gurukul Refund Bot...")

    # Initialise database
    await init_db()
    logger.info("✅ Database ready")

    bot = create_bot()

    # Register all handlers
    # IMPORTANT: Admin handlers must be registered BEFORE user handlers
    # so that admin FSM states are caught first.
    register_admin_handlers(bot)
    register_user_handlers(bot)

    logger.info("✅ Handlers registered")
    logger.info(f"👑 Super-admins: {ADMIN_IDS}")

    # Set bot commands
    from telebot.types import BotCommand
    await bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("refund", "Apply for a refund"),
        BotCommand("status", "Check your refund status"),
        BotCommand("help", "Help & Support"),
        BotCommand("cancel", "Cancel current action"),
    ])

    logger.info("🤖 Bot is polling... Press Ctrl+C to stop.")

    try:
        await bot.polling(non_stop=True, timeout=30, request_timeout=60)
    except Exception as e:
        logger.error("Polling error: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())

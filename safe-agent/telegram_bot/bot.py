"""
Telegram Bot — Phone interface for the Safe Automation Agent.

This bot:
  1. Accepts commands from authorized Telegram users only.
  2. Forwards valid commands to the cloud agent via REST.
  3. Polls the cloud agent for results and relays them back.

SAFETY:
  - Only chat IDs in ALLOWED_CHAT_IDS can use the bot.
  - Commands are validated against the whitelist before forwarding.
  - No shell access, no file uploads, no arbitrary text execution.

Shortcut commands (one-tap from phone):
  /status    — Laptop system status (CPU, RAM, disk)
  /startnav  — Open the navigation dashboard
  /stopnav   — Close the navigation dashboard
  /logs      — Last 50 lines of listener log
  /ping      — Check if laptop is online
  /battery   — Battery percentage
  /procs     — Top 10 processes by memory
  /folder    — Open project folder on laptop

General commands:
  /start     — Welcome message
  /help      — Full command list
  /myid      — Show your Telegram chat ID (for ALLOWED_CHAT_IDS)
  /run <action>  — Run any whitelisted action by name
  /health    — Check cloud agent reachability
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ── Ensure shared package is importable ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import (
    ALLOWED_ACTION_NAMES,
    ALLOWED_CHAT_IDS,
    AUTH_TOKEN,
    CLOUD_AGENT_URL,
    COMMAND_SHORTCUTS,
    TELEGRAM_BOT_TOKEN,
    WHITELISTED_ACTIONS,
)

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_bot")

# ── HTTP client for cloud agent communication ────────────────────
HEADERS = {"X-Auth-Token": AUTH_TOKEN}


# ── Authorization guard ──────────────────────────────────────────
def authorized(update: Update) -> bool:
    """Return True only if the sender's chat ID is in the allow-list."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        logger.warning("Unauthorized access attempt from chat_id=%s", chat_id)
        return False
    return True


# ══════════════════════════════════════════════
# GENERAL COMMANDS
# ══════════════════════════════════════════════


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Welcome message with quick overview."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    logger.info("/start from chat_id=%s", chat_id)

    if not authorized(update):
        await update.message.reply_text(  # type: ignore[union-attr]
            f"⛔ Unauthorized. Your chat ID is `{chat_id}`.\n"
            "Ask the admin to add it to ALLOWED_CHAT_IDS.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(  # type: ignore[union-attr]
        "🤖 *Safe Automation Agent*\n\n"
        "Control your laptop from here.\n\n"
        "*Quick commands:*\n"
        "/status — System status\n"
        "/startnav — Open dashboard\n"
        "/stopnav — Close dashboard\n"
        "/logs — View listener logs\n"
        "/ping — Check laptop is alive\n\n"
        "Type /help for the full list.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — Full command reference."""
    if not authorized(update):
        await update.message.reply_text("⛔ You are not authorized.")  # type: ignore[union-attr]
        return

    lines = [
        "*━━━ Shortcut Commands ━━━*\n",
        "/status — Laptop CPU, RAM & disk",
        "/startnav — Open navigation dashboard",
        "/stopnav — Close navigation dashboard",
        "/logs — Last 50 lines of listener log",
        "/ping — Check if laptop listener is alive",
        "/battery — Battery level & charging state",
        "/procs — Top 10 processes by memory",
        "/folder — Open project folder in file manager",
        "",
        "*━━━ General Commands ━━━*\n",
        "/health — Check cloud agent status",
        "/myid — Show your Telegram chat ID",
        "/run `<action>` — Run any whitelisted action",
        "",
        "*━━━ All Whitelisted Actions ━━━*\n",
    ]
    for name, info in WHITELISTED_ACTIONS.items():
        lines.append(f"• `{name}` — {info['description']}")

    await update.message.reply_text(  # type: ignore[union-attr]
        "\n".join(lines), parse_mode="Markdown"
    )


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/myid — Show the user's Telegram chat ID for configuration."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    user = update.effective_user  # type: ignore[union-attr]
    username = f"@{user.username}" if user and user.username else "(no username)"
    logger.info("/myid from chat_id=%s user=%s", chat_id, username)

    await update.message.reply_text(  # type: ignore[union-attr]
        f"🆔 *Your Telegram Info*\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"Username: {username}\n\n"
        f"_Add this chat ID to_ `ALLOWED_CHAT_IDS` _in your .env file._",
        parse_mode="Markdown",
    )


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/health — Check if the cloud agent is reachable."""
    if not authorized(update):
        await update.message.reply_text("⛔ You are not authorized.")  # type: ignore[union-attr]
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{CLOUD_AGENT_URL}/health")
            data = resp.json()
            await update.message.reply_text(  # type: ignore[union-attr]
                f"☁️ Cloud Agent: *{data.get('status', 'unknown')}*\n"
                f"Pending actions: {data.get('pending', '?')}",
                parse_mode="Markdown",
            )
    except Exception as exc:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"❌ Cloud agent unreachable: {exc}"
        )


# ══════════════════════════════════════════════
# ACTION DISPATCH (shared by /run and shortcuts)
# ══════════════════════════════════════════════


async def _dispatch_action(update: Update, action: str) -> None:
    """
    Validate an action, send it to the cloud agent, poll for results.
    Used by both /run and the shortcut commands.
    """
    # ── SAFETY GATE: local whitelist check before calling cloud ──
    if action not in ALLOWED_ACTION_NAMES:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"⛔ `{action}` is not an allowed action.\nUse /help to see the list.",
            parse_mode="Markdown",
        )
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{CLOUD_AGENT_URL}/command",
                json={"action": action},
                headers=HEADERS,
            )
            if resp.status_code != 200:
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"❌ Cloud rejected command: {resp.text}"
                )
                return

            data = resp.json()
            action_id = data["action_id"]

        await update.message.reply_text(  # type: ignore[union-attr]
            f"✅ `{action}` queued — waiting for laptop…",
            parse_mode="Markdown",
        )

        # Poll for result (up to 30 seconds)
        result_text = await _poll_for_result(action_id)
        await update.message.reply_text(  # type: ignore[union-attr]
            result_text, parse_mode="Markdown"
        )

    except Exception as exc:
        logger.exception("Error dispatching action '%s'", action)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"❌ Error: {exc}"
        )


async def _poll_for_result(action_id: str, timeout: int = 30, interval: int = 2) -> str:
    """Poll the cloud agent for a completed result."""
    elapsed = 0
    async with httpx.AsyncClient(timeout=5) as client:
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            try:
                resp = await client.get(
                    f"{CLOUD_AGENT_URL}/result/{action_id}",
                    headers=HEADERS,
                )
                data = resp.json()
                if data.get("status") == "completed":
                    success = "✅" if data.get("success") else "❌"
                    output = data.get("output", "(no output)")
                    return f"{success} *Result:*\n```\n{output}\n```"
            except Exception:
                pass

    return "⏰ Timed out waiting for result. The laptop may be offline."


# ══════════════════════════════════════════════
# /run <action> — Generic action runner
# ══════════════════════════════════════════════


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/run <action> — Execute any whitelisted action by name."""
    if not authorized(update):
        await update.message.reply_text("⛔ You are not authorized.")  # type: ignore[union-attr]
        return

    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Usage: `/run <action>`\nSee /help for available actions.",
            parse_mode="Markdown",
        )
        return

    action = context.args[0].strip().lower()
    await _dispatch_action(update, action)


# ══════════════════════════════════════════════
# SHORTCUT COMMANDS — /status, /startnav, etc.
# ══════════════════════════════════════════════


def _make_shortcut_handler(action_name: str):
    """
    Factory that creates a handler for a shortcut command.
    Each shortcut maps to exactly one whitelisted action.
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not authorized(update):
            await update.message.reply_text("⛔ You are not authorized.")  # type: ignore[union-attr]
            return
        await _dispatch_action(update, action_name)

    handler.__name__ = f"shortcut_{action_name}"
    handler.__doc__ = f"Shortcut for whitelisted action: {action_name}"
    return handler


# ══════════════════════════════════════════════
# BOT COMMAND MENU (auto-registered with BotFather)
# ══════════════════════════════════════════════

BOT_COMMANDS = [
    BotCommand("start", "Welcome message"),
    BotCommand("help", "Full command reference"),
    BotCommand("status", "Laptop CPU, RAM & disk"),
    BotCommand("startnav", "Open navigation dashboard"),
    BotCommand("stopnav", "Close navigation dashboard"),
    BotCommand("logs", "View listener logs"),
    BotCommand("ping", "Check if laptop is alive"),
    BotCommand("battery", "Battery level"),
    BotCommand("procs", "Top processes by memory"),
    BotCommand("folder", "Open project folder"),
    BotCommand("health", "Cloud agent status"),
    BotCommand("myid", "Show your chat ID"),
    BotCommand("run", "Run any whitelisted action"),
]


async def post_init(application: Application) -> None:
    """Set the command menu in Telegram after the bot starts."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Registered %d commands with Telegram menu.", len(BOT_COMMANDS))


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Exiting.")
        sys.exit(1)
    if not AUTH_TOKEN:
        logger.error("SAFE_AGENT_TOKEN is not set. Exiting.")
        sys.exit(1)

    logger.info("Starting Telegram bot…")
    logger.info("Cloud agent URL: %s", CLOUD_AGENT_URL)
    logger.info("Allowed chat IDs: %s", ALLOWED_CHAT_IDS or "(any — open access)")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # General commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("myid", cmd_myid))
    application.add_handler(CommandHandler("health", cmd_health))
    application.add_handler(CommandHandler("run", cmd_run))

    # Shortcut commands — each maps to one whitelisted action
    for cmd_name, action_name in COMMAND_SHORTCUTS.items():
        application.add_handler(
            CommandHandler(cmd_name, _make_shortcut_handler(action_name))
        )
        logger.info("Registered shortcut: /%s → %s", cmd_name, action_name)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

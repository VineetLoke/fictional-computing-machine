"""
Shared configuration and whitelist for the Safe Automation Agent.

SAFETY: This file defines the ONLY actions the system is allowed to perform.
Any action not listed here will be rejected at both cloud and laptop layers.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from the project root (safe-agent/.env)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

# ──────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────
# Shared secret loaded from environment — never hardcoded.
AUTH_TOKEN = os.environ.get("SAFE_AGENT_TOKEN", "")

# Telegram bot token (cloud side only)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Comma-separated list of allowed Telegram user/chat IDs.
# Only these users can issue commands.
ALLOWED_CHAT_IDS: list[int] = [
    int(cid.strip())
    for cid in os.environ.get("ALLOWED_CHAT_IDS", "").split(",")
    if cid.strip().isdigit()
]

# ──────────────────────────────────────────────
# Cloud Agent Settings
# ──────────────────────────────────────────────
CLOUD_HOST = os.environ.get("CLOUD_HOST", "0.0.0.0")
CLOUD_PORT = int(os.environ.get("CLOUD_PORT", "8000"))

# ──────────────────────────────────────────────
# Laptop Listener Settings
# ──────────────────────────────────────────────
# URL the laptop polls for pending actions
CLOUD_AGENT_URL = os.environ.get("CLOUD_AGENT_URL", "http://localhost:8000")

# Seconds between polls (keep low CPU usage)
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3"))

# ──────────────────────────────────────────────
# WHITELISTED ACTIONS
# ──────────────────────────────────────────────
# Each key is the command name users type.
# "description" is shown in /help.
# "function" is the exact Python function name in laptop/actions.py.
# "args" lists any expected argument names (currently none — all are zero-arg).
#
# ⚠ SAFETY: To add a new action you must:
#   1. Add an entry here.
#   2. Implement the function in laptop/actions.py.
#   3. There is NO other way to execute code.
# ──────────────────────────────────────────────

WHITELISTED_ACTIONS: dict[str, dict] = {
    "get_system_status": {
        "description": "Return CPU, memory, and disk usage of the laptop.",
        "function": "get_system_status",
        "args": [],
    },
    "start_navigation_dashboard": {
        "description": "Open the navigation/project dashboard in the default browser.",
        "function": "start_navigation_dashboard",
        "args": [],
    },
    "stop_navigation_dashboard": {
        "description": "Close the navigation dashboard process.",
        "function": "stop_navigation_dashboard",
        "args": [],
    },
    "send_log_file": {
        "description": "Return the last 50 lines of the agent log file.",
        "function": "send_log_file",
        "args": [],
    },
    "open_project_folder": {
        "description": "Open the default project folder in the file manager.",
        "function": "open_project_folder",
        "args": [],
    },
    "ping": {
        "description": "Check if the laptop listener is alive.",
        "function": "ping",
        "args": [],
    },
    "get_battery_status": {
        "description": "Return battery percentage and charging state.",
        "function": "get_battery_status",
        "args": [],
    },
    "list_running_processes": {
        "description": "Return top 10 processes by memory usage.",
        "function": "list_running_processes",
        "args": [],
    },
    "lock_screen": {
        "description": "Lock the laptop screen immediately.",
        "function": "lock_screen",
        "args": [],
    },
    "get_ip_address": {
        "description": "Show local IP address and hostname.",
        "function": "get_ip_address",
        "args": [],
    },
    "get_wifi_name": {
        "description": "Show the currently connected Wi-Fi network.",
        "function": "get_wifi_name",
        "args": [],
    },
    "get_uptime": {
        "description": "Show how long the laptop has been running.",
        "function": "get_uptime",
        "args": [],
    },
    "get_volume_level": {
        "description": "Show current system audio volume level.",
        "function": "get_volume_level",
        "args": [],
    },
}

# Pre-computed set for O(1) lookup
ALLOWED_ACTION_NAMES: set[str] = set(WHITELISTED_ACTIONS.keys())

# ──────────────────────────────────────────────
# TELEGRAM SHORTCUT COMMANDS
# ──────────────────────────────────────────────
# Maps short /command names to whitelisted action names.
# These give users quick one-tap access from the Telegram command menu.
COMMAND_SHORTCUTS: dict[str, str] = {
    "status": "get_system_status",
    "startnav": "start_navigation_dashboard",
    "stopnav": "stop_navigation_dashboard",
    "logs": "send_log_file",
    "ping": "ping",
    "battery": "get_battery_status",
    "procs": "list_running_processes",
    "folder": "open_project_folder",
    "lock": "lock_screen",
    "ip": "get_ip_address",
    "wifi": "get_wifi_name",
    "uptime": "get_uptime",
    "volume": "get_volume_level",
}

#!/usr/bin/env bash
# ============================================================
# Safe Automation Agent — One-Command Launcher
# ============================================================
# Usage:  ./start.sh
#
# Starts the cloud agent and Telegram bot in the foreground.
# Press Ctrl+C to stop both.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   Safe Automation Agent — Launcher${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ── Check .env ───────────────────────────────────────────────
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠  No .env file found.${NC}"
    echo ""
    if [ -f .env.example ]; then
        echo "Creating .env from .env.example…"
        cp .env.example .env

        # Auto-generate a secure token
        TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "CHANGE_ME")
        sed -i "s/^SAFE_AGENT_TOKEN=CHANGE_ME/SAFE_AGENT_TOKEN=${TOKEN}/" .env
        echo -e "${GREEN}✓  Generated .env with auto-generated SAFE_AGENT_TOKEN${NC}"
        echo ""
        echo -e "${YELLOW}You still need to set:${NC}"
        echo "  1. TELEGRAM_BOT_TOKEN  (from @BotFather)"
        echo "  2. ALLOWED_CHAT_IDS    (your Telegram chat ID)"
        echo ""
        echo "Edit .env and re-run this script."
        echo "See docs/TELEGRAM_SETUP.md for step-by-step instructions."
        exit 1
    else
        echo -e "${RED}✗  No .env.example found either. Cannot continue.${NC}"
        exit 1
    fi
fi

# ── Load and validate .env ───────────────────────────────────
set -a
source .env
set +a

ERRORS=0

if [ -z "${SAFE_AGENT_TOKEN:-}" ] || [ "$SAFE_AGENT_TOKEN" = "CHANGE_ME" ]; then
    echo -e "${RED}✗  SAFE_AGENT_TOKEN is not set.${NC}"
    ERRORS=1
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ "$TELEGRAM_BOT_TOKEN" = "CHANGE_ME" ]; then
    echo -e "${RED}✗  TELEGRAM_BOT_TOKEN is not set.${NC}"
    echo "   Get one from @BotFather on Telegram."
    ERRORS=1
fi

if [ "$ERRORS" -eq 1 ]; then
    echo ""
    echo "Edit safe-agent/.env and re-run this script."
    exit 1
fi

echo -e "${GREEN}✓  Environment loaded${NC}"

# ── Check dependencies ───────────────────────────────────────
echo -n "Checking Python dependencies… "
MISSING=""
python3 -c "import fastapi" 2>/dev/null || MISSING="$MISSING fastapi"
python3 -c "import uvicorn" 2>/dev/null || MISSING="$MISSING uvicorn"
python3 -c "import telegram" 2>/dev/null || MISSING="$MISSING python-telegram-bot"
python3 -c "import httpx" 2>/dev/null || MISSING="$MISSING httpx"
python3 -c "import dotenv" 2>/dev/null || MISSING="$MISSING python-dotenv"

if [ -n "$MISSING" ]; then
    echo -e "${YELLOW}installing missing:${MISSING}${NC}"
    pip install -q $MISSING
else
    echo -e "${GREEN}OK${NC}"
fi

# ── Trap Ctrl+C to clean up both processes ───────────────────
CLOUD_PID=""
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down…${NC}"
    if [ -n "$CLOUD_PID" ]; then
        kill "$CLOUD_PID" 2>/dev/null || true
        wait "$CLOUD_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}Done.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Start Cloud Agent (background) ──────────────────────────
echo -e "${CYAN}Starting cloud agent on ${CLOUD_HOST:-0.0.0.0}:${CLOUD_PORT:-8000}…${NC}"
python3 -m cloud.agent &
CLOUD_PID=$!
sleep 2

# Verify it started
if ! kill -0 "$CLOUD_PID" 2>/dev/null; then
    echo -e "${RED}✗  Cloud agent failed to start.${NC}"
    exit 1
fi
echo -e "${GREEN}✓  Cloud agent running (PID $CLOUD_PID)${NC}"

# ── Start Telegram Bot (foreground) ─────────────────────────
echo -e "${CYAN}Starting Telegram bot…${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   System is live! Open Telegram and send /start${NC}"
echo -e "${GREEN}   Press Ctrl+C to stop.${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

python3 -m telegram_bot.bot

# If bot exits, clean up
cleanup

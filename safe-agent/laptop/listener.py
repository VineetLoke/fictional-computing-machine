"""
Laptop Listener — Lightweight polling client that runs on the user's laptop.

This script:
  1. Polls the cloud agent's /pending endpoint every POLL_INTERVAL seconds.
  2. When an action arrives, validates it against the LOCAL whitelist.
  3. Executes the corresponding function from actions.py.
  4. Reports the result back to the cloud agent via /result.

SAFETY:
  - Double whitelist check (cloud already checked, we check again).
  - Only functions in ACTION_REGISTRY can execute.
  - No eval, no exec, no shell=True, no dynamic imports.
  - Auth token required for every HTTP call.
  - Minimal resource usage: single thread, simple polling.

Resource Usage:
  - ~10 MB RAM at idle.
  - Near-zero CPU between polls.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import requests

# ── Ensure shared package is importable ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import (
    ALLOWED_ACTION_NAMES,
    AUTH_TOKEN,
    CLOUD_AGENT_URL,
    POLL_INTERVAL,
)

from laptop.actions import ACTION_REGISTRY, LOG_FILE

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("laptop_listener")

# ── HTTP headers ─────────────────────────────────────────────────
HEADERS = {"X-Auth-Token": AUTH_TOKEN}


def fetch_pending_action() -> dict | None:
    """Poll the cloud agent for the next pending action."""
    try:
        resp = requests.get(
            f"{CLOUD_AGENT_URL}/pending",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("action") is None:
            return None
        return data
    except requests.RequestException as exc:
        logger.warning("Failed to fetch pending action: %s", exc)
        return None


def report_result(action_id: str, success: bool, output: str) -> None:
    """Send the action result back to the cloud agent."""
    try:
        resp = requests.post(
            f"{CLOUD_AGENT_URL}/result",
            json={
                "action_id": action_id,
                "success": success,
                "output": output[:4000],  # Truncate large outputs
            },
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Reported result for %s", action_id)
    except requests.RequestException as exc:
        logger.error("Failed to report result for %s: %s", action_id, exc)


def execute_action(action_payload: dict) -> None:
    """
    Validate and execute a single action.
    
    SAFETY: Even though the cloud agent already validated the action,
    we perform a SECOND whitelist check here at the laptop level.
    """
    action_id = action_payload.get("action_id", "unknown")
    action_name = action_payload.get("action", "")

    logger.info("Received action: %s (id=%s)", action_name, action_id)

    # ── SAFETY GATE 1: Whitelist check ───────────────────────────
    if action_name not in ALLOWED_ACTION_NAMES:
        logger.warning("REJECTED: '%s' not in whitelist", action_name)
        report_result(action_id, False, f"Action '{action_name}' is not whitelisted.")
        return

    # ── SAFETY GATE 2: Registry check ────────────────────────────
    func = ACTION_REGISTRY.get(action_name)
    if func is None:
        logger.warning("REJECTED: '%s' not in ACTION_REGISTRY", action_name)
        report_result(action_id, False, f"Action '{action_name}' has no implementation.")
        return

    # ── Execute ──────────────────────────────────────────────────
    try:
        output = func()
        logger.info("Action '%s' completed successfully", action_name)
        report_result(action_id, True, output)
    except Exception as exc:
        logger.exception("Action '%s' raised an exception", action_name)
        report_result(action_id, False, f"Error: {exc}")


def main_loop() -> None:
    """
    Main polling loop.
    Runs indefinitely, fetching and executing one action per cycle.
    """
    logger.info("Laptop listener started.")
    logger.info("Polling %s every %ds", CLOUD_AGENT_URL, POLL_INTERVAL)
    logger.info("Whitelisted actions: %s", ", ".join(sorted(ALLOWED_ACTION_NAMES)))

    while True:
        action = fetch_pending_action()
        if action is not None:
            execute_action(action)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    if not AUTH_TOKEN:
        logger.error("SAFE_AGENT_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Listener stopped by user.")

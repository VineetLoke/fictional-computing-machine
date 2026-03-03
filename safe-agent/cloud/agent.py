"""
Cloud Agent — FastAPI server that sits between the phone interface
and the laptop listener.

Responsibilities:
  1. Receive commands from Telegram bot (or web UI).
  2. Validate them against the shared whitelist.
  3. Queue them for the laptop listener to pick up.
  4. Store results returned by the laptop.

SAFETY:
  - Every inbound command is checked against ALLOWED_ACTION_NAMES.
  - Every request from the laptop must carry the AUTH_TOKEN.
  - No shell commands, no eval, no dynamic imports.
"""

from __future__ import annotations

import logging
import sys
import time
import uuid
from collections import deque
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

# ── Ensure shared package is importable ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import ALLOWED_ACTION_NAMES, AUTH_TOKEN, CLOUD_HOST, CLOUD_PORT

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cloud_agent")

# ── FastAPI app ──────────────────────────────────────────────────
app = FastAPI(
    title="Safe Automation Agent — Cloud",
    version="1.0.0",
    docs_url="/docs",
)

# ── In-memory queues (no database needed for lightweight use) ───
# Pending actions waiting for the laptop to pick up
pending_actions: deque[dict] = deque(maxlen=100)

# Completed results keyed by action_id
completed_results: dict[str, dict] = {}


# ── Pydantic models ─────────────────────────────────────────────
class CommandRequest(BaseModel):
    """Inbound command from Telegram bot or web UI."""
    action: str  # must be in ALLOWED_ACTION_NAMES


class ActionResult(BaseModel):
    """Result reported back by the laptop listener."""
    action_id: str
    success: bool
    output: str


# ── Auth dependency ──────────────────────────────────────────────
def verify_token(x_auth_token: str = Header(...)) -> str:
    """Reject requests without a valid token."""
    if not AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server AUTH_TOKEN not configured.",
        )
    if x_auth_token != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    return x_auth_token


# ── Endpoints ────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Public health-check (no auth needed)."""
    return {"status": "ok", "pending": len(pending_actions)}


@app.post("/command")
async def submit_command(cmd: CommandRequest, _token: str = Depends(verify_token)):
    """
    Called by the Telegram bot (or web UI) to queue a new action.
    The action MUST be in the whitelist — anything else is rejected.
    """
    # ── SAFETY GATE: whitelist check ─────────────────────────────
    if cmd.action not in ALLOWED_ACTION_NAMES:
        logger.warning("Rejected unknown action: %s", cmd.action)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action '{cmd.action}' is not in the whitelist.",
        )

    action_id = str(uuid.uuid4())
    action_payload = {
        "action_id": action_id,
        "action": cmd.action,
        "queued_at": time.time(),
    }
    pending_actions.append(action_payload)
    logger.info("Queued action %s → %s", action_id, cmd.action)

    return {"action_id": action_id, "status": "queued"}


@app.get("/pending")
async def get_pending(_token: str = Depends(verify_token)):
    """
    Called by the laptop listener to fetch the next pending action.
    Returns one action at a time (FIFO) or 204 if the queue is empty.
    """
    if not pending_actions:
        return {"action": None}

    action = pending_actions.popleft()
    logger.info("Dispatched action %s → laptop", action["action_id"])
    return action


@app.post("/result")
async def report_result(result: ActionResult, _token: str = Depends(verify_token)):
    """
    Called by the laptop listener to report the outcome of an action.
    """
    completed_results[result.action_id] = {
        "success": result.success,
        "output": result.output,
        "completed_at": time.time(),
    }
    logger.info(
        "Result for %s: success=%s", result.action_id, result.success
    )
    return {"status": "received"}


@app.get("/result/{action_id}")
async def get_result(action_id: str, _token: str = Depends(verify_token)):
    """
    Called by the Telegram bot to check if a result is ready.
    """
    if action_id in completed_results:
        return {"status": "completed", **completed_results[action_id]}
    return {"status": "pending"}


# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    if not AUTH_TOKEN:
        logger.error("SAFE_AGENT_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    logger.info("Starting cloud agent on %s:%s", CLOUD_HOST, CLOUD_PORT)
    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT)

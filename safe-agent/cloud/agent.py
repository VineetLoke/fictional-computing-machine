"""
Cloud Agent — FastAPI server that sits between the phone interface
and the laptop listener.

Responsibilities:
  1. Receive commands from Telegram bot (or web UI).
  2. Validate them against the shared whitelist.
  3. Queue them for the laptop listener to pick up.
  4. Store results returned by the laptop.

SECURITY HARDENING (v2):
  - Every inbound command is checked against ALLOWED_ACTION_NAMES.
  - Token comparison uses hmac.compare_digest (timing-attack safe).
  - Per-IP rate limiting (60 requests/minute default).
  - Auto-lockout after 5 failed auth attempts (15-minute ban).
  - Full audit log written to cloud/logs/audit.jsonl.
  - HTTPS enforcement warning on startup.
  - No shell commands, no eval, no dynamic imports.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import sys
import time
import uuid
from collections import deque, defaultdict
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
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

# ── Audit log ────────────────────────────────────────────────────
AUDIT_DIR = Path(__file__).resolve().parent / "logs"
AUDIT_DIR.mkdir(exist_ok=True)
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"


def audit_log(event: str, **kwargs) -> None:
    """Append a structured JSON event to the audit log file."""
    entry = {"ts": time.time(), "event": event, **kwargs}
    try:
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        logger.warning("Failed to write audit log entry")


# ── Rate limiter (in-memory, per-IP) ────────────────────────────
RATE_LIMIT_WINDOW = 60   # seconds
RATE_LIMIT_MAX = 60       # requests per window

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if the request should be ALLOWED, False if rate-limited."""
    now = time.time()
    bucket = _rate_buckets[client_ip]
    # Prune old entries
    _rate_buckets[client_ip] = [t for t in bucket if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_buckets[client_ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_buckets[client_ip].append(now)
    return True


# ── Auth lockout (per-IP) ───────────────────────────────────────
LOCKOUT_THRESHOLD = 5      # failed attempts before lockout
LOCKOUT_DURATION = 900     # 15 minutes

_auth_failures: dict[str, list[float]] = defaultdict(list)
_locked_ips: dict[str, float] = {}


def _is_locked(client_ip: str) -> bool:
    """Return True if the IP is currently locked out."""
    if client_ip in _locked_ips:
        if time.time() - _locked_ips[client_ip] < LOCKOUT_DURATION:
            return True
        # Lockout expired — clear it
        del _locked_ips[client_ip]
        _auth_failures.pop(client_ip, None)
    return False


def _record_auth_failure(client_ip: str) -> None:
    """Record a failed auth attempt; lock out if threshold exceeded."""
    now = time.time()
    _auth_failures[client_ip].append(now)
    # Only count recent failures
    _auth_failures[client_ip] = [
        t for t in _auth_failures[client_ip] if now - t < LOCKOUT_DURATION
    ]
    if len(_auth_failures[client_ip]) >= LOCKOUT_THRESHOLD:
        _locked_ips[client_ip] = now
        audit_log("ip_locked", ip=client_ip, reason="too_many_auth_failures")
        logger.warning("LOCKED OUT IP %s after %d failed attempts",
                        client_ip, LOCKOUT_THRESHOLD)


def _clear_auth_failures(client_ip: str) -> None:
    """Clear auth failure history on successful auth."""
    _auth_failures.pop(client_ip, None)


# ── Pre-hashed token for constant-time comparison ───────────────
_TOKEN_HASH = hashlib.sha256(AUTH_TOKEN.encode()).hexdigest() if AUTH_TOKEN else ""


# ── FastAPI app ──────────────────────────────────────────────────
app = FastAPI(
    title="Safe Automation Agent — Cloud",
    version="2.0.0",
    docs_url="/docs",
)


# ── Middleware: rate limiting + HTTPS check ──────────────────────
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"

    # Rate limit check
    if not _check_rate_limit(client_ip):
        audit_log("rate_limited", ip=client_ip, path=request.url.path)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Try again later."},
        )

    # Lockout check
    if _is_locked(client_ip):
        audit_log("locked_out_request", ip=client_ip, path=request.url.path)
        return JSONResponse(
            status_code=403,
            content={"detail": "IP temporarily locked out due to repeated auth failures."},
        )

    response = await call_next(request)
    return response


# ── In-memory queues (no database needed for lightweight use) ───
pending_actions: deque[dict] = deque(maxlen=100)
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


# ── Auth dependency (timing-attack safe) ─────────────────────────
def verify_token(request: Request, x_auth_token: str = Header(...)) -> str:
    """Reject requests without a valid token. Uses constant-time comparison."""
    client_ip = request.client.host if request.client else "unknown"

    if not AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server AUTH_TOKEN not configured.",
        )

    # Constant-time comparison to prevent timing attacks
    incoming_hash = hashlib.sha256(x_auth_token.encode()).hexdigest()
    if not hmac.compare_digest(incoming_hash, _TOKEN_HASH):
        _record_auth_failure(client_ip)
        audit_log("auth_failure", ip=client_ip, path=str(request.url.path))
        logger.warning("AUTH FAILURE from %s on %s", client_ip, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    _clear_auth_failures(client_ip)
    return x_auth_token


# ── Endpoints ────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Public health-check (no auth needed)."""
    return {"status": "ok", "pending": len(pending_actions)}


@app.post("/command")
async def submit_command(
    request: Request, cmd: CommandRequest, _token: str = Depends(verify_token)
):
    """
    Called by the Telegram bot (or web UI) to queue a new action.
    The action MUST be in the whitelist — anything else is rejected.
    """
    client_ip = request.client.host if request.client else "unknown"

    # ── SAFETY GATE: whitelist check ─────────────────────────────
    if cmd.action not in ALLOWED_ACTION_NAMES:
        audit_log("rejected_action", ip=client_ip, action=cmd.action)
        logger.warning("Rejected unknown action: %s from %s", cmd.action, client_ip)
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
    audit_log("command_queued", ip=client_ip, action=cmd.action, action_id=action_id)
    logger.info("Queued action %s → %s (from %s)", action_id, cmd.action, client_ip)

    return {"action_id": action_id, "status": "queued"}


@app.get("/pending")
async def get_pending(_token: str = Depends(verify_token)):
    """
    Called by the laptop listener to fetch the next pending action.
    Returns one action at a time (FIFO) or empty if the queue is empty.
    """
    if not pending_actions:
        return {"action": None}

    action = pending_actions.popleft()
    audit_log("action_dispatched", action=action["action"], action_id=action["action_id"])
    logger.info("Dispatched action %s → laptop", action["action_id"])
    return action


@app.post("/result")
async def report_result(result: ActionResult, _token: str = Depends(verify_token)):
    """
    Called by the laptop listener to report the outcome of an action.
    """
    # Sanitize output — strip potential control characters
    clean_output = result.output[:4000].replace("\x00", "")

    completed_results[result.action_id] = {
        "success": result.success,
        "output": clean_output,
        "completed_at": time.time(),
    }
    audit_log("result_received", action_id=result.action_id, success=result.success)
    logger.info("Result for %s: success=%s", result.action_id, result.success)
    return {"status": "received"}


@app.get("/result/{action_id}")
async def get_result(action_id: str, _token: str = Depends(verify_token)):
    """
    Called by the Telegram bot to check if a result is ready.
    """
    # Validate action_id format (UUID only)
    try:
        uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action_id format.",
        )

    if action_id in completed_results:
        return {"status": "completed", **completed_results[action_id]}
    return {"status": "pending"}


# ── Startup: HTTPS enforcement warning ───────────────────────────
@app.on_event("startup")
async def startup_warnings():
    """Log security warnings on startup."""
    audit_log("server_started", host=CLOUD_HOST, port=CLOUD_PORT)

    # Warn if running behind plain HTTP
    import os
    if not os.environ.get("HTTPS", "") and not os.environ.get("SSL_CERT_FILE", ""):
        logger.warning(
            "⚠️  SECURITY: No HTTPS detected. In production, always use HTTPS "
            "(Codespaces provides this automatically via port forwarding)."
        )

    if not AUTH_TOKEN:
        logger.error("⚠️  CRITICAL: SAFE_AGENT_TOKEN is not set!")

    # Check token strength
    if AUTH_TOKEN and len(AUTH_TOKEN) < 32:
        logger.warning(
            "⚠️  SECURITY: Auth token is shorter than 32 characters. "
            "Generate a stronger one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    logger.info("Security features active: rate-limiting, auto-lockout, audit logging, timing-safe auth")


# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    if not AUTH_TOKEN:
        logger.error("SAFE_AGENT_TOKEN environment variable is not set. Exiting.")
        sys.exit(1)

    logger.info("Starting cloud agent on %s:%s", CLOUD_HOST, CLOUD_PORT)
    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT)

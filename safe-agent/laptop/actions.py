"""
Laptop Actions — The ONLY code that actually runs on the user's machine.

SAFETY RULES:
  1. Every function here is a whitelisted action from shared/config.py.
  2. Functions MUST NOT accept arbitrary user input.
  3. No subprocess with shell=True.
  4. No eval(), exec(), or dynamic imports.
  5. No file writes outside the agent's own log directory.
  6. No network requests (only the listener makes those).

To add a new action:
  1. Define it below as a plain function returning a string.
  2. Register it in shared/config.py WHITELISTED_ACTIONS.
"""

from __future__ import annotations

import datetime
import os
import platform
import subprocess
import sys
from pathlib import Path

# ── Logging directory ────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "listener.log"

# ── Dashboard process handle (module-level state) ────────────────
_dashboard_process: subprocess.Popen | None = None


# ──────────────────────────────────────────────
# Action: ping
# ──────────────────────────────────────────────
def ping() -> str:
    """Simple liveness check."""
    return f"pong — {datetime.datetime.now().isoformat()}"


# ──────────────────────────────────────────────
# Action: get_system_status
# ──────────────────────────────────────────────
def get_system_status() -> str:
    """Return basic system metrics without any third-party deps."""
    info_lines = [
        f"Platform : {platform.system()} {platform.release()}",
        f"Machine  : {platform.machine()}",
        f"Python   : {sys.version.split()[0]}",
        f"Time     : {datetime.datetime.now().isoformat()}",
    ]

    # CPU load (Unix only)
    try:
        load1, load5, load15 = os.getloadavg()
        info_lines.append(f"Load avg : {load1:.2f} / {load5:.2f} / {load15:.2f}")
    except OSError:
        info_lines.append("Load avg : (unavailable on this OS)")

    # Memory (Linux /proc/meminfo)
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        mem = {}
        for line in meminfo.read_text().splitlines()[:5]:
            key, val = line.split(":")
            mem[key.strip()] = val.strip()
        info_lines.append(f"MemTotal : {mem.get('MemTotal', '?')}")
        info_lines.append(f"MemFree  : {mem.get('MemFree', '?')}")
        info_lines.append(f"MemAvail : {mem.get('MemAvailable', '?')}")

    # Disk usage (stdlib)
    try:
        usage = os.statvfs("/")
        total_gb = (usage.f_frsize * usage.f_blocks) / (1024**3)
        free_gb = (usage.f_frsize * usage.f_bfree) / (1024**3)
        info_lines.append(f"Disk     : {free_gb:.1f} GB free / {total_gb:.1f} GB total")
    except Exception:
        info_lines.append("Disk     : (unavailable)")

    return "\n".join(info_lines)


# ──────────────────────────────────────────────
# Action: get_battery_status
# ──────────────────────────────────────────────
def get_battery_status() -> str:
    """Read battery info from /sys (Linux) or report unavailable."""
    bat_path = Path("/sys/class/power_supply/BAT0")
    if not bat_path.exists():
        return "Battery info not available (no BAT0 found — may be a desktop or VM)."

    try:
        capacity = (bat_path / "capacity").read_text().strip()
        status = (bat_path / "status").read_text().strip()
        return f"Battery: {capacity}% — {status}"
    except Exception as exc:
        return f"Could not read battery info: {exc}"


# ──────────────────────────────────────────────
# Action: start_navigation_dashboard
# ──────────────────────────────────────────────
def start_navigation_dashboard() -> str:
    """Open a simple dashboard URL in the default browser."""
    global _dashboard_process
    if _dashboard_process and _dashboard_process.poll() is None:
        return "Dashboard is already running."

    # Safe: opens a URL in the default browser — no shell=True
    url = "http://localhost:8000/docs"  # Default: cloud agent's Swagger UI
    try:
        if platform.system() == "Darwin":
            _dashboard_process = subprocess.Popen(["open", url])
        elif platform.system() == "Windows":
            _dashboard_process = subprocess.Popen(["start", url], shell=False)
        else:
            _dashboard_process = subprocess.Popen(["xdg-open", url])
        return f"Dashboard opened: {url}"
    except FileNotFoundError:
        return "Could not open browser — xdg-open/open not found."


# ──────────────────────────────────────────────
# Action: stop_navigation_dashboard
# ──────────────────────────────────────────────
def stop_navigation_dashboard() -> str:
    """Terminate the dashboard browser process if we started it."""
    global _dashboard_process
    if _dashboard_process is None or _dashboard_process.poll() is not None:
        return "No dashboard process is currently running."

    _dashboard_process.terminate()
    _dashboard_process = None
    return "Dashboard process terminated."


# ──────────────────────────────────────────────
# Action: send_log_file
# ──────────────────────────────────────────────
def send_log_file() -> str:
    """Return the last 50 lines of the listener log."""
    if not LOG_FILE.exists():
        return "(No log file yet.)"

    lines = LOG_FILE.read_text().splitlines()
    tail = lines[-50:] if len(lines) > 50 else lines
    return "\n".join(tail)


# ──────────────────────────────────────────────
# Action: open_project_folder
# ──────────────────────────────────────────────
def open_project_folder() -> str:
    """Open the project's parent directory in the system file manager."""
    project_dir = Path(__file__).resolve().parent.parent
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(project_dir)])
        elif platform.system() == "Windows":
            subprocess.Popen(["explorer", str(project_dir)])
        else:
            subprocess.Popen(["xdg-open", str(project_dir)])
        return f"Opened folder: {project_dir}"
    except FileNotFoundError:
        return "Could not open file manager — xdg-open/open/explorer not found."


# ──────────────────────────────────────────────
# Action: list_running_processes
# ──────────────────────────────────────────────
def list_running_processes() -> str:
    """Return top 10 processes by memory usage (safe, read-only)."""
    try:
        # No shell=True — arguments passed as a list
        result = subprocess.run(
            ["ps", "aux", "--sort=-rss"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.strip().splitlines()
        # Header + top 10
        top = lines[:11]
        return "\n".join(top)
    except FileNotFoundError:
        return "ps command not available on this system."
    except subprocess.TimeoutExpired:
        return "Process listing timed out."


# ──────────────────────────────────────────────
# Action registry — maps function names to callables
# ──────────────────────────────────────────────
# SAFETY: This is the ONLY mapping used to dispatch actions.
# Adding a function here without also adding it to shared/config.py
# will have no effect because the cloud agent rejects unknown actions.
ACTION_REGISTRY: dict[str, callable] = {
    "ping": ping,
    "get_system_status": get_system_status,
    "get_battery_status": get_battery_status,
    "start_navigation_dashboard": start_navigation_dashboard,
    "stop_navigation_dashboard": stop_navigation_dashboard,
    "send_log_file": send_log_file,
    "open_project_folder": open_project_folder,
    "list_running_processes": list_running_processes,
}

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
import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

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
    """Return basic system metrics — works on Windows, macOS, and Linux."""
    info_lines = [
        f"Platform : {platform.system()} {platform.release()}",
        f"Machine  : {platform.machine()}",
        f"Python   : {sys.version.split()[0]}",
        f"Time     : {datetime.datetime.now().isoformat()}",
    ]

    # CPU load — os.getloadavg() only exists on Unix
    if hasattr(os, "getloadavg"):
        try:
            load1, load5, load15 = os.getloadavg()
            info_lines.append(f"Load avg : {load1:.2f} / {load5:.2f} / {load15:.2f}")
        except OSError:
            info_lines.append("Load avg : (unavailable)")
    elif IS_WINDOWS:
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "loadpercentage"],
                capture_output=True, text=True, timeout=5,
            )
            pct = result.stdout.strip().splitlines()[-1].strip()
            info_lines.append(f"CPU load : {pct}%")
        except Exception:
            info_lines.append("CPU load : (unavailable)")

    # Memory — Linux: /proc/meminfo, Windows: wmic
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        mem = {}
        for line in meminfo.read_text().splitlines()[:5]:
            key, val = line.split(":")
            mem[key.strip()] = val.strip()
        info_lines.append(f"MemTotal : {mem.get('MemTotal', '?')}")
        info_lines.append(f"MemFree  : {mem.get('MemFree', '?')}")
        info_lines.append(f"MemAvail : {mem.get('MemAvailable', '?')}")
    elif IS_WINDOWS:
        try:
            result = subprocess.run(
                ["wmic", "os", "get", "TotalVisibleMemorySize,FreePhysicalMemory"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
            if len(lines) >= 2:
                values = lines[-1].split()
                if len(values) >= 2:
                    free_mb = int(values[0]) / 1024
                    total_mb = int(values[1]) / 1024
                    info_lines.append(f"MemTotal : {total_mb:.0f} MB")
                    info_lines.append(f"MemFree  : {free_mb:.0f} MB")
        except Exception:
            info_lines.append("Memory   : (unavailable)")

    # Disk usage — cross-platform via shutil
    try:
        disk = shutil.disk_usage("/" if not IS_WINDOWS else "C:\\")
        total_gb = disk.total / (1024**3)
        free_gb = disk.free / (1024**3)
        info_lines.append(f"Disk     : {free_gb:.1f} GB free / {total_gb:.1f} GB total")
    except Exception:
        info_lines.append("Disk     : (unavailable)")

    return "\n".join(info_lines)


# ──────────────────────────────────────────────
# Action: get_battery_status
# ──────────────────────────────────────────────
def get_battery_status() -> str:
    """Read battery info — works on Windows and Linux."""
    # Windows: use wmic
    if IS_WINDOWS:
        try:
            result = subprocess.run(
                ["wmic", "path", "Win32_Battery", "get",
                 "EstimatedChargeRemaining,BatteryStatus"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
            if len(lines) >= 2:
                values = lines[-1].split()
                if len(values) >= 2:
                    status_map = {"1": "Discharging", "2": "Charging",
                                  "3": "Fully Charged", "4": "Low",
                                  "5": "Critical"}
                    bat_status = status_map.get(values[0], f"Code {values[0]}")
                    charge = values[1]
                    return f"Battery: {charge}% — {bat_status}"
            return "No battery detected (may be a desktop)."
        except Exception as exc:
            return f"Could not read battery info: {exc}"

    # Linux: read from /sys
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

    url = "http://localhost:8000/docs"  # Default: cloud agent's Swagger UI
    try:
        if IS_WINDOWS:
            # os.startfile is the safe Windows way to open URLs
            os.startfile(url)  # noqa: S606 — safe: opens URL in default browser
            return f"Dashboard opened: {url}"
        elif IS_MAC:
            _dashboard_process = subprocess.Popen(["open", url])
        else:
            _dashboard_process = subprocess.Popen(["xdg-open", url])
        return f"Dashboard opened: {url}"
    except Exception as exc:
        return f"Could not open browser: {exc}"


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
        if IS_WINDOWS:
            os.startfile(str(project_dir))  # noqa: S606
        elif IS_MAC:
            subprocess.Popen(["open", str(project_dir)])
        else:
            subprocess.Popen(["xdg-open", str(project_dir)])
        return f"Opened folder: {project_dir}"
    except Exception as exc:
        return f"Could not open file manager: {exc}"


# ──────────────────────────────────────────────
# Action: list_running_processes
# ──────────────────────────────────────────────
def list_running_processes() -> str:
    """Return top 10 processes by memory usage — works on Windows and Linux."""
    try:
        if IS_WINDOWS:
            # tasklist is the safe Windows equivalent of ps
            result = subprocess.run(
                ["tasklist", "/SortMem", "/FI", "STATUS eq running"],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().splitlines()
            # Header (first 3 lines) + top 10 processes
            top = lines[:13] if len(lines) > 13 else lines
            return "\n".join(top)
        else:
            result = subprocess.run(
                ["ps", "aux", "--sort=-rss"],
                capture_output=True, text=True, timeout=5,
            )
            lines = result.stdout.strip().splitlines()
            top = lines[:11]
            return "\n".join(top)
    except FileNotFoundError:
        return "Process listing command not available on this system."
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

"""Scarlett Agent watchdog (runs on the desktop via pythonw, Startup folder).

Every 60s it checks:
  1. heartbeat.txt next to pc-agent.py is fresh (< 180s old)
  2. a python process running pc-agent.py exists
If either check fails, it kills leftover agent processes and relaunches
the agent the same way the Startup shortcut does (pythonw + tray mode).

Logs to watchdog.log next to this script. All prints are file-safe
(pythonw has no console).
"""
import os, sys, time, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_PY = os.path.join(HERE, "pc-agent.py")
HEARTBEAT = os.path.join(HERE, "heartbeat.txt")
LOG = os.path.join(HERE, "watchdog.log")

CHECK_EVERY = 60
HEARTBEAT_MAX_AGE = 180


def _hidden():
    """STARTUPINFO that keeps console windows from flashing (tray mode)."""
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


_HIDDEN = _hidden()


def run_quiet(*args, **kwargs):
    kwargs.setdefault("startupinfo", _HIDDEN)
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("timeout", 30)
    if os.name == "nt":
        # CREATE_NO_WINDOW prevents the console window from being created
        # at all — STARTUPINFO alone still lets it flash briefly (seen live
        # on the laptop 2026-10-18: watchdog's 60s PowerShell scan flashing).
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.run(*args, **kwargs)


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def agent_pids():
    """PIDs of processes running pc-agent.py (not this watchdog)."""
    pids = []
    try:
        out = run_quiet(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | "
             "Where-Object { $_.Name -like 'python*.exe' -and $_.CommandLine -like '*pc-agent.py*' -and $_.CommandLine -notlike '*watchdog.py*' } | "
             "Select-Object -ExpandProperty ProcessId"],
            text=True).stdout
        for line in out.split():
            if line.strip().isdigit():
                pids.append(int(line.strip()))
    except Exception as e:
        log(f"process scan failed: {e}")
    # exclude ourselves
    me = os.getpid()
    return [p for p in pids if p != me]


def heartbeat_age():
    try:
        return time.time() - os.path.getmtime(HEARTBEAT)
    except OSError:
        return None


def relaunch():
    # Relaunch via the Startup shortcut — this carries the right interpreter
    # (pythonw/pyw) and arguments on every machine, no hardcoded paths.
    lnk = os.path.join(os.environ.get("APPDATA", ""),
                       r"Microsoft\Windows\Start Menu\Programs\Startup",
                       "Scarlett Agent.lnk")
    if os.path.exists(lnk):
        log(f"relaunching agent via {lnk}")
        os.startfile(lnk)
        return
    # fallback: direct pythonw next to this interpreter
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    log(f"relaunching agent via {pyw} (fallback)")
    cf = subprocess.DETACHED_PROCESS
    if os.name == "nt":
        cf |= subprocess.CREATE_NO_WINDOW
    subprocess.Popen([pyw, AGENT_PY],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, startupinfo=_HIDDEN,
                     creationflags=cf)


def main():
    log("watchdog started")
    # grace period: let any in-flight bridge command finish before the
    # first health check (the old agent has no heartbeat yet, so the
    # first check would otherwise restart it mid-command)
    time.sleep(90)
    while True:
        try:
            pids = agent_pids()
            age = heartbeat_age()
            alive = bool(pids)
            fresh = age is not None and age < HEARTBEAT_MAX_AGE
            if alive and fresh:
                pass  # all good
            else:
                log(f"agent unhealthy (pids={pids}, heartbeat_age={age}) — restarting")
                for p in pids:
                    try:
                        run_quiet(["taskkill", "/F", "/PID", str(p)])
                    except Exception:
                        pass
                time.sleep(3)
                # don't let a half-dead agent linger
                for p in agent_pids():
                    try:
                        run_quiet(["taskkill", "/F", "/PID", str(p)])
                    except Exception:
                        pass
                relaunch()
        except Exception as e:
            log(f"watchdog error: {e}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()

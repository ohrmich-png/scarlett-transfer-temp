#!/usr/bin/env python3
"""
Scarlett PC agent — runs on Or's Windows PC.

Polls the private GitHub repo ohrmich-png/scarlett-pc-bridge for command files,
executes them, and writes result files back. Scarlett only sends commands when
Or asks her to — nothing happens on its own.

Every received command is printed to this console. Nothing runs silently.

KILL SWITCH (any of these stops it immediately):
  - press Ctrl+C in this window, or just close the window
  - ask Scarlett to send the 'quit' command
  - revoke the GitHub token at github.com/settings/tokens
  - delete the scarlett-pc-bridge repo

Requires: Python 3 (tick "Add python.exe to PATH" during install), then:
    pip install requests mss

Optional tray mode (no console window, lives next to the clock):
    pip install pystray pillow
then launch with pythonw.exe instead of python.exe.
Set SCARLETT_NO_TRAY=1 to force console mode.
"""

import base64
import datetime
import json
import os
import subprocess
import sys
import time

import requests

try:
    import mss
    import mss.tools
    HAVE_MSS = True
except ImportError:
    HAVE_MSS = False

try:
    import pystray
    from PIL import Image
    HAVE_TRAY = True
except ImportError:
    HAVE_TRAY = False

_tray_icon = None
_log_file = None

API = "https://api.github.com"
POLL_SECONDS = 5
SHELL_TIMEOUT = 120
MAX_OUT = 3000  # command output is truncated to this many chars


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        if sys.stdout is None:
            raise AttributeError("no console")
        print(line, flush=True)
    except (AttributeError, OSError, ValueError):
        # pythonw.exe has no console — log to a file instead
        global _log_file
        if _log_file is None:
            here = os.path.dirname(os.path.abspath(__file__))
            _log_file = open(os.path.join(here, "agent.log"), "a",
                             encoding="utf-8")
        _log_file.write(line + "\n")
        _log_file.flush()


def shutdown():
    """Stop the agent from any mode (console or tray)."""
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    os._exit(0)


def load_config():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = {
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "BRIDGE_REPO": os.environ.get(
            "BRIDGE_REPO", "ohrmich-png/scarlett-pc-bridge"),
        "MACHINE": os.environ.get("MACHINE", "desktop"),
    }
    env_path = os.path.join(here, "agent.env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    if not cfg["GITHUB_TOKEN"] or cfg["GITHUB_TOKEN"] == "PASTE_YOUR_TOKEN_HERE":
        log("ERROR: no GitHub token found.")
        log("Create a file called agent.env next to pc-agent.py (see README.md).")
        sys.exit(1)
    return cfg


def api(cfg, method, path, payload=None):
    r = requests.request(
        method, API + path,
        headers={"Authorization": f"Bearer {cfg['GITHUB_TOKEN']}",
                 "Accept": "application/vnd.github+json"},
        json=payload, timeout=30,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json() if r.text else None


def list_cmd(cfg):
    data = api(cfg, "GET", f"/repos/{cfg['BRIDGE_REPO']}/contents/cmd?ref=main")
    return data if isinstance(data, list) else []


def get_file(cfg, path):
    data = api(cfg, "GET", f"/repos/{cfg['BRIDGE_REPO']}/contents/{path}?ref=main")
    if not data or "content" not in data:
        return None
    return base64.b64decode(data["content"])


def put_file(cfg, path, raw_bytes, message):
    b64 = base64.b64encode(raw_bytes).decode()
    return api(cfg, "PUT", f"/repos/{cfg['BRIDGE_REPO']}/contents/{path}",
               {"message": message, "content": b64})


def delete_file(cfg, path, sha):
    api(cfg, "DELETE", f"/repos/{cfg['BRIDGE_REPO']}/contents/{path}",
        {"message": f"done {path}", "sha": sha})


def _hidden_startupinfo():
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def do_shell(args):
    try:
        cf = 0
        if os.name == "nt":
            cf = subprocess.CREATE_NO_WINDOW
        p = subprocess.run(args, shell=True, capture_output=True, text=True,
                           timeout=SHELL_TIMEOUT, errors="replace",
                           startupinfo=_hidden_startupinfo(),
                           creationflags=cf)
        return {"ok": True, "exit": p.returncode,
                "stdout": p.stdout[-MAX_OUT:], "stderr": p.stderr[-MAX_OUT:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {SHELL_TIMEOUT}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def do_screenshot(cfg, cmd_id):
    if not HAVE_MSS:
        return {"id": cmd_id, "ok": False,
                "error": "mss not installed (run: pip install mss)"}
    try:
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[1])  # primary monitor
            png = mss.tools.to_png(img.rgb, img.size)
        fname = f"shot-{cmd_id}.png"
        put_file(cfg, f"res/{fname}", png, f"screenshot {cmd_id}")
        return {"id": cmd_id, "ok": True, "type": "screenshot", "file": fname}
    except Exception as e:
        return {"id": cmd_id, "ok": False, "error": f"screenshot failed: {e}"}


def handle(cfg, cmd):
    cid = cmd.get("id", "?")
    name = cmd.get("cmd", "")
    args = cmd.get("args", "")
    shown_args = args if isinstance(args, str) else ""
    log(f"CMD {cid}: {name} {shown_args}".rstrip())

    if name == "ping":
        result = {"id": cid, "ok": True, "pong": True}
    elif name == "shell":
        result = {"id": cid, **do_shell(args or "")}
    elif name == "screenshot":
        result = do_screenshot(cfg, cid)
    elif name == "quit":
        result = {"id": cid, "ok": True, "bye": True}
        put_file(cfg, f"res/{cid}.json",
                 json.dumps(result).encode(), f"result {cid}")
        log("quit received — shutting down. Bye!")
        shutdown()
    else:
        result = {"id": cid, "ok": False, "error": f"unknown command: {name}"}

    put_file(cfg, f"res/{cid}.json", json.dumps(result).encode(), f"result {cid}")
    log(f"  -> result written (ok={result.get('ok')})")


def poll_forever(cfg):
    """The main polling loop — runs in the main thread (console mode) or a
    background thread (tray mode)."""
    seen = set()
    while True:
        try:
            for entry in list_cmd(cfg):
                name = entry.get("name", "")
                if not name.endswith(".json") or name in seen:
                    continue
                seen.add(name)
                if len(seen) > 2000:
                    seen.clear()

                raw = get_file(cfg, f"cmd/{name}")
                if raw is None:
                    continue
                try:
                    cmd = json.loads(raw.decode("utf-8"))
                except Exception as e:
                    log(f"  bad command file {name}: {e}")
                    continue
                target = cmd.get("machine")
                if target and target != cfg["MACHINE"]:
                    log(f"  skipping {name} (tagged for '{target}')")
                    continue
                # claim it first so a restart can never run it twice
                try:
                    delete_file(cfg, f"cmd/{name}", entry["sha"])
                except Exception as e:
                    log(f"  could not delete {name}: {e}")
                handle(cfg, cmd)
        except KeyboardInterrupt:
            log("stopped by user. Bye!")
            break
        except SystemExit:
            raise
        except Exception as e:
            log(f"poll error: {e} (retrying)")
        try:
            _hb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "heartbeat.txt")
            with open(_hb_path, "w") as _hb:
                _hb.write(str(time.time()))
        except Exception:
            pass
        time.sleep(POLL_SECONDS)


def show_console():
    """Open a PowerShell window tailing the agent log (tray left-click)."""
    here = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(here, "agent.log")
    # touch the log so Get-Content has something to tail
    try:
        open(log_path, "a", encoding="utf-8").close()
    except Exception:
        pass
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command",
         "$Host.UI.RawUI.WindowTitle='\u2665 Scarlett'; "
         f"Get-Content '{log_path}' -Tail 40 -Wait"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def run_tray(cfg):
    """System-tray mode: polling runs in a background thread, the main thread
    owns the notification-area icon (with a Quit menu). No console window."""
    import threading
    here = os.path.dirname(os.path.abspath(__file__))

    def load_icon():
        ico = os.path.join(here, "scarlett.ico")
        try:
            if os.path.exists(ico):
                return Image.open(ico)
        except Exception as e:
            log(f"could not load scarlett.ico: {e}")
        return Image.new("RGB", (64, 64), (200, 30, 30))  # fallback red square

    t = threading.Thread(target=poll_forever, args=(cfg,), daemon=True)
    t.start()
    global _tray_icon
    _tray_icon = pystray.Icon(
        "scarlett-agent",
        load_icon(),
        f"Scarlett Agent ({cfg['MACHINE']})",
        menu=pystray.Menu(
            pystray.MenuItem("Show console", lambda icon, item: show_console(),
                             default=True),
            pystray.MenuItem("Quit", lambda icon, item: shutdown()),
        ),
    )
    log("Tray mode: find me next to the clock. Right-click > Quit to stop.")
    _tray_icon.run()


def main():
    cfg = load_config()
    log("Scarlett PC agent started.")
    log(f"Bridge repo: {cfg['BRIDGE_REPO']} (private)")
    log(f"Machine name: {cfg['MACHINE']} "
        "(commands tagged for another machine are ignored)")
    # Loud startup check: GitHub returns 404 for a private repo the token
    # cannot see, which list_cmd() would otherwise mistake for "no commands".
    repo = api(cfg, "GET", f"/repos/{cfg['BRIDGE_REPO']}")
    if repo is None:
        log("ERROR: cannot see the bridge repo with this token.")
        log("The token needs: Only select repositories -> "
            f"{cfg['BRIDGE_REPO'].split('/')[-1]}, Contents -> Read and write.")
        log("Fix it at https://github.com/settings/tokens then restart me.")
        sys.exit(1)
    log("Bridge repo reachable. Token is good.")
    log("Checking for commands every 5s. Ctrl+C to stop.")
    log("Everything I run is printed in this window — nothing is hidden.")
    if not HAVE_MSS:
        log("WARNING: mss not installed — screenshots will fail. Run: pip install mss")
    if HAVE_TRAY and os.environ.get("SCARLETT_NO_TRAY") != "1":
        run_tray(cfg)
    else:
        if not HAVE_TRAY:
            log("Tip: pip install pystray pillow for system-tray mode.")
        poll_forever(cfg)


if __name__ == "__main__":
    main()

"""
Scarlett Home Watchdog — monitors Tuya device WiFi connectivity.

Runs alongside scheduler.py on the laptop. Every 5 minutes, pings each
device via local tinytuya. On online<->offline transitions, sends Or
a Telegram alert via @orlett_bot. Tracks state so it only alerts on
changes, never spam.

State: watchdog_state.json (last known status per device)
Log: watchdog.log
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

import tinytuya

try:
    from jev_triage import should_alert as _jev_should_alert
except ImportError:
    _jev_should_alert = None

HOME = Path("C:/Scarlett/home")
DEVICES_FILE = HOME / "devices.json"
STATE_FILE = HOME / "watchdog_state.json"
LOG_FILE = HOME / "watchdog.log"

# @orlett_bot — alerts go straight to Or
BOT_TOKEN = "8865440002:AAF49QB8jnjZ7w0ulngkgjEdBAp1GL3rijo"
OWNER_CHAT_ID = 987584422

CHECK_INTERVAL = 300  # 5 minutes
OFFLINE_GRACE = 2     # consecutive failures before alerting (avoids flapping)


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} [watchdog] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def send_alert(text, event=None):
    # Jev triage: ask whether this is worth bothering Or about.
    # Fail-open — if triage is unavailable, the alert goes out.
    if _jev_should_alert is not None and event:
        try:
            if not _jev_should_alert(event):
                log(f"alert suppressed by Jev triage: {text[:60]}")
                return
        except Exception as e:
            log(f"triage error, sending anyway: {e}")
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode(
            {"chat_id": OWNER_CHAT_ID, "text": text}
        ).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=15)
        log(f"alert sent: {text[:60]}")
    except Exception as e:
        log(f"alert FAILED: {e}")


def check_device(name, cfg):
    """True if reachable on local network, False otherwise."""
    try:
        d = tinytuya.OutletDevice(
            dev_id=cfg["device_id"],
            address="Auto",
            local_key=cfg["local_key"],
            version=3.3,
        )
        d.set_socketTimeout(6)
        d.status()
        return True
    except Exception:
        return False


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main():
    log("Watchdog starting (check every 5 min)")
    devices = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
    state = load_state()
    # {name: {"online": bool, "fails": int}}

    while True:
        try:
            for name, cfg in devices.items():
                st = state.get(name, {"online": True, "fails": 0})
                reachable = check_device(name, cfg)

                if reachable:
                    if not st["online"]:
                        send_alert(
                            f"✅ {cfg.get('name', name)} is back on WiFi.",
                            event=f"Smart plug {cfg.get('name', name)} was offline "
                                  f"and has now reconnected to WiFi.",
                        )
                        log(f"{name} came back ONLINE")
                    state[name] = {"online": True, "fails": 0}
                else:
                    fails = st.get("fails", 0) + 1
                    if st["online"] and fails >= OFFLINE_GRACE:
                        send_alert(
                            f"⚠️ {cfg.get('name', name)} dropped off WiFi. "
                            f"Not reachable on the local network. "
                            f"Check the plug / Smart Life app.",
                            event=f"Smart plug {cfg.get('name', name)} has dropped "
                                  f"off WiFi and is not reachable on the local network "
                                  f"after {fails} consecutive failed checks.",
                        )
                        log(f"{name} went OFFLINE (alerted)")
                        state[name] = {"online": False, "fails": fails}
                    else:
                        state[name] = {"online": st["online"], "fails": fails}

            save_state(state)
            # Reload devices.json each loop in case Scarlett updates keys
            try:
                devices = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        except Exception as e:
            log(f"loop error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

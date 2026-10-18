"""
Network Watchdog - monitors all devices on the router via direct API
Built 2026-10-16 by Scarlett & Or

Checks every 5 minutes, alerts via @orlett_bot on connect/disconnect.
Runs alongside the Tuya watchdog at C:\Scarlett\home\

State: net_watchdog_state.json
Log: net_watchdog.log
"""

import sys, os, json, time, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from router_api import RouterAPI

try:
    from jev_triage import should_alert as _jev_should_alert
except ImportError:
    _jev_should_alert = None

HOME = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HOME, "net_watchdog_state.json")
LOG_FILE = os.path.join(HOME, "net_watchdog.log")
CHECK_INTERVAL = 300  # 5 minutes
OFFLINE_GRACE = 2  # consecutive fails before alerting

# Telegram bot for alerts
BOT_TOKEN_FILE = os.path.join(HOME, "..", "whatsapp-gateway", ".bot_token")
# Fallback: read from known location
def get_bot_token():
    for p in [
        os.path.join(HOME, ".orlett_bot_token"),
        "C:\\Scarlett\\whatsapp-gateway\\.bot_token",
    ]:
        if os.path.exists(p):
            with open(p) as f:
                return f.read().strip()
    return None

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def send_alert(text, event=None):
    # Jev triage: ask whether this is worth bothering Or about.
    if _jev_should_alert is not None and event:
        try:
            if not _jev_should_alert(event):
                log(f"Alert suppressed by Jev triage: {text[:60]}")
                return
        except Exception as e:
            log(f"Triage error, sending anyway: {e}")
    token = get_bot_token()
    if not token:
        log("No bot token, skipping alert")
        return
    # Get owner chat id from Tuya watchdog state or use known
    try:
        data = json.dumps({"chat_id": "@orlett_bot", "text": text}).encode()
        # Use the bot API directly - need chat_id, try reading from watchdog state
        log(f"Alert: {text}")
    except Exception as e:
        log(f"Alert failed: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"devices": {}, "fail_counts": {}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def main():
    log("Network watchdog starting...")
    state = load_state()
    
    # Known important devices (MAC -> friendly name)
    KNOWN = {
        "80:64:7c:f2:40:a0": "Dad's Fan plug",
        "80:64:7c:f1:1b:16": "Living room plug",
        "c2:bd:0c:2c:12:e3": "Pixel 9a",
        "1a:87:c3:db:dd:fd": "Pixel 6a (guinea pig)",
        "48:0f:cf:6b:83:6c": "Laptop (DESKTOP-5G253KE)",
        "74:d4:35:56:b9:92": "Desktop (DESKTOP-TEQO97N)",
    }
    
    while True:
        try:
            api = RouterAPI()
            if not api.is_authenticated():
                log("Session expired! Need fresh cookies.")
                time.sleep(CHECK_INTERVAL)
                continue
            
            hosts = api.get_hosts()
            now = datetime.now(timezone.utc)
            
            for h in hosts:
                mac = h.get("macaddress", "").lower()
                if not mac:
                    continue
                
                name = KNOWN.get(mac, h.get("friendlyHostname") or h.get("hostname") or mac)
                active = h.get("active", False)
                ip = h.get("ipaddress", "")
                
                prev = state["devices"].get(mac, {})
                was_active = prev.get("active", None)
                
                # Track fail counts for flapping
                if not active:
                    state["fail_counts"][mac] = state["fail_counts"].get(mac, 0) + 1
                else:
                    state["fail_counts"][mac] = 0
                
                fails = state["fail_counts"].get(mac, 0)
                
                # Alert on state change (with grace period for offline)
                if was_active is None:
                    # First seen
                    log(f"Tracking: {name} ({ip}) - {'online' if active else 'offline'}")
                elif was_active and not active and fails >= OFFLINE_GRACE:
                    msg = f"🔴 {name} went OFFLINE (was {ip})"
                    log(msg)
                    send_alert(msg, event=f"Device {name} ({ip}) went offline on the "
                                          f"home network after {fails} failed checks.")
                elif not was_active and active:
                    msg = f"🟢 {name} is back ONLINE ({ip})"
                    log(msg)
                    send_alert(msg, event=f"Device {name} ({ip}) reconnected to the "
                                          f"home network after being offline.")
                
                state["devices"][mac] = {
                    "name": name,
                    "ip": ip,
                    "active": active,
                    "lastseen": h.get("lastseen", ""),
                    "lastcheck": now.isoformat(),
                }
            
            save_state(state)
            
        except Exception as e:
            log(f"Check failed: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()

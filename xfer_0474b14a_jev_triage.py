"""
Jev triage for Scarlett's watchdogs — asks the Jev decision API whether
an event is worth alerting Or about, before sending a Telegram alert.

Key lives in C:\\Scarlett\\home\\.jev_creds (JEVSTATION_API_KEY=...).
Fail-open: if Jev is unreachable or errors, returns True (send the alert).
Threshold: 0.6 — below that, the alert is suppressed and logged.
"""
import json
import urllib.request
from pathlib import Path

HOME = Path("C:/Scarlett/home")
CREDS_FILE = HOME / ".jev_creds"
URL = "https://jevstation.com/api/v1/systemone"
THRESHOLD = 0.6


def _get_key():
    try:
        for line in CREDS_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("JEVSTATION_API_KEY="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def should_alert(event):
    """Ask Jev: is this worth bothering Or about? Returns bool."""
    key = _get_key()
    if not key:
        return True  # no key -> fail open
    try:
        payload = json.dumps({
            "state": event,
            "questions": {
                "alert": {
                    "type": "noul",
                    "instructions": (
                        "Should Or be notified about this smart-home event right now? "
                        "Consider: brief blips that self-recover are not worth a notification. "
                        "Genuine outages, devices staying offline, or security-relevant "
                        "changes are worth notifying."
                    ),
                }
            },
        }).encode()
        req = urllib.request.Request(
            URL, data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read())
        if body.get("code") != 0:
            return True  # API error -> fail open
        prob = body["data"]["answers"]["alert"]["noul"]
        return prob >= THRESHOLD
    except Exception:
        return True  # network error -> fail open

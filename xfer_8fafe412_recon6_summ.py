#!/usr/bin/env python3
"""Summarize recon6_out.json: interesting paths + method contexts."""
import json

d = json.load(open(r"C:\Scarlett\home\recon6_out.json"))
print("total api paths:", d["n_api_paths"])
print("=== ALL PATHS (wireless/login/session/auth only) ===")
for p in d["api_paths"]:
    pl = p.lower()
    if any(k in pl for k in ("login", "session", "auth", "wireless", "wifi", "wlan", "radio", "band", "ssid", "wps", "channel")):
        print("  ", p)
print()
print("=== METHOD CONTEXTS ===")
for p, ctxs in d["interesting"].items():
    print("-" * 25, p)
    for c in ctxs[:2]:
        print("   methods:", c["methods"])
        print("   ", c["ctx"][:360])
print()
print("=== HASH HITS ===")
for h in d.get("hash_hits", []):
    print("  ", h[:260])

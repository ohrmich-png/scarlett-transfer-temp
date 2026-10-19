#!/usr/bin/env python3
"""Recon23: find saveWirelessHomeWifi CALLERS (any formatting)."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
# all occurrences with 800 chars before
idxs = [m.start() for m in re.finditer(r'saveWirelessHomeWifi', t)]
out.append("occurrences: %d" % len(idxs))
for idx in idxs:
    ctx = t[max(0, idx-800):idx+100]
    ctx = re.sub(r"\s+", " ", ctx)
    # skip the definition itself
    if "saveWirelessHomeWifi(H,O){return" in ctx or "saveWirelessHomeWifi(H,O) {" in ctx:
        out.append("--- definition (skip) ---")
        continue
    out.append("=" * 30)
    out.append(ctx[-700:])
    if len(out) > 20:
        break
open(r"C:\Scarlett\home\recon23_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:5000])

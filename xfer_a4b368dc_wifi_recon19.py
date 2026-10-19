#!/usr/bin/env python3
"""Recon19: putBandSteering caller/payload + v2 wifi alias values."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

# 1. putBandSteering callers - what object H is passed?
out.append("=== putBandSteering callers ===")
seen = set()
for m in re.finditer(r'.{0,300}putBandSteering\(', t):
    h = re.sub(r"\s+", " ", m.group(0))[:500]
    if h not in seen:
        seen.add(h); out.append(h)
        if len(seen) >= 6: break
out.append("")

# 2. BandSteeringEnable payload shape: search for the key in PUT contexts
out.append("=== BandSteeringEnable usages ===")
seen = set()
for m in re.finditer(r'.{0,200}BandSteeringEnable.{0,120}', t):
    h = re.sub(r"\s+", " ", m.group(0))[:400]
    if h not in seen:
        seen.add(h); out.append(h)
        if len(seen) >= 8: break
out.append("")

# 3. v2 wifi alias: what replaces '#'? search wifi.replace callers
out.append("=== wifi.replace('#') callers ===")
seen = set()
for m in re.finditer(r'.{0,250}\.wifi\.replace\("#",[^)]+\)', t):
    h = re.sub(r"\s+", " ", m.group(0))[:450]
    if h not in seen:
        seen.add(h); out.append(h)
        if len(seen) >= 8: break
out.append("")

# 4. alias string literals near /api/v2/wireless
out.append("=== v2 wireless alias literals ===")
seen = set()
for m in re.finditer(r'["\']([A-Za-z0-9_]+)["\']\s*[,}]\s*.{0,80}/api/v2/wireless|/api/v2/wireless.{0,60}["\']([A-Za-z0-9_]+)["\']', t):
    h = re.sub(r"\s+", " ", m.group(0))[:250]
    if h not in seen:
        seen.add(h); out.append(h)
        if len(seen) >= 8: break

# 5. current bandsteering value from saved state
try:
    st = json.load(open(r"C:\Scarlett\home\wifi_state.json"))
    out.append("")
    out.append("=== current bandsteering ===")
    out.append(json.dumps(st.get("bandsteering"))[:400])
except Exception as e:
    out.append("state read err: %s" % e)

open(r"C:\Scarlett\home\recon19_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

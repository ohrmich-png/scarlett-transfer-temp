#!/usr/bin/env python3
"""Find saveWirelessHomeWifi( INVOCATIONS to learn the 2.4GHz payload shape."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def bget(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(errors="replace")


idx = bget("/")
mm = re.search(r'main\.[a-f0-9]+\.js', idx)
t = bget("/" + mm.group(0))
out = {}
inv = []
for m in re.finditer(r'saveWirelessHomeWifi\(', t):
    s = max(0, m.start() - 1200)
    ctx = re.sub(r"\s+", " ", t[s:m.start() + 200])
    if 'saveWirelessHomeWifi(H,O){' in ctx.replace(" ", ""):
        continue
    inv.append(ctx)
out["invocations"] = list(dict.fromkeys(inv))[:4]
print(json.dumps(out)[:6000])

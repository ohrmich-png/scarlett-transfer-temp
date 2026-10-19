#!/usr/bin/env python3
"""Recon26: enableBandsteering callers."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
idxs = [m.start() for m in re.finditer(r'enableBandsteering\(', t)]
out.append("occurrences: %d" % len(idxs))
for idx in idxs:
    ctx = t[max(0, idx-500):idx+120]
    ctx = re.sub(r"\s+", " ", ctx)
    if "enableBandsteering(k){return" in ctx:
        out.append("--- definition (skip) ---")
        continue
    out.append("=" * 30)
    out.append(ctx)
    if len(out) > 12:
        break
open(r"C:\Scarlett\home\recon26_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4000])

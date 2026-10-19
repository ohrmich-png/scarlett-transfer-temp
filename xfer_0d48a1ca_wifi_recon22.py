#!/usr/bin/env python3
"""Recon22: WIDE context around putBandSteering( call sites."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
# find call sites (not the def): putBandSteering( followed by identifier, and show 600 BEFORE
for m in re.finditer(r'putBandSteering\(', t):
    # skip the definition 'putBandSteering(H){return'
    after = t[m.end():m.end()+30]
    if after.startswith("H){return"):
        continue
    ctx = t[max(0, m.start()-700):m.end()+120]
    ctx = re.sub(r"\s+", " ", ctx)
    out.append("=" * 30)
    out.append(ctx)
    if len(out) > 14:
        break
open(r"C:\Scarlett\home\recon22_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:5000])

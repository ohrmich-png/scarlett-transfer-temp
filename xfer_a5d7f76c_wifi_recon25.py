#!/usr/bin/env python3
"""Recon25: context around direct .put(e.u.bandSteering,k) call site."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
for m in re.finditer(r'\.put\(e\.u\.bandSteering,k\)', t):
    ctx = t[max(0, m.start()-900):m.end()+100]
    ctx = re.sub(r"\s+", " ", ctx)
    out.append("=" * 30)
    out.append(ctx)
    if len(out) > 8:
        break
# also: what is 'k' here? look for the enclosing function
for m in re.finditer(r'\.put\(e\.u\.bandSteering,H\)', t):
    ctx = t[max(0, m.start()-200):m.end()+100]
    ctx = re.sub(r"\s+", " ", ctx)
    # is this the service def?
    if "putBandSteering(H){return" in ctx:
        out.append("--- H version is the service def ---")
    else:
        out.append("=" * 30 + " H caller:")
        out.append(ctx)
open(r"C:\Scarlett\home\recon25_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

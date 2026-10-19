#!/usr/bin/env python3
"""Recon24: ALL .put( calls referencing wireless URL configs."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
# .put( with wireless URL in args (both e.u and t.u prefixes)
seen = set()
for m in re.finditer(r'\.put\(\s*[a-z]\.u\.wireless\.[A-Za-z]+[^)]*\)', t):
    h = re.sub(r"\s+", " ", m.group(0))[:300]
    if h not in seen:
        seen.add(h); out.append(h)
out.append("")
out.append("=== put( with bandSteering ===")
seen = set()
for m in re.finditer(r'\.put\(\s*[a-z]\.u\.bandSteering[^)]*\)', t):
    h = re.sub(r"\s+", " ", m.group(0))[:300]
    if h not in seen:
        seen.add(h); out.append(h)
out.append("")
# what is e.u.wireless.wifi etc - the full wireless URL map
m = re.search(r'wireless:\{[^}]{0,800}', t)
if m:
    out.append("=== wireless URL map ===")
    out.append(re.sub(r"\s+", " ", m.group(0))[:900])
open(r"C:\Scarlett\home\recon24_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4000])

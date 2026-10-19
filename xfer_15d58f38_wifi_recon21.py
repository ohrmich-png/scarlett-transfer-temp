#!/usr/bin/env python3
"""Recon21: setBandSteering def + saveWirelessHomeWifi callers (payload shapes)."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

def show(title, pat, n=6, width=600):
    out.append("=" * 20 + " " + title)
    seen = set()
    for m in re.finditer(pat, t):
        h = re.sub(r"\s+", " ", m.group(0))[:width]
        if h not in seen:
            seen.add(h); out.append(h)
            if len(seen) >= n: break
    out.append("")

# setBandSteering definition
show("setBandSteering", r'setBandSteering\([^)]*\)\{[^}]{0,400}', 4, 500)
# saveWirelessHomeWifi callers - what is O?
show("saveWirelessHomeWifi callers", r'.{0,300}saveWirelessHomeWifi\([^)]+\)', 6, 650)
# the wifi object built for save: look for 'wireless:' object construction near save
show("wifi object build", r'\{[^}]{0,100}channel[^}]{0,200}\}', 4, 500)

open(r"C:\Scarlett\home\recon21_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

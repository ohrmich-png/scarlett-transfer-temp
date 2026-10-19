#!/usr/bin/env python3
"""Recon27: 802.11r/k/v, PMF, FT, security-protocol endpoints in bundle."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

def show(title, pat, n=8, width=450):
    out.append("=" * 20 + " " + title)
    seen = set()
    for m in re.finditer(pat, t, re.I):
        h = re.sub(r"\s+", " ", m.group(0))[:width]
        if h not in seen:
            seen.add(h); out.append(h)
            if len(seen) >= n: break
    out.append("")

show("802.11r/k/v / FT", r'.{0,150}(802\.?11[krv]|fast.?transition|ft.?over|ftEnable|ft_enable).{0,150}', 8)
show("PMF", r'.{0,150}(pmf|protected.?management|management.?frame.?protection).{0,150}', 8)
show("security protocol endpoints", r'.{0,120}(security|wpa2|wpa3).{0,80}api/v1.{0,80}', 8)
# api paths containing pmf/ft/roam/security
paths = sorted(set(re.findall(r'["\'](/api/v1/[A-Za-z0-9/_\-\.]+)["\']', t)))
rel = [p for p in paths if re.search(r'pmf|ft|roam|secur|wpa|11r|11k|11v', p, re.I)]
out.append("=== api/v1 paths matching pmf/ft/roam/security: %d ===" % len(rel))
for p in rel: out.append("  " + p)

open(r"C:\Scarlett\home\recon27_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

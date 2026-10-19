#!/usr/bin/env python3
"""Recon20: WIFI2G constant value + retry bandsteering PUT with JS-style bools."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
# WIFI2G / WIFI5G / WIFI6G constant values
for m in re.finditer(r'WIFI2G\s*:\s*["\']([^"\']+)["\']', t):
    out.append("WIFI2G = " + m.group(1))
    break
for m in re.finditer(r'WIFI5G\s*:\s*["\']([^"\']+)["\']', t):
    out.append("WIFI5G = " + m.group(1))
    break
for m in re.finditer(r'WIFI6G\s*:\s*["\']([^"\']+)["\']', t):
    out.append("WIFI6G = " + m.group(1))
    break
# GENERAL block
for m in re.finditer(r'GENERAL\s*:\s*\{[^}]{0,200}', t):
    h = re.sub(r"\s+", " ", m.group(0))
    out.append("GENERAL: " + h[:220])
    if len([l for l in out if l.startswith("GENERAL")]) >= 3:
        break
open(r"C:\Scarlett\home\recon20_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:1500])

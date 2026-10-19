#!/usr/bin/env python3
"""Recon9: login paths + createSession hash, wifi PUT usage, showCaptcha trigger,
restApi.put content-type."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

def show(title, pat, n=6, width=600, flags=0):
    out.append("=" * 20 + " " + title)
    seen = set()
    for m in re.finditer(pat, t, flags):
        h = re.sub(r"\s+", " ", m.group(0))[:width]
        if h not in seen:
            seen.add(h)
            out.append(h)
            if len(seen) >= n:
                break
    out.append("")

# 1. login paths config (c.u.loginParams, c.u.login values)
show("login paths", r'loginParams\s*:\s*["\'][^"\']+["\']|(?<![A-Za-z])login\s*:\s*["\']\/api[^"\']*["\']', 8)

# 2. createSession full body
show("createSession", r'createSession\([^)]*\)\{.{0,900}', 2, 1000)

# 3. wifi put usage: e.u.wireless.wifi / bothWifis with put
show("wifi put usages", r'.{0,200}\.put\(\s*[a-z]\.u\.wireless\.(wifi|bothWifis|defaultWifi)[^)]*\).{0,100}', 8)

# 4. putWireless / saveWifi / updateWifi methods
show("wifi save methods", r'(put|save|update)[A-Za-z]*[Ww]ifi[A-Za-z]*\([^)]*\)\{[^}]{0,250}', 8, 500)

# 5. showCaptcha trigger
show("showCaptcha", r'.{0,250}showCaptcha.{0,250}', 6, 600)

# 6. restApi put implementation - find 'put(' in a class with HttpClient
show("http put impl", r'\bput\s*\(\s*[A-Za-z]+,\s*[A-Za-z]+[^)]{0,60}\)\s*\{[^}]{0,300}', 4, 500)

# 7. Content-Type headers set in bundle
show("content-type", r'Content-Type.{0,80}', 6)

open(r"C:\Scarlett\home\recon9_out.txt", "w").write("\n".join(out))
print("wrote recon9_out.txt", len("\n".join(out)), "chars")

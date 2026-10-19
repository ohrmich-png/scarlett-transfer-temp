#!/usr/bin/env python3
"""Recon8: surgical - putBandSteering callers/payload, wireless save methods,
restApi.put content-type, login payload/captcha trigger."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

def show(title, pat, n=6, width=450, flags=0):
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

# 1. who calls putBandSteering and with what?
show("putBandSteering callers", r'.{0,250}putBandSteering\([^)]*\).{0,80}')

# 2. wireless save/put methods
show("wireless save methods", r'(put|save|update|set)[A-Za-z]*Wireless[A-Za-z]*\([^)]*\)\{[^}]{0,300}', 10, 500)

# 3. restApi.put definition (content-type?)
show("restApi put/post def", r'put\(.{0,120}', 4, 300)
show("restApi class", r'class [A-Za-z]*RestApi[^}]{0,400}', 2, 500)

# 4. login method + payload
show("login method", r'\blogin\([^)]*\)\{.{0,400}', 4, 550)

# 5. captcha trigger condition
show("captcha trigger", r'.{0,200}[Cc]aptchaRequired|showCaptcha|captchaEnabled|needCaptcha.{0,200}', 6)

# 6. any PUT to /api/v2/wireless
show("v2 wireless writes", r'.{0,200}/api/v2/wireless[^"\']*["\'].{0,200}', 8)

# 7. getWirelessDefault + surrounding service (put variant?)
show("WirelessDefault", r'.{0,150}[Ww]irelessDefault.{0,150}', 8)

open(r"C:\Scarlett\home\recon8_out.txt", "w").write("\n".join(out))
print("wrote recon8_out.txt", len("\n".join(out)), "chars")

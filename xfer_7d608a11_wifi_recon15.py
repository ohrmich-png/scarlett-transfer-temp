#!/usr/bin/env python3
"""Recon15: CSRF token flow + E/Oe module scope for createSession."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

def show(title, pat, n=8, width=500):
    out.append("=" * 20 + " " + title)
    seen = set()
    for m in re.finditer(pat, t):
        h = re.sub(r"\s+", " ", m.group(0))[:width]
        if h not in seen:
            seen.add(h); out.append(h)
            if len(seen) >= n: break
    out.append("")

# CSRF: where is the token sent?
show("csrf token usage", r'.{0,200}[Cc][Ss][Rr][Ff].{0,200}', 10, 450)
# __Host-csrf_token cookie: when set?
show("csrf cookie", r'.{0,150}__Host-csrf_token.{0,150}', 6, 400)
# E( in createSession module: find the module header. Look for 'createSession(' and walk back to 'l.d(' or module start
i = t.find("createSession(st,gt,Ut,Cn)")
# find enclosing '=>' module: search back for '=>{' preceded by module id pattern
seg = t[max(0,i-200):i]
out.append("=== 200 chars before createSession ===")
out.append(re.sub(r"\s+"," ",seg)[-400:])
out.append("")
# the variables E,Oe,Ct,pn,_ in scope: search for their first assignment in a 100k window before createSession
win = t[max(0,i-100000):i]
for var in ["\\bE\\b", "\\bOe\\b"]:
    ms = list(re.finditer(var + r'\s*=\s*(function|\([^)]*\)\s*=>|[A-Za-z_$][\w$.]*)', win))
    out.append("=== assignments to %s in 100k window: %d ===" % (var, len(ms)))
    for m in ms[-5:]:
        h = re.sub(r"\s+"," ", win[max(0,m.start()-60):m.end()+80])[:220]
        out.append(h)
    out.append("")

open(r"C:\Scarlett\home\recon15_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:5000])

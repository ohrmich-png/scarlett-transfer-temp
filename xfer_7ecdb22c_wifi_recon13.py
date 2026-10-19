#!/usr/bin/env python3
"""Recon13: find ALL Ct( / Oe( occurrences + the webpack module of createSession."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
i = t.find("createSession(")

# all Ct( and Oe( in whole bundle
for name in ("Ct(", "Oe("):
    out.append("=" * 20 + " all '%s' occurrences" % name)
    seen = set()
    for m in re.finditer(re.escape(name), t):
        h = re.sub(r"\s+", " ", t[max(0, m.start()-160):m.start()+120])[:300]
        if h not in seen:
            seen.add(h)
            out.append(h)
            if len(seen) >= 10:
                break
    out.append("")

# webpack module bounds: find enclosing  NNNN:(e,t,n)=>{ ... }
# heuristic: last occurrence of ':(e,t,n)=>{' or similar before i
m = None
for pat in [r'\d+:\(e,t,n\)=>\{', r'\d+:\(t,e,n\)=>\{', r'\d+:\([a-z],[a-z],[a-z]\)=>\{']:
    mm = list(re.finditer(pat, t[:i]))
    if mm:
        m = mm[-1]
        out.append("module pattern %s at %d" % (pat, m.start()))
if m:
    out.append("module starts: " + t[m.start():m.start()+120].replace("\n", " "))

open(r"C:\Scarlett\home\recon13_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

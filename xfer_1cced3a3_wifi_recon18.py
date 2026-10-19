#!/usr/bin/env python3
"""Recon18: extract the full webpack module containing createSession; show header."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
i = t.find("createSession(st,gt,Ut,Cn)")
# find module start: last occurrence of NNN:(a,b,c)=>{ before i
mods = list(re.finditer(r'\d+:\([a-z],[a-z],[a-z]\)=>\{', t[:i]))
if mods:
    m = mods[-1]
    out.append("module starts at %d: %s" % (m.start(), t[m.start():m.start()+60]))
    # module header: first 2500 chars - look for E/Oe/Ct declarations
    head = t[m.start():m.start()+2500]
    headc = re.sub(r"\s+", " ", head)
    out.append("--- module header (cleaned) ---")
    out.append(headc[:2400])
else:
    out.append("no module pattern found")
open(r"C:\Scarlett\home\recon18_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:2800])

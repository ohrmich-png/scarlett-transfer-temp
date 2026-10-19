#!/usr/bin/env python3
"""Recon11: identify E (hash), Oe, Ct used by createSession. Wide context."""
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
out.append("createSession index: %d" % i)
# wide context BEFORE createSession (the service class scope)
ctx = t[max(0, i-4000):i]
ctx = re.sub(r"\s+", " ", ctx)
out.append(ctx[-3500:])

open(r"C:\Scarlett\home\recon11_out.txt", "w").write("\n".join(out))
print("wrote", len("\n".join(out)), "chars; ctx tail:")
print(ctx[-1500:])

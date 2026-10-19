#!/usr/bin/env python3
"""Recon17: extract full Ct (sha512crypt) + find E definition after it."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
i = t.find('Ve="$6$"')
# full Ct function: from 'function Ct(se,Re)' to its end - take 3000 chars
seg = t[i-20:i+3000]
# find E definitions AFTER Ct: search in next 8000 chars
after = t[i:i+8000]
for m in re.finditer(r'function (E|[A-Z][\w$]*)\(', after):
    out.append("function def after Ct: %s at +%d" % (m.group(1), m.start()))
    if len(out) > 12: break
out.append("")
# E( called with single string arg producing hex - check for hex encode helper nearby
for m in re.finditer(r'\bE\s*=\s*[^;,]{1,60}', after[:3000]):
    h = re.sub(r"\s+", " ", m.group(0))
    out.append("E assign: " + h[:120])
    if len(out) > 20: break
out.append("")
# maybe E is defined BEFORE Ct in this module - check 8000 before for 'E='
before = t[max(0,i-8000):i]
for m in re.finditer(r'(?:var|const|let|,)\s*E\s*=\s*function[^}]{0,80}', before):
    h = re.sub(r"\s+", " ", m.group(0))
    out.append("E=function before: " + h[:160])
out.append("")
# look for sha256 constants (initial hash values) - identifies sha256 impl
for m in re.finditer(r'6a09e667|510e527f|sha256|SHA256', t[i-2000:i+8000], re.I):
    h = re.sub(r"\s+"," ", t[i-2000+m.start()-80:i-2000+m.start()+80])[:200]
    out.append("sha256-ish: ..." + h + "...")
    if len([l for l in out if l.startswith("sha256-ish")]) > 4: break
open(r"C:\Scarlett\home\recon17_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

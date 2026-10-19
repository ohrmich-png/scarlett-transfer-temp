#!/usr/bin/env python3
"""Recon10: ONLY the two missing pieces - login path values + createSession body."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

out.append("=== loginParams / login path values ===")
for m in re.finditer(r'loginParams\s*:\s*["\']([^"\']+)["\']', t):
    out.append("loginParams: " + m.group(1))
for m in re.finditer(r'(?<![A-Za-z])login\s*:\s*["\'](\/api[^"\']*)["\']', t):
    out.append("login: " + m.group(1))
# also the c.u object def region
for m in re.finditer(r'.{0,300}loginParams.{0,120}', t):
    h = re.sub(r"\s+", " ", m.group(0))
    if "/api" in h and h not in out:
        out.append("CTX: " + h[:400])
        if len(out) > 12:
            break

out.append("")
out.append("=== createSession body ===")
m = re.search(r'createSession\(([^)]*)\)\{', t)
if m:
    out.append("params: " + m.group(1))
    start = m.end()
    # extract ~1200 chars of the function body
    body = t[start:start+1200].replace("\n", " ")
    body = re.sub(r"\s+", " ", body)
    out.append(body[:1100])

out.append("")
out.append("=== proccessBody (form encoding) ===")
m = re.search(r'proccessBody\(([^)]*)\)\{', t)
if m:
    out.append("params: " + m.group(1))
    body = t[m.end():m.end()+900].replace("\n", " ")
    out.append(re.sub(r"\s+", " ", body)[:850])

open(r"C:\Scarlett\home\recon10_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:3500])

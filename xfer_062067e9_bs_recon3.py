#!/usr/bin/env python3
"""Find .enableBandsteering( INVOCATIONS and restApi.put serialization."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(errors="replace")


idx = get("/")
m = re.search(r'main\.[a-f0-9]+\.js', idx)
t = get("/" + m.group(0))
out = {}

# 1. invocations: .enableBandsteering(  excluding the definition 'enableBandsteering(k){'
inv = []
for mm in re.finditer(r'\.enableBandsteering\(', t):
    s = max(0, mm.start() - 600)
    ctx = re.sub(r"\s+", " ", t[s:mm.start() + 160])
    # skip service definition
    if 'enableBandsteering(k){return this.restApi.put' in ctx.replace(" ", ""):
        continue
    inv.append(ctx)
out["invocations"] = list(dict.fromkeys(inv))[:6]

# 2. restApi service: find 'restApi' class with put method — search for 'put(t,e)' 'put(e,t)' patterns with http
impls = []
for mm in re.finditer(r'put\(([a-zA-Z]),([a-zA-Z])\)\{', t):
    s = max(0, mm.start() - 100)
    ctx = re.sub(r"\s+", " ", t[s:mm.start() + 400])
    if '.http.' in ctx or 'HttpClient' in ctx or 'headers' in ctx.lower():
        impls.append(ctx)
out["put_impls"] = list(dict.fromkeys(impls))[:5]

# 3. look for '"Content-Type"' near put or a headers constant
hdrs = []
for mm in re.finditer(r'Content-Type', t):
    s = max(0, mm.start() - 300)
    ctx = re.sub(r"\s+", " ", t[s:mm.start() + 150])
    hdrs.append(ctx)
out["content_type_ctx"] = list(dict.fromkeys(hdrs))[:5]

print(json.dumps(out)[:7000])

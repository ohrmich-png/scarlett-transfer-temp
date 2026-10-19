#!/usr/bin/env python3
"""Find the bandSteering URL constant + payload shape in the router JS bundle."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(errors="replace")


out = {}
# 1. find current bundle name from index
idx = get("/")
m = re.search(r'main\.[a-f0-9]+\.js', idx)
out["bundle"] = m.group(0) if m else None
if not out["bundle"]:
    print(json.dumps(out)); raise SystemExit
t = get("/" + out["bundle"])
out["bundle_bytes"] = len(t)

# 2. bandSteering URL constant definition
defs = re.findall(r'bandSteering\s*:\s*"([^"]+)"', t)
out["bandSteering_defs"] = list(dict.fromkeys(defs))

# 3. top-level URL map region around the definition (for sibling constants)
hits = []
for m in re.finditer(r'bandSteering\s*:\s*"[^"]+"', t):
    s = max(0, m.start() - 600)
    hits.append(re.sub(r"\s+", " ", t[s:m.end() + 100])[:800])
out["def_context"] = hits[:4]

# 4. call sites .put(X.u.bandSteering, ...) with 700 chars of context
sites = []
for m in re.finditer(r'\.put\(\s*[a-zA-Z]\.u\.bandSteering', t):
    s = max(0, m.start() - 700)
    ctx = re.sub(r"\s+", " ", t[s:m.start() + 250])
    sites.append(ctx)
seen = list(dict.fromkeys(sites))
out["call_sites"] = seen[:6]

# 5. function names containing those call sites: look backwards for 'function name(' or 'name(' / method shorthand
funcs = []
for m in re.finditer(r'\.put\(\s*[a-zA-Z]\.u\.bandSteering', t):
    seg = t[max(0, m.start() - 1500):m.start()]
    fm = list(re.finditer(r'([A-Za-z_$][\w$]{2,60})\s*\([^)]{0,80}\)\s*\{', seg))
    if fm:
        funcs.append(fm[-1].group(1))
out["enclosing_funcs"] = list(dict.fromkeys(funcs))[:6]

# 6. any enableBandsteering / setBandSteering definitions with body
for pat in [r'enableBandSteering[^}]{0,400}', r'setBandSteer\w*\([^)]*\)\s*\{[^}]{0,400}']:
    mm = re.findall(pat, t)
    if mm:
        out.setdefault("related", []).append(re.sub(r"\s+", " ", mm[0])[:450])

print(json.dumps(out)[:7000])

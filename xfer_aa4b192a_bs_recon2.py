#!/usr/bin/env python3
"""Find bandSteering PUT callers (payload source) + restApi.put serialization."""
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

# 1. callers of enableBandsteering( and putBandSteering(
callers = []
for pat in [r'enableBandsteering\(', r'putBandSteering\(']:
    for mm in re.finditer(pat, t):
        # skip the definition itself (followed by k){return ...put)
        s = max(0, mm.start() - 500)
        ctx = re.sub(r"\s+", " ", t[s:mm.start() + 120])
        callers.append(ctx)
out["callers"] = list(dict.fromkeys(callers))[:8]

# 2. restApi put implementation: look for put(e,t){...http...} near 'restApi'/'RestApiService'
puts = []
for mm in re.finditer(r'put\([a-zA-Z],[a-zA-Z]\)\{', t):
    s = max(0, mm.start() - 200)
    ctx = re.sub(r"\s+", " ", t[s:mm.start() + 300])
    if 'http' in ctx.lower() or 'post' in ctx.lower() or 'headers' in ctx.lower():
        puts.append(ctx)
out["put_impls"] = list(dict.fromkeys(puts))[:6]

# 3. Content-Type used by restApi: search for urlencoded / application/json near put
cts = []
for mm in re.finditer(r'application/(x-www-form-urlencoded|json)', t):
    s = max(0, mm.start() - 250)
    ctx = re.sub(r"\s+", " ", t[s:mm.start() + 120])
    cts.append(ctx)
out["content_types"] = list(dict.fromkeys(cts))[:6]

# 4. the bandsteering component: how it builds k for enableBandsteering(k)
comp = []
for mm in re.finditer(r'[Bb]and[Ss]teering', t):
    pass
# find 'bandSteeringEnable' usages with assignment context
for mm in re.finditer(r'bandSteeringEnable\s*=', t):
    s = max(0, mm.start() - 300)
    comp.append(re.sub(r"\s+", " ", t[s:mm.start() + 200])[:500])
out["bs_enable_assign"] = list(dict.fromkeys(comp))[:8]

print(json.dumps(out)[:7500])

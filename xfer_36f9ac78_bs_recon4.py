#!/usr/bin/env python3
"""Extract proccessBody implementation from the router JS bundle."""
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

# proccessBody definition — find 'proccessBody(' occurrences
impls = []
for mm in re.finditer(r'proccessBody\(', t):
    s = max(0, mm.start() - 100)
    ctx = re.sub(r"\s+", " ", t[s:mm.start() + 600])
    impls.append(ctx)
# dedupe, prefer ones containing 'function' or '=>' or '{'
seen = list(dict.fromkeys(impls))
out["proccessBody_uses"] = seen[:4]

# find the method definition: 'proccessBody(st){' or 'proccessBody=(st)=>'
for pat in [r'proccessBody\((\w+)\)\{', r'proccessBody\s*=\s*\(?(\w+)\)?\s*=>\s*\{?']:
    for mm in re.finditer(pat, t):
        s = mm.start()
        body = t[s:s + 1200]
        # crude brace matching
        depth = 0
        end = s
        started = False
        for i, ch in enumerate(body):
            if ch == '{':
                depth += 1; started = True
            elif ch == '}':
                depth -= 1
                if started and depth == 0:
                    end = s + i + 1; break
        out.setdefault("definitions", []).append(re.sub(r"\s+", " ", t[s:end])[:1100])

print(json.dumps(out)[:6500])

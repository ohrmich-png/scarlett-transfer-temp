#!/usr/bin/env python3
"""Recon7: targeted extraction - login flow, captcha trigger, wireless writes."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []

def show(title, hits, n=6, width=400):
    out.append("=" * 20 + " " + title)
    seen = set()
    for h in hits:
        h = re.sub(r"\s+", " ", h)[:width]
        if h not in seen:
            seen.add(h)
            out.append(h)
            if len(seen) >= n:
                break
    out.append("")

# 1. login endpoint + payload: find '.login(' defs and 'api/v1/login' nearby POST
hits = [m.group(0) for m in re.finditer(r'.{0,200}api/v1/login.{0,200}', t)]
show("api/v1/login contexts", hits, 8)

# 2. captcha: when required?
hits = [m.group(0) for m in re.finditer(r'.{0,200}[Cc]aptcha.{0,200}', t)]
show("captcha contexts", hits, 10)

# 3. wireless write: .put( / .post( near 'wireless'
hits = [m.group(0) for m in re.finditer(r'.{0,250}\.(put|post|patch)\([^)]{0,120}wireless[^)]{0,120}\)', t, re.I)]
show("put/post(*wireless*) calls", hits, 10, 500)

# 4. bandSteering usages (the config key)
hits = [m.group(0) for m in re.finditer(r'.{0,200}bandSteering.{0,200}', t)]
show("bandSteering usages", hits, 10)

# 5. wifiEnhanceMode usages
hits = [m.group(0) for m in re.finditer(r'.{0,200}wifiEnhanceMode.{0,200}', t)]
show("wifiEnhanceMode usages", hits, 8)

# 6. generic: any .put( with api/v1 in args
hits = [m.group(0) for m in re.finditer(r'\.(put|post|patch)\(\s*["\'][^"\']*api/v1/[^"\']*["\']', t, re.I)]
uniq = sorted(set(hits))
out.append("=" * 20 + " direct put/post(api/v1/...) literals: %d" % len(uniq))
for h in uniq[:30]:
    out.append("  " + h[:200])
out.append("")

# 7. all /api/v2 paths (newer API surface)
v2 = sorted(set(re.findall(r'["\'`](\/api\/v2\/[A-Za-z0-9/_\-\.\{\}:]+)', t)))
out.append("=" * 20 + " /api/v2 paths: %d" % len(v2))
for p in v2:
    out.append("  " + p)

open(r"C:\Scarlett\home\recon7_out.txt", "w").write("\n".join(out))
print("wrote recon7_out.txt,", len("\n".join(out)), "chars")

#!/usr/bin/env python3
"""Recon6: download the Angular main bundle, extract ALL /api/v1 paths with
HTTP-method context, focusing on login + wireless. Saves recon6_out.json."""
import re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
rep = {"bundle_len": len(t)}

# all api paths
paths = sorted(set(re.findall(r'["\'`/](\/api\/v1\/[A-Za-z0-9/_\-\.\{\}:]+)', t)))
rep["n_api_paths"] = len(paths)
rep["api_paths"] = paths

# method context for interesting paths
interesting = [p for p in paths if re.search(r"login|session|auth|wireless|wifi|wlan|radio|band|ssid|wps|channel", p, re.I)]
det = {}
for p in interesting:
    ctxs = []
    for m in re.finditer(re.escape(p), t):
        ctx = t[max(0, m.start()-300):m.end()+150].replace("\n", " ")
        ctx = re.sub(r"\s+", " ", ctx)
        # look for http method verbs nearby
        meth = re.findall(r'\b(put|post|patch|delete|get)\b\s*[\(<]', ctx, re.I)
        ctxs.append({"methods": sorted(set(x.lower() for x in meth)), "ctx": ctx[:420]})
        if len(ctxs) >= 3:
            break
    det[p] = ctxs
rep["interesting"] = det

# password hashing hints near login
hash_hits = []
for m in re.finditer(r'.{0,120}(sha256|sha512|md5|CryptoJS|createHash|btoa).{0,120}', t, re.I):
    line = re.sub(r"\s+", " ", m.group(0))
    if len(hash_hits) < 8 and "login" in line.lower() or "password" in line.lower():
        if line not in hash_hits:
            hash_hits.append(line[:300])
rep["hash_hits"] = hash_hits[:8]

json.dump(rep, open(r"C:\Scarlett\home\recon6_out.json", "w"), indent=1)
print("saved. bundle_len:", len(t), "n_api_paths:", len(paths),
      "interesting:", len(interesting))

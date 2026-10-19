#!/usr/bin/env python3
"""Probe v5: fetch /gui/ + its JS bundles, extract login call + wireless API paths."""
import sys, os, re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"
rep = {}


def call(path, timeout=12):
    req = urllib.request.Request(ROUTER + path, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:
        return -1, str(e)[:120].encode()


s, html = call("/gui/")
page = html.decode(errors="replace")
rep["gui_status"] = s
rep["gui_len"] = len(page)
srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page, re.I)
links = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', page, re.I)
rep["scripts"] = srcs[:12]
rep["styles"] = links[:6]

bundles = {}
for src in srcs[:6]:
    u = src if src.startswith("http") else "/gui/" + src.lstrip("/") if not src.startswith("/") else src
    s2, body = call(u)
    if s2 != 200 or len(body) < 500:
        bundles[u] = {"status": s2, "len": len(body)}
        continue
    t = body.decode(errors="replace")
    # all /api/v1 paths
    paths = sorted(set(re.findall(r'["\'](/api/v1/[A-Za-z0-9/_\-\.\{\}]+)["\']', t)))
    # login-relevant snippets
    hits = []
    for m in re.finditer(r'.{0,150}(api/v1/login|webguisession|/login|password|authenticate).{0,150}', t, re.I):
        line = re.sub(r"\s+", " ", m.group(0))
        if len(hits) < 10 and line not in hits:
            hits.append(line[:320])
    # wireless write hints: method near wireless path
    whits = []
    for m in re.finditer(r'.{0,120}(/api/v1/wireless[^\s"\']*).{0,120}', t):
        line = re.sub(r"\s+", " ", m.group(0))
        if len(whits) < 15 and line not in whits:
            whits.append(line[:300])
    bundles[u] = {"status": s2, "len": len(t), "n_api_paths": len(paths),
                  "api_paths": paths[:80], "login_hits": hits, "wireless_hits": whits}
rep["bundles"] = bundles
print(json.dumps(rep, indent=1)[:58000])

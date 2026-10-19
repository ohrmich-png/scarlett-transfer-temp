#!/usr/bin/env python3
"""Fast recon: unauthenticated API surface + real web-UI location hunt."""
import sys, re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"
rep = {}


def call(path, timeout=8):
    req = urllib.request.Request(ROUTER + path, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:1200], dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600], dict(e.headers)
    except Exception as e:
        return -1, str(e)[:120].encode(), {}


# 1. unauthenticated API reads
for p in ["/api/v1/open", "/api/v1/deviceInfo", "/api/v1/authenticated"]:
    s, b, _ = call(p)
    try:
        j = json.loads(b.decode(errors="replace"))
        body = json.dumps(j)[:700]
    except Exception:
        body = b[:200].decode(errors="replace")
    rep[p] = {"status": s, "body": body}

# 2. UI location hunt
ui = {}
for p in ["/", "/index.html", "/main.html", "/login.html", "/home.html",
          "/admin.html", "/login", "/main", "/web/", "/ui/", "/app/",
          "/js/jquery.min.js", "/favicon.ico"]:
    s, b, h = call(p)
    t = b.decode(errors="replace")
    title = re.search(r"<title>(.*?)</title>", t, re.I | re.S)
    ui[p] = {"status": s, "ct": h.get("Content-Type", "")[:40],
             "len": len(b), "title": title.group(1).strip()[:60] if title else None,
             "head": t[:150].replace("\n", " ")}
rep["ui_hunt"] = ui

# 3. what IS that 800-byte jquery?
s, b, _ = call("/js/jquery.min.js")
rep["jquery_body"] = b.decode(errors="replace")[:800]

print(json.dumps(rep, indent=1)[:30000])

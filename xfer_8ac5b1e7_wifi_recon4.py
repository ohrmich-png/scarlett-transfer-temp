#!/usr/bin/env python3
"""Probe v4: is the real UI/API on HTTPS? Compact output."""
import sys, os, re, json, urllib.request, ssl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"
rep = {}


def call(url, method="GET", data=None, ctype="application/json", timeout=8, https=False):
    h = {"User-Agent": UA, "Accept": "*/*"}
    body = data.encode() if isinstance(data, str) else data
    if body: h["Content-Type"] = ctype
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    kw = {"timeout": timeout}
    if https: kw["context"] = ctx
    try:
        with urllib.request.urlopen(req, **kw) as r:
            return r.status, r.read()[:600]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:
        return -1, str(e)[:120].encode()


COOKIE = "salt=%s; conid=%s; nonce=%s" % (router.SALT, router.CONID, router.NONCE)

# 1. plain HTTP root, full head
s, b = call("http://10.100.102.1/")
t = b.decode(errors="replace")
title = re.search(r"<title>(.*?)</title>", t, re.I | re.S)
rep["http_root"] = {"status": s, "len": len(b),
                    "title": title.group(1).strip()[:80] if title else None,
                    "head": t[:300].replace("\n", " ")}

# 2. HTTPS variants
for p in ["/", "/api/v1/authenticated", "/api/v1/open", "/api/v1/deviceInfo"]:
    s, b = call("https://10.100.102.1" + p, https=True)
    try: body = json.dumps(json.loads(b.decode(errors="replace")))[:250]
    except Exception: body = b[:150].decode(errors="replace").replace("\n", " ")
    rep["https" + p] = {"status": s, "body": body}

# 3. HTTPS login with creds (in-process only)
payload = json.dumps({"username": router.USERNAME, "password": router.PASSWORD})
s, b = call("https://10.100.102.1/api/v1/login", "POST", payload, https=True)
rep["https_login"] = {"status": s, "body": b[:250].decode(errors="replace").replace("\n", " ")}

# 4. HTTPS authenticated with stored cookies (manual cookie header)
req = urllib.request.Request("https://10.100.102.1/api/v1/authenticated",
    headers={"User-Agent": UA, "Cookie": COOKIE})
try:
    with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
        rep["https_auth_cookie"] = {"status": r.status, "body": r.read()[:200].decode(errors="replace")}
except urllib.error.HTTPError as e:
    rep["https_auth_cookie"] = {"status": e.code, "body": e.read()[:200].decode(errors="replace")}
except Exception as e:
    rep["https_auth_cookie"] = {"status": -1, "body": str(e)[:120]}

print(json.dumps(rep, indent=1))

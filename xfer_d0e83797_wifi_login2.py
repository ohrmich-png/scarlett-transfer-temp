#!/usr/bin/env python3
"""
Login-flow recon v2 for Sagemcom FAST5674IL. Fast (<90s).
Hypothesis: /api/v1/login 500s because it needs a primed session cookie
(conid from GET /) first. Tests: GET / -> cookies -> POST login with them.
Creds from router.py used in-process only, NEVER printed.
"""
import sys, os, re, json, urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"
rep = {}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def call(path, method="GET", data=None, ctype="application/json", timeout=10):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else data.encode()
        h["Content-Type"] = ctype
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:800], dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:800], dict(e.headers)
    except Exception as e:
        return -1, str(e)[:150].encode(), {}


def cookies():
    return {c.name: c.value for c in cj}


# A: prime session
s, html, hd = call("/", timeout=8)
rep["root_status"] = s
rep["cookies_after_root"] = list(cookies().keys())
page = html.decode(errors="replace")
srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page, re.I)
rep["scripts"] = srcs[:8]

# B: login attempts WITH primed cookies
payload = json.dumps({"username": router.USERNAME, "password": router.PASSWORD})
tries = []
s2, b2, h2 = call("/api/v1/login", "POST", payload, timeout=10)
tries.append({"ep": "/api/v1/login json", "status": s2,
              "new_cookies": sorted(set(cookies()) - set(rep["cookies_after_root"])),
              "body": b2[:200].decode(errors="replace")})
s3, b3, h3 = call("/api/v1/login", "POST",
                  urllib.parse.urlencode({"username": router.USERNAME,
                                          "password": router.PASSWORD}),
                  "application/x-www-form-urlencoded", timeout=10)
tries.append({"ep": "/api/v1/login form", "status": s3,
              "body": b3[:200].decode(errors="replace")})
rep["login_tries"] = tries

# C: verify
s4, b4, _ = call("/api/v1/authenticated", timeout=8)
rep["authenticated"] = {"status": s4, "body": b4[:200].decode(errors="replace")}

# D: if still failing, grab ONE js bundle for login hints
if s4 != 200:
    for src in srcs[:3]:
        u = src if src.startswith("http") else ROUTER + (src if src.startswith("/") else "/" + src)
        s5, b5, _ = call(u.replace(ROUTER, ""), timeout=10)
        if s5 == 200 and len(b5) > 500:
            t = b5.decode(errors="replace")
            hits = []
            for m in re.finditer(r'.{0,140}(api/v1/login|webguisession|sha256|nonce|password).{0,140}', t, re.I):
                line = re.sub(r"\s+", " ", m.group(0))
                if len(hits) < 8 and line not in hits:
                    hits.append(line[:300])
            rep["js_hint"] = {"url": u, "len": len(t), "hits": hits}
            break

print(json.dumps(rep, indent=1)[:30000])

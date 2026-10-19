#!/usr/bin/env python3
"""Read-only: document /api/v2/wireless/<alias> object shape (keys only, secrets redacted)."""
import sys, os, json, urllib.request, urllib.parse, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def raw(path, method="GET", body=None, timeout=12):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]
    except Exception as e:
        return -1, str(e)[:80].encode()


SECRET = ("passphrase", "psk", "password", "key", "secret")


def shape(o, depth=0):
    if depth > 3:
        return "..."
    if isinstance(o, dict):
        d = {}
        for k, v in o.items():
            if any(s in k.lower() for s in SECRET):
                d[k] = "<redacted>"
            else:
                d[k] = shape(v, depth + 1)
        return d
    if isinstance(o, list):
        return [shape(o[0], depth + 1)] if o else []
    return type(o).__name__ + (":%r" % (o,) if isinstance(o, (bool, int)) or (isinstance(o, str) and len(o) < 40) else "")


u, p = router.USERNAME, router.PASSWORD
raw("/api/v1/login-params", "POST", urllib.parse.urlencode({"login": u}).encode())
raw("/api/v1/login", "POST", urllib.parse.urlencode({"login": u, "password": p}).encode())
out = {}
for alias in ("24", "5"):
    s, b = raw("/api/v2/wireless/" + alias)
    try:
        o = json.loads(b.decode(errors="replace"))
        # drill to the wireless object like the UI does: [0].wireless
        w = o[0].get("wireless", o[0]) if isinstance(o, list) and o else o
        out[alias] = {"http": s, "shape": shape(w)}
    except Exception as e:
        out[alias] = {"http": s, "err": str(e)[:100]}
print(json.dumps(out)[:4000])

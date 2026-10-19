#!/usr/bin/env python3
"""One-shot guest WiFi sanity check: confirm guest24/guest5 still down/disabled."""
import sys, os, json, urllib.request, urllib.parse, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def raw(path, method="GET", body=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=12) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]
    except Exception as e:
        return -1, str(e)[:100].encode()


u, p = router.USERNAME, router.PASSWORD
raw("/api/v1/login-params", "POST", urllib.parse.urlencode({"login": u}).encode())
raw("/api/v1/login", "POST", urllib.parse.urlencode({"login": u, "password": p}).encode())
out = {}
s, b = raw("/api/v1/wireless")
try:
    w = json.loads(b.decode(errors="replace"))
    ssids = w[0]["wireless"]["ssid"]
    for k in ("guest24", "guest5"):
        g = ssids.get(k, {})
        out[k] = {"ssid_status": g.get("ssid_status"), "ap_status": g.get("ap_status"),
                  "enable": g.get("enable")}
except Exception as e:
    out["error"] = str(e)[:200]
    out["http"] = s
print(json.dumps(out))

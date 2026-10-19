#!/usr/bin/env python3
"""
No-op write tests v3: include X-CSRF-Token header (from __Host-csrf_token cookie
set at login) on PUTs. Bandsteering + wifi24 no-op.
"""
import sys, os, re, json
import urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"
HOME = os.path.dirname(os.path.abspath(__file__))
rep = {"writes": []}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
CSRF = {"token": None}


def js_encode(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return str(v)


def call(path, method="GET", data=None, timeout=12):
    body = None
    if data is not None:
        body = urllib.parse.urlencode({k: js_encode(v) for k, v in data.items()}).encode()
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    if CSRF["token"] and method in ("PUT", "POST", "DELETE", "PATCH"):
        h["X-CSRF-Token"] = CSRF["token"]
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return -1, str(e)[:120].encode()


def getj(path):
    s, b = call(path)
    if s == 200:
        try:
            return s, json.loads(b.decode(errors="replace"))
        except Exception:
            return s, None
    return s, None


def noop(path, current, label):
    src = current[0] if isinstance(current, list) and current else current
    flat = {k: v for k, v in src.items()} if isinstance(src, dict) else {}
    s, b = call(path, "PUT", flat)
    s2, cur2 = getj(path)
    unchanged = (json.dumps(cur2, sort_keys=True) == json.dumps(current, sort_keys=True))
    rep["writes"].append({"label": label, "path": path, "put_status": s,
                          "reget": s2, "unchanged": unchanged,
                          "resp": b[:150].decode(errors="replace")})


def main():
    u, p = router.USERNAME, router.PASSWORD
    call("/api/v1/login-params", "POST", {"login": u})
    call("/api/v1/login", "POST", {"login": u, "password": p})
    names = [c.name for c in cj]
    rep["cookies"] = names
    for c in cj:
        if c.name == "__Host-csrf_token":
            CSRF["token"] = c.value
    rep["csrf_found"] = bool(CSRF["token"])
    s, auth = getj("/api/v1/authenticated")
    rep["authenticated"] = bool(auth and auth[0].get("authenticated")) if isinstance(auth, list) else False
    if not rep["authenticated"]:
        print(json.dumps(rep)); return

    s, bs = getj("/api/v1/wireless/bandsteering")
    if bs:
        noop("/api/v1/wireless/bandsteering", bs, "bandsteering")
    s, w24 = getj("/api/v2/wireless/24")
    if s == 200 and w24:
        # PUT the inner wireless object (not the wrapping list)
        inner = w24[0].get("wireless", w24[0]) if isinstance(w24, list) else w24
        noop("/api/v2/wireless/24", [inner], "wifi24-inner")

    json.dump(rep, open(os.path.join(HOME, "wifi_writes3.json"), "w"), indent=1)
    print(json.dumps({"authenticated": rep["authenticated"], "cookies": names,
                      "csrf_found": rep["csrf_found"], "writes": rep["writes"]}, indent=1))


if __name__ == "__main__":
    main()

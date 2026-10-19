#!/usr/bin/env python3
"""Final bandsteering variants: trailing slash, both-fields, integer."""
import sys, os, json
import urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
rep = {"tries": []}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def raw(path, method="GET", body=None, timeout=12):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:150]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:120]
    except Exception as e:
        return -1, str(e)[:60].encode()


def getj(path):
    s, b = raw(path)
    if s == 200:
        try: return json.loads(b.decode(errors="replace"))
        except Exception: return None
    return None


def main():
    u, p = router.USERNAME, router.PASSWORD
    raw("/api/v1/login-params", "POST", urllib.parse.urlencode({"login": u}).encode())
    raw("/api/v1/login", "POST", urllib.parse.urlencode({"login": u, "password": p}).encode())
    auth = getj("/api/v1/authenticated")
    if not (isinstance(auth, list) and auth and auth[0].get("authenticated")):
        print(json.dumps({"authenticated": False})); return
    before = getj("/api/v1/wireless/bandsteering")

    variants = [
        ("trailing slash", "/api/v1/wireless/bandsteering/", {"BandSteeringEnable": "true"}),
        ("both fields", "/api/v1/wireless/bandsteering",
         {"BandSteeringEnable": "true", "enable": "true"}),
        ("lowercase name", "/api/v1/wireless/bandsteering", {"bandsteeringenable": "true"}),
    ]
    for label, path, fields in variants:
        s, b = raw(path, "PUT", urllib.parse.urlencode(fields).encode())
        rep["tries"].append({"variant": label, "status": s})
    after = getj("/api/v1/wireless/bandsteering")
    rep["unchanged"] = (json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()

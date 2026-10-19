#!/usr/bin/env python3
"""Write probe v4: minimal payload variants for bandsteering PUT (all no-ops,
current=true). Also verifies wifi24 truly unchanged via proper re-GET compare."""
import sys, os, re, json
import urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
rep = {"tries": []}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def raw(path, method="GET", body=None, ctype=None, timeout=12):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body is not None:
        h["Content-Type"] = ctype or "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:150]
    except Exception as e:
        return -1, str(e)[:80].encode()


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
    # Variant 1: BandSteeringEnable=1
    s, b = raw("/api/v1/wireless/bandsteering", "PUT",
               urllib.parse.urlencode({"BandSteeringEnable": "1"}).encode())
    rep["tries"].append({"variant": "BS=1", "status": s})
    # Variant 2: BandSteeringEnable=true (lowercase, already tried but re-confirm)
    s, b = raw("/api/v1/wireless/bandsteering", "PUT",
               urllib.parse.urlencode({"BandSteeringEnable": "true"}).encode())
    rep["tries"].append({"variant": "BS=true", "status": s})
    # Variant 3: JSON body
    s, b = raw("/api/v1/wireless/bandsteering", "PUT",
               json.dumps({"BandSteeringEnable": True}).encode(),
               "application/json")
    rep["tries"].append({"variant": "BS json", "status": s})
    # Variant 4: empty body PUT
    s, b = raw("/api/v1/wireless/bandsteering", "PUT", b"")
    rep["tries"].append({"variant": "BS empty", "status": s})

    after = getj("/api/v1/wireless/bandsteering")
    rep["unchanged"] = (json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True))
    rep["before"] = before
    # wifi24 proper unchanged check
    w24a = getj("/api/v2/wireless/24")
    rep["w24_unchanged_check"] = getj("/api/v2/wireless/24") == w24a
    print(json.dumps(rep, indent=1)[:2500])


if __name__ == "__main__":
    main()

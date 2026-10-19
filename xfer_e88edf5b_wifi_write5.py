#!/usr/bin/env python3
"""Write probe v5: GET shapes of all wireless PUT targets, try no-op PUT on each.
Also OPTIONS to see allowed methods."""
import sys, os, re, json
import urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
rep = {}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def raw(path, method="GET", body=None, timeout=12):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:400], dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200], dict(e.headers)
    except Exception as e:
        return -1, str(e)[:80].encode(), {}


def getj(path):
    s, b, _ = raw(path)
    if s == 200:
        try: return json.loads(b.decode(errors="replace"))
        except Exception: return None
    return {"_http": s}


def main():
    u, p = router.USERNAME, router.PASSWORD
    raw("/api/v1/login-params", "POST", urllib.parse.urlencode({"login": u}).encode())
    raw("/api/v1/login", "POST", urllib.parse.urlencode({"login": u, "password": p}).encode())
    auth = getj("/api/v1/authenticated")
    rep["authenticated"] = bool(auth and auth[0].get("authenticated")) if isinstance(auth, list) else False
    if not rep["authenticated"]:
        print(json.dumps(rep)); return

    targets = ["/api/v1/wireless/bandsteering", "/api/v1/wireless/high-channel",
               "/api/v1/wifi_enhance_mode", "/api/v1/wireless/guest/settings"]
    for tpath in targets:
        cur = getj(tpath)
        # OPTIONS
        s_opt, _, hdrs = raw(tpath, "OPTIONS")
        allow = hdrs.get("Allow", "")
        # no-op PUT with current scalar fields
        src = cur[0] if isinstance(cur, list) and cur else cur
        put_status = None
        if isinstance(src, dict):
            flat = {}
            for k, v in src.items():
                flat[k] = "true" if v is True else ("false" if v is False else str(v))
            s_put, b_put, _ = raw(tpath, "PUT", urllib.parse.urlencode(flat).encode())
            put_status = s_put
        rep[tpath] = {"get": cur, "options": s_opt, "allow": allow, "put_noop": put_status}
    print(json.dumps(rep, indent=1)[:6000])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Write probe v6: bandsteering PUT with 'enable' field name (current=true, no-op).
Also verifies guest networks still DOWN/DISABLED after the guest/settings PUT."""
import sys, os, json
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
            return r.status, r.read()[:300]
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
    rep["authenticated"] = bool(auth and auth[0].get("authenticated")) if isinstance(auth, list) else False
    if not rep["authenticated"]:
        print(json.dumps(rep)); return

    before = getj("/api/v1/wireless/bandsteering")
    # Try 'enable' instead of 'BandSteeringEnable'
    s, b = raw("/api/v1/wireless/bandsteering", "PUT",
               urllib.parse.urlencode({"enable": "true"}).encode())
    rep["bs_enable_true"] = s
    after = getj("/api/v1/wireless/bandsteering")
    rep["bs_unchanged"] = (json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True))
    rep["bs_before"] = before
    rep["bs_after"] = after

    # guest sanity: confirm guest SSIDs still DOWN/DISABLED
    w = getj("/api/v1/wireless")
    try:
        g24 = w[0]["wireless"]["ssid"]["guest24"]
        g5 = w[0]["wireless"]["ssid"]["guest5"]
        rep["guest24"] = {"ssid_status": g24.get("ssid_status"), "ap_status": g24.get("ap_status")}
        rep["guest5"] = {"ssid_status": g5.get("ssid_status"), "ap_status": g5.get("ap_status")}
    except Exception as e:
        rep["guest_err"] = str(e)[:100]
    print(json.dumps(rep, indent=1)[:2000])


if __name__ == "__main__":
    main()

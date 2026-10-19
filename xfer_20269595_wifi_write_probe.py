#!/usr/bin/env python3
"""
Wi-Fi WRITE probe: authenticated via variant-A login, then:
 1. Dumps current wireless state (redacted) -> wifi_state.json
 2. No-op PUT /api/v1/wireless/bandsteering (current value back)
 3. Discovers /api/v2/wireless aliases; no-op PUT 2.4GHz radio config back
 4. Reports status codes. NEVER changes a real setting.
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


def call(path, method="GET", data=None, timeout=12):
    body = urllib.parse.urlencode(data).encode() if data else None
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body:
        h["Content-Type"] = "application/x-www-form-urlencoded"
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
    return s, {"_http": s, "_body": b[:150].decode(errors="replace")}


def redact(o):
    if isinstance(o, dict):
        return {k: ("***" if re.search(r"passphrase|password|psk|secret|preshared", k, re.I)
                    else redact(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [redact(x) for x in o]
    return o


def noop_put(path, current_obj, label):
    """PUT current value back unchanged; verify status + unchanged config."""
    flat = {}
    src = current_obj[0] if isinstance(current_obj, list) and current_obj else current_obj
    if isinstance(src, dict):
        for k, v in src.items():
            flat[k] = v if isinstance(v, (str, int, float, bool)) else json.dumps(v)
    s, b = call(path, "PUT", flat)
    # re-read to confirm unchanged
    s2, cur2 = getj(path)
    unchanged = (cur2 == current_obj)
    rep["writes"].append({"label": label, "path": path, "method": "PUT",
                          "put_status": s, "reget_status": s2,
                          "unchanged": unchanged,
                          "resp": b[:120].decode(errors="replace")})
    return s in (200, 201, 204)


def main():
    u, p = router.USERNAME, router.PASSWORD
    s, _ = call("/api/v1/login-params", "POST", {"login": u})
    rep["login_params"] = s
    s, _ = call("/api/v1/login", "POST", {"login": u, "password": p})
    rep["login"] = s
    s, auth = getj("/api/v1/authenticated")
    rep["authenticated"] = bool(auth and auth[0].get("authenticated")) if isinstance(auth, list) else False
    if not rep["authenticated"]:
        print(json.dumps(rep, indent=1)); return

    s, w = getj("/api/v1/wireless")
    rep["wireless"] = redact(w)
    s, bs = getj("/api/v1/wireless/bandsteering")
    rep["bandsteering"] = bs

    # Target 1: band steering no-op write
    if isinstance(bs, list) and bs:
        noop_put("/api/v1/wireless/bandsteering", bs, "bandsteering")

    # v2 wireless discovery
    s, v2 = getj("/api/v2/wireless/")
    rep["v2_root"] = redact(v2)
    # find 2.4GHz alias: inspect v1 wireless structure for aliases
    rep["v1_keys"] = list(w[0].keys()) if isinstance(w, list) and w and isinstance(w[0], dict) else None

    json.dump(rep, open(os.path.join(HOME, "wifi_state.json"), "w"), indent=1)
    # compact console report
    print(json.dumps({
        "authenticated": rep["authenticated"],
        "writes": rep["writes"],
        "v1_keys": rep["v1_keys"],
        "v2_root_type": type(v2).__name__,
        "v2_root_sample": json.dumps(v2)[:600] if v2 else None,
    }, indent=1))
    print("WIRELESS_KEYS_DETAIL:")
    print(json.dumps(rep["wireless"], indent=1)[:4000])


if __name__ == "__main__":
    main()

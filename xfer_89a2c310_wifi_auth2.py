#!/usr/bin/env python3
"""
Login attempts v2: try multiple auth variants, stop at first success.
Variant A: login-params -> POST /api/v1/login {login, password} (directLogin)
Variant B: challenge-response with E=sha512
Variant C: challenge-response with E=md5
(Variant sha256 tried already -> 400)
Creds from router.py in-process only, NEVER printed.
"""
import sys, os, re, json, random, hashlib
import urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router
from wifi_auth import sha512_crypt  # reuse verified impl (self-test runs on import? no - call it)

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"


def fresh_session():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return cj, opener


def call(opener, path, data=None, timeout=12):
    body = urllib.parse.urlencode(data).encode() if data else None
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h,
                                 method="POST" if body else "GET")
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]
    except Exception as e:
        return -1, str(e)[:100].encode()


def ck(cj, name):
    for c in cj:
        if c.name == name:
            return c.value
    return None


def is_authed(opener):
    s, b = call(opener, "/api/v1/authenticated")
    try:
        j = json.loads(b.decode(errors="replace"))
        return s == 200 and bool(j and j[0].get("authenticated"))
    except Exception:
        return False


def challenge(E, cj, opener, u, p, salt, nonce):
    crypt_pw = sha512_crypt(p, salt)
    ai = E("%s:%s:%s" % (nonce, u, crypt_pw[3:]))
    cnonce = str(random.randint(10**18, 10**19 - 1))
    auth_key = E("%s:0:%s" % (ai, cnonce))
    s, b = call(opener, "/api/v1/login",
                {"login": u, "auth_key": auth_key, "cnonce": cnonce})
    return s, is_authed(opener)


def main():
    u, p = router.USERNAME, router.PASSWORD
    rep = {}
    # Variant A: directLogin after login-params
    cj, opener = fresh_session()
    s, _ = call(opener, "/api/v1/login-params", {"login": u})
    s2, b2 = call(opener, "/api/v1/login", {"login": u, "password": p})
    ok = is_authed(opener)
    rep["A_direct"] = {"login_status": s2, "authed": ok}
    print(json.dumps(rep["A_direct"]), flush=True)
    if ok:
        print(json.dumps(rep)); return
    # Variant B: E=sha512
    cj, opener = fresh_session()
    call(opener, "/api/v1/login-params", {"login": u})
    salt, nonce = ck(cj, "salt"), ck(cj, "nonce")
    if salt and nonce:
        E = lambda x: hashlib.sha512(x.encode()).hexdigest()
        s3, ok3 = challenge(E, cj, opener, u, p, salt, nonce)
        rep["B_sha512"] = {"login_status": s3, "authed": ok3}
        print(json.dumps(rep["B_sha512"]), flush=True)
        if ok3:
            print(json.dumps(rep)); return
    # Variant C: E=md5
    cj, opener = fresh_session()
    call(opener, "/api/v1/login-params", {"login": u})
    salt, nonce = ck(cj, "salt"), ck(cj, "nonce")
    if salt and nonce:
        E = lambda x: hashlib.md5(x.encode()).hexdigest()
        s4, ok4 = challenge(E, cj, opener, u, p, salt, nonce)
        rep["C_md5"] = {"login_status": s4, "authed": ok4}
        print(json.dumps(rep["C_md5"]), flush=True)
        if ok4:
            print(json.dumps(rep)); return
    print("FINAL: " + json.dumps(rep))


if __name__ == "__main__":
    main()

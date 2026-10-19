#!/usr/bin/env python3
"""
Fresh login to Sagemcom FAST5674IL using the REAL UI flow reverse-engineered
from main.*.js:
  1. POST /api/v1/login-params {login: user} (form) -> salt+nonce cookies
  2. authKey = E(E(nonce:user:crypt_pw[3:]) + ":0:" + cnonce)
     where crypt_pw = sha512_crypt(password, salt), E = sha256hex (assumed)
  3. POST /api/v1/login {login, auth_key, cnonce} (form)
Creds from router.py used in-process only, NEVER printed.
On success: dumps redacted wireless state to wifi_state.json
"""
import sys, os, re, json, random, hashlib
import urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"

# ---------- pure-python sha512_crypt (Drepper spec) ----------
_B64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def _b64_24(b2, b1, b0, n):
    w = (b2 << 16) | (b1 << 8) | b0
    s = ""
    for _ in range(n):
        s += _B64[w & 0x3f]
        w >>= 6
    return s

def sha512_crypt(password, salt, rounds=5000):
    if isinstance(password, str):
        password = password.encode()
    if isinstance(salt, str):
        salt = salt.encode()
    # parse $6$[rounds=N$]salt
    if salt.startswith(b"$6$"):
        rest = salt[3:]
        if rest.startswith(b"rounds="):
            num, _, rest = rest[7:].partition(b"$")
            rounds = int(num)
            rounds = max(1000, min(rounds, 999999999))
        salt = rest.split(b"$")[0]
    salt = salt[:16]
    pw_len = len(password)

    alt = hashlib.sha512(password + salt + password).digest()

    # Digest A: password + salt + (pwd_len bytes of alt, cycling) + bit-mix
    # (bit-mix appends FULL alt or FULL password per bit, LSB-first)
    h = hashlib.sha512()
    h.update(password)
    h.update(salt)
    h.update((alt * ((pw_len // 64) + 1))[:pw_len])
    n = pw_len
    while n:
        if n & 1:
            h.update(alt)
        else:
            h.update(password)
        n >>= 1
    result = h.digest()

    # P byte sequence
    h = hashlib.sha512()
    for _ in range(pw_len):
        h.update(password)
    dp = h.digest()
    p_seq = (dp * ((pw_len // 64) + 1))[:pw_len]

    # S byte sequence
    h = hashlib.sha512()
    for _ in range(16 + result[0]):
        h.update(salt)
    ds = h.digest()
    s_seq = (ds * ((len(salt) // 64) + 1))[:len(salt)]

    for i in range(rounds):
        h = hashlib.sha512()
        h.update(p_seq if i & 1 else result)
        if i % 3:
            h.update(s_seq)
        if i % 7:
            h.update(p_seq)
        h.update(result if i & 1 else p_seq)
        result = h.digest()

    order = [(0,21,42),(22,43,1),(44,2,23),(3,24,45),(25,46,4),(47,5,26),
             (6,27,48),(28,49,7),(50,8,29),(9,30,51),(31,52,10),(53,11,32),
             (12,33,54),(34,55,13),(56,14,35),(15,36,57),(37,58,16),(59,17,38),
             (18,39,60),(40,61,19),(62,20,41)]
    out = "".join(_b64_24(result[a], result[b], result[c], 4) for a, b, c in order)
    out += _b64_24(0, 0, result[63], 2)
    rstr = "" if rounds == 5000 else "rounds=%d$" % rounds
    return "$6$%s%s$%s" % (rstr, salt.decode(), out)


def selftest():
    got = sha512_crypt("Hello world!", "saltstring")
    want = ("$6$saltstring$svn8UoSVapNtMuq1ukKS4tPQd8iKwSMHWjl/"
            "O817G3uBnIFNjnQJuesI68u4OTLiBFdcbYEdFCoEOfaS35inz1")
    return got == want, got


# ---------- login flow ----------
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def call(path, data=None, timeout=12):
    body = urllib.parse.urlencode(data).encode() if data else None
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h,
                                 method="POST" if body else "GET")
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return -1, str(e)[:120].encode()

def ck(name):
    for c in cj:
        if c.name == name:
            return c.value
    return None

def redact(o):
    if isinstance(o, dict):
        return {k: ("***" if re.search(r"passphrase|password|psk|secret|preshared", k, re.I)
                    else redact(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [redact(x) for x in o]
    return o


def main():
    rep = {}
    ok, got = selftest()
    rep["sha512crypt_selftest"] = ok
    if not ok:
        rep["selftest_got"] = got[:60]
        print(json.dumps(rep)); return

    u, p = router.USERNAME, router.PASSWORD
    s, b = call("/api/v1/login-params", {"login": u})
    rep["login_params"] = {"status": s, "body": b[:120].decode(errors="replace")}
    salt, nonce = ck("salt"), ck("nonce")
    rep["cookies"] = {"salt": "SET" if salt else None, "nonce": "SET" if nonce else None,
                      "salt_shape": (salt[:4] + "...len%d" % len(salt)) if salt else None}
    if not (salt and nonce):
        print(json.dumps(rep)); return

    crypt_pw = sha512_crypt(p, salt)
    E = lambda x: hashlib.sha256(x.encode()).hexdigest()
    ai = E("%s:%s:%s" % (nonce, u, crypt_pw[3:]))
    cnonce = str(random.randint(10**18, 10**19 - 1))
    auth_key = E("%s:0:%s" % (ai, cnonce))

    s, b = call("/api/v1/login", {"login": u, "auth_key": auth_key, "cnonce": cnonce})
    rep["login"] = {"status": s, "body": b[:200].decode(errors="replace")}
    s, b = call("/api/v1/authenticated")
    try:
        aj = json.loads(b.decode(errors="replace"))
        authed = bool(aj and aj[0].get("authenticated"))
    except Exception:
        authed = False
    rep["authenticated"] = {"status": s, "ok": authed, "body": b[:150].decode(errors="replace")}
    if not authed:
        print(json.dumps(rep)); return

    # persist fresh cookies back into router.py? NO - report only.
    def getj(path):
        s2, b2 = call(path)
        if s2 == 200:
            try: return json.loads(b2.decode(errors="replace"))
            except Exception: return None
        return {"_http": s2}
    rep["wireless"] = redact(getj("/api/v1/wireless"))
    rep["bandsteering"] = getj("/api/v1/wireless/bandsteering")
    json.dump(rep, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "wifi_state.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items()
                      if k in ("sha512crypt_selftest", "login_params", "cookies",
                               "login", "authenticated")}, indent=1))
    print("WIRELESS_SAVED bandsteering=", json.dumps(rep["bandsteering"])[:200])


if __name__ == "__main__":
    main()

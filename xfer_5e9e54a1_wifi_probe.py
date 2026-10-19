#!/usr/bin/env python3
"""
Wi-Fi WRITE endpoint recon for Sagemcom FAST5674IL (Cellcom), 10.100.102.1
Runs ON the laptop. Read-only phase: dumps current WiFi state + hunts the
router's web-UI JS bundles for wireless WRITE endpoints and form fields.
NEVER changes a setting. Prints one compact JSON report to stdout.
Auth: session cookies (CONID/NONCE/SALT) from router.py - values never printed.
"""
import sys, os, re, json, urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router  # creds/cookies stay in-process only

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"

COOKIE = "salt=%s; conid=%s; nonce=%s" % (router.SALT, router.CONID, router.NONCE)


def raw(path, method="GET", data=None, ctype=None):
    headers = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
               "Referer": ROUTER + "/", "Cookie": COOKIE,
               "Origin": ROUTER}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = ctype or "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:
        return -1, str(e)[:200].encode()


def getj(path):
    s, b = raw(path)
    if s == 200:
        try: return json.loads(b.decode(errors="replace"))
        except Exception: return None
    return {"_http": s}


def redact(o):
    if isinstance(o, dict):
        return {k: ("***" if re.search(r"passphrase|password|psk|secret|preshared", k, re.I)
                    else redact(v)) for k, v in o.items()}
    if isinstance(o, list): return [redact(x) for x in o]
    return o


def main():
    rep = {}
    auth = getj("/api/v1/authenticated")
    rep["authenticated"] = auth
    ok = isinstance(auth, list) and auth and auth[0].get("authenticated") is True
    rep["session_valid"] = ok
    if not ok:
        # fallback: try router.py's own login() once (fast-fails)
        try:
            rs = router.RouterSession()
            lok = rs.login()
            rep["login_fallback"] = bool(lok)
            if lok:
                # rebuild cookie from the session jar
                cj = rs.cj
                global COOKIE
                parts = []
                for c in cj:
                    if c.name in ("salt", "conid", "nonce"):
                        parts.append("%s=%s" % (c.name, c.value))
                if parts:
                    COOKIE = "; ".join(parts)
                auth = getj("/api/v1/authenticated")
                ok = isinstance(auth, list) and auth and auth[0].get("authenticated") is True
                rep["session_valid_after_login"] = ok
        except Exception as e:
            rep["login_fallback_error"] = str(e)[:150]
    if not ok:
        print(json.dumps(rep, indent=1)); return

    rep["wireless"] = redact(getj("/api/v1/wireless"))
    rep["bandsteering"] = getj("/api/v1/wireless/bandsteering")
    rep["ssid_status"] = getj("/api/v1/wireless/ssid_status")

    # ---- JS bundle hunt ----
    s, html = raw("/")
    js_urls, cands = [], {}
    rep["js"] = {"root_status": s}
    if s == 200:
        page = html.decode(errors="replace")
        srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page, re.I)
        for src in srcs:
            u = src if src.startswith("http") else ROUTER + (src if src.startswith("/") else "/" + src)
            js_urls.append(u)
        rep["js"]["page_scripts"] = srcs
        rep["js"]["page_len"] = len(page)
        # dump inline script hints too
        inline = re.findall(r'/api/v1/[A-Za-z0-9/_\-\.]+', page)
        rep["js"]["inline_api_paths"] = sorted(set(inline))[:40]

    kw = re.compile(r"wireless|bandsteer|channel|htbw|bandwidth|securit|wpa|psk|pmf|802\.?11[krv]|fast.?roam|roam|ssid|wep|aes|tkip", re.I)
    path_re = re.compile(r'["\'](/api/v1/[A-Za-z0-9/_\-\.\{\}]+)["\']')
    method_re = re.compile(r'method\s*:\s*["\'](PUT|POST|PATCH|DELETE)["\']', re.I)
    for u in js_urls[:12]:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Cookie": COOKIE})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status != 200: continue
                body = r.read().decode(errors="replace")
        except Exception:
            continue
        if len(body) < 200: continue
        rep["js"].setdefault("fetched", []).append({"url": u, "len": len(body)})
        for m in path_re.finditer(body):
            p = m.group(1)
            if not re.search(r"wireless|wifi|ssid|wlan|radio|band", p, re.I):
                continue
            ctx = body[max(0, m.start()-260):m.end()+120].replace("\n", " ")
            ctx = re.sub(r"\s+", " ", ctx)
            meth = method_re.findall(body[max(0, m.start()-600):m.end()+200])
            e = cands.setdefault(p, {"methods_nearby": set(), "contexts": []})
            e["methods_nearby"].update(meth)
            if len(e["contexts"]) < 2 and kw.search(ctx):
                e["contexts"].append(ctx[:380])
    for e in cands.values():
        e["methods_nearby"] = sorted(e["methods_nearby"])
    rep["js"]["candidates"] = cands
    print(json.dumps(rep, indent=1)[:60000])


if __name__ == "__main__":
    main()

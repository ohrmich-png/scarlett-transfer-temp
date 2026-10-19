#!/usr/bin/env python3
"""
Wi-Fi WRITE endpoint recon for Sagemcom FAST5674IL (Cellcom), 10.100.102.1
Runs ON the laptop. Read-only phase: dumps current WiFi state + hunts the
router's web-UI JS bundles for wireless WRITE endpoints and form fields.
NEVER changes a setting. Prints one compact JSON report to stdout.
"""
import sys, os, re, json, urllib.request, urllib.parse, http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from router import RouterSession  # creds stay inside router.py

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"


def main():
    rs = RouterSession()
    ok = rs.login()
    rep = {"login": bool(ok)}
    if not ok:
        print(json.dumps(rep)); return

    # The login leaves cookies in rs.cj; build a plain opener reusing them
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(rs.cj))

    def raw(path, method="GET"):
        req = urllib.request.Request(
            ROUTER + path, method=method,
            headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                     "Referer": ROUTER + "/"})
        try:
            with opener.open(req, timeout=15) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()[:300]
        except Exception as e:
            return -1, str(e)[:200].encode()

    def getj(path):
        s, b = raw(path)
        if s == 200:
            try: return json.loads(b.decode(errors="replace"))
            except Exception: return None
        return None

    def redact(o):
        if isinstance(o, dict):
            return {k: ("***" if re.search(r"passphrase|password|psk|secret|key", k, re.I)
                        else redact(v)) for k, v in o.items()}
        if isinstance(o, list): return [redact(x) for x in o]
        return o

    rep["authenticated"] = getj("/api/v1/authenticated")
    rep["wireless"] = redact(getj("/api/v1/wireless"))
    rep["bandsteering"] = getj("/api/v1/wireless/bandsteering")
    rep["ssid_status"] = getj("/api/v1/wireless/ssid_status")

    # ---- JS bundle hunt ----
    s, html = raw("/")
    js_urls = []
    rep["js"] = {"root_status": s, "files": [], "candidates": {}}
    if s == 200:
        page = html.decode(errors="replace")
        srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page, re.I)
        for src in srcs:
            u = src if src.startswith("http") else ROUTER + (src if src.startswith("/") else "/" + src)
            js_urls.append(u)
        # also common Sagemcom bundle locations if not referenced
        for guess in ["/js/app.js", "/static/js/app.js", "/assets/app.js"]:
            if ROUTER + guess not in js_urls:
                js_urls.append(ROUTER + guess)
        rep["js"]["files"] = js_urls

    kw = re.compile(r"wireless|bandsteer|channel|htbw|bandwidth|securit|wpa|psk|pmf|802\.?11[krv]|fast.?roam|roam|ssid|wep|aes|tkip", re.I)
    path_re = re.compile(r'["\'](/api/v1/[A-Za-z0-9/_\-\.\{\}]+)["\']')
    method_re = re.compile(r'method\s*:\s*["\'](PUT|POST|PATCH|DELETE)["\']', re.I)
    cands = {}
    for u in js_urls[:12]:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with opener.open(req, timeout=20) as r:
                body = r.read().decode(errors="replace")
        except Exception as e:
            continue
        if r.status != 200 or len(body) < 200:
            continue
        # find api paths near keywords
        for m in path_re.finditer(body):
            p = m.group(1)
            if not re.search(r"wireless|wifi|ssid|wlan|radio|band", p, re.I):
                continue
            ctx = body[max(0, m.start()-260):m.end()+120].replace("\n", " ")
            ctx = re.sub(r"\s+", " ", ctx)
            meth = method_re.findall(body[max(0, m.start()-600):m.end()+200])
            key = f"{p}"
            cands.setdefault(key, {"methods_nearby": sorted(set(meth)), "contexts": []})
            if len(cands[key]["contexts"]) < 2 and kw.search(ctx):
                cands[key]["contexts"].append(ctx[:380])
    rep["js"]["candidates"] = cands
    print(json.dumps(rep, indent=1)[:60000])


if __name__ == "__main__":
    main()

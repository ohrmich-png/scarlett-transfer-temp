#!/usr/bin/env python3
"""
Login-flow recon for Sagemcom FAST5674IL. No auth needed: fetches the public
login page + its JS bundles and extracts the real login API call, including
any challenge/hash scheme (nonce/salt cookies suggest challenge-response).
Also probes candidate session-init endpoints. Prints compact JSON. No creds used.
"""
import sys, os, re, json, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155.0.0.0 Safari/537.36"
rep = {}


def raw(path, method="GET", data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if headers: h.update(headers)
    req = urllib.request.Request(ROUTER + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600], dict(e.headers)
    except Exception as e:
        return -1, str(e)[:200].encode(), {}


s, html, hdrs = raw("/")
rep["root_status"] = s
rep["root_set_cookie"] = hdrs.get("Set-Cookie", "")[:300]
rep["root_len"] = len(html)
page = html.decode(errors="replace")
srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page, re.I)
rep["scripts"] = srcs
rep["title"] = (re.search(r"<title>(.*?)</title>", page, re.I | re.S).group(1).strip()
                if re.search(r"<title>(.*?)</title>", page, re.I | re.S) else None)

# inline api paths on the login page
inline = sorted(set(re.findall(r'/api/v1/[A-Za-z0-9/_\-\.]+', page)))
rep["inline_api_paths"] = inline[:40]

# fetch JS bundles and hunt login logic
found = {}
for src in srcs[:10]:
    u = src if src.startswith("http") else ROUTER + (src if src.startswith("/") else "/" + src)
    s2, body, _ = raw(u.replace(ROUTER, ""))
    if s2 != 200 or len(body) < 200:
        found[u] = {"status": s2}
        continue
    t = body.decode(errors="replace")
    # login-relevant snippets
    hits = []
    for m in re.finditer(r'.{0,160}(login|password|nonce|salt|sha256|sha1|md5|hash|challenge|webguisession).{0,160}', t, re.I):
        line = re.sub(r"\s+", " ", m.group(0))
        if len(hits) < 12 and line not in hits:
            hits.append(line[:330])
    # api paths in this bundle
    paths = sorted(set(re.findall(r'["\'](/api/v1/[A-Za-z0-9/_\-\.\{\}]+)["\']', t)))
    found[u] = {"status": s2, "len": len(t), "api_paths": paths[:60], "login_hits": hits}
rep["bundles"] = found

# probe candidate session-init endpoints (no auth)
for p in ["/api/v1/login", "/api/v1/session", "/api/v1/webguisession",
          "/api/v1/webguisession-login", "/api/v1/auth", "/api/v1/nonce",
          "/api/v1/challenge", "/api/v1/salt"]:
    s3, b3, _ = raw(p)
    rep.setdefault("endpoint_probes", {})[p] = {"status": s3, "body": b3[:250].decode(errors="replace")}

print(json.dumps(rep, indent=1)[:55000])

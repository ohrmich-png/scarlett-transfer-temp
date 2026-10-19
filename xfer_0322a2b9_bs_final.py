#!/usr/bin/env python3
"""Definitive bandsteering PUT matrix (all no-op, stays ON) + wifi-save caller grep."""
import sys, os, re, json, urllib.request, urllib.parse, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
rep = {"matrix": []}


def raw(path, method="GET", body=None, ctype=None, timeout=12):
    h = {"User-Agent": UA, "Accept": "*/*", "Referer": ROUTER + "/"}
    if body is not None:
        h["Content-Type"] = ctype or "application/x-www-form-urlencoded"
    req = urllib.request.Request(ROUTER + path, data=body, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read()[:200]
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


u, p = router.USERNAME, router.PASSWORD
raw("/api/v1/login-params", "POST", urllib.parse.urlencode({"login": u}).encode())
raw("/api/v1/login", "POST", urllib.parse.urlencode({"login": u, "password": p}).encode())
if not getj("/api/v1/authenticated"):
    print(json.dumps({"authenticated": False})); raise SystemExit

before = getj("/api/v1/wireless/bandsteering")
P = "/api/v1/wireless/bandsteering"
variants = [
    ("form BandSteeringEnable=1", "PUT", urllib.parse.urlencode({"BandSteeringEnable": "1"}).encode(), None),
    ("form BandSteeringEnable=true", "PUT", urllib.parse.urlencode({"BandSteeringEnable": "true"}).encode(), None),
    ("json {BandSteeringEnable:true}", "PUT", json.dumps({"BandSteeringEnable": True}).encode(), "application/json"),
    ("json {BandSteeringEnable:1}", "PUT", json.dumps({"BandSteeringEnable": 1}).encode(), "application/json"),
]
for label, method, body, ctype in variants:
    s, _ = raw(P, method, body, ctype)
    rep["matrix"].append({"variant": label, "status": s})
after = getj("/api/v1/wireless/bandsteering")
rep["unchanged"] = (json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True))
rep["before"] = before

# --- secondary: wifi save caller shape (bundle grep only, no writes) ---
def bget(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(errors="replace")
idx = bget("/")
mm = re.search(r'main\.[a-f0-9]+\.js', idx)
t = bget("/" + mm.group(0))
saves = []
for m in re.finditer(r'\.put\(\s*[a-zA-Z]\.u\.wireless\.wifi\.replace\(', t):
    s = max(0, m.start() - 300)
    saves.append(re.sub(r"\s+", " ", t[s:m.start() + 400])[:700])
rep["wifi_save_callsites"] = list(dict.fromkeys(saves))[:4]
# enclosing save function: look for 'saveWifi' / 'save(' definitions near wireless
for pat in [r'saveWifi\w*\([^)]*\)\{[^}]{0,600}', r'saveWireless\([^)]*\)\{[^}]{0,600}']:
    f = re.findall(pat, t)
    if f:
        rep.setdefault("save_funcs", []).append(re.sub(r"\s+", " ", f[0])[:650])
print(json.dumps(rep)[:6500])

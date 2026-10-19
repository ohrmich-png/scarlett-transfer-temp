#!/usr/bin/env python3
"""Print the full 600-byte root bootstrap page + probe /gui variants."""
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request("http://10.100.102.1" + p, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return -1, str(e).encode()


s, b = get("/")
print("=== / (%d bytes, status %d) ===" % (len(b), s))
print(b.decode(errors="replace"))
print()
for p in ["/gui", "/gui/index.html", "/gui/login", "/gui/", "/main.html"]:
    s, b = get(p)
    print(p, "->", s, len(b))

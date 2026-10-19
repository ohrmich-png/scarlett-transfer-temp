#!/usr/bin/env python3
"""Recon12: find E/Oe/Ct hash definitions for createSession."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
i = t.find("createSession(")

# search backwards/forwards for E, Oe, Ct definitions in a 60k window
win = t[max(0, i-30000):i+30000]
def show(title, pat, n=8, width=400):
    out.append("=" * 20 + " " + title)
    seen = set()
    for m in re.finditer(pat, win):
        h = re.sub(r"\s+", " ", m.group(0))[:width]
        if h not in seen:
            seen.add(h)
            out.append(h)
            if len(seen) >= n:
                break
    out.append("")

# E assigned from something hash-like
show("E hash assign", r'[^A-Za-z0-9_$]E\s*=\s*[^;,]{1,90}', 10)
# Oe definition
show("Oe def", r'[^A-Za-z0-9_$]Oe\s*=\s*[^;,]{1,90}', 10)
# Ct definition
show("Ct def", r'[^A-Za-z0-9_$]Ct\s*=\s*[^;,]{1,90}', 10)
# sha/md5/crypto mentions in window
show("crypto mentions", r'.{0,60}(sha256|sha512|SHA256|CryptoJS|createHash|md5|MD5|subtle).{0,60}', 10, 200)
# E( usages with string concat (hash calls look like E(a+":"+b))
show("E( calls", r'E\([A-Za-z0-9_$]+\+"[^"]{0,10}"\+[A-Za-z0-9_$.()]+\)', 8, 200)

open(r"C:\Scarlett\home\recon12_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4000])

#!/usr/bin/env python3
"""Recon14: find E/Oe/Ct definitions ANYWHERE in bundle (all modules)."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
# every plausible definition pattern, whole bundle
patterns = [
    (r'function E\(', "function E("),
    (r'function Oe\(', "function Oe("),
    (r'function Ct\(', "function Ct("),
    (r'\bE\s*=\s*function', "E = function"),
    (r'\bOe\s*=\s*function', "Oe = function"),
    (r'\bCt\s*=\s*function', "Ct = function"),
    (r'\bE\s*=\s*[a-zA-Z_$][\w$]*\.(sha256|sha512|SHA256|md5|createHash)', "E = lib.hash"),
    (r'\bE\s*:\s*function', "E: function"),
    (r'import[^;]*\bE\b', "import E"),
    (r'sha256', "sha256 literal"),
    (r'SHA256', "SHA256 literal"),
    (r'createHash', "createHash literal"),
]
for pat, label in patterns:
    ms = list(re.finditer(pat, t))
    out.append("=== %s : %d hits ===" % (label, len(ms)))
    seen = set()
    for m in ms[:6]:
        h = re.sub(r"\s+", " ", t[max(0, m.start()-100):m.start()+150])[:280]
        if h not in seen:
            seen.add(h); out.append(h)
    out.append("")
open(r"C:\Scarlett\home\recon14_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4500])

#!/usr/bin/env python3
"""Recon16: extract region around the $6$ Ct definition - E/Oe should be nearby."""
import re, urllib.request

ROUTER = "http://10.100.102.1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(p):
    req = urllib.request.Request(ROUTER + p, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode(errors="replace")


t = get("/main.bfaad2e20f43e459.js")
out = []
i = t.find('Ve="$6$"')
out.append("Ct($6$) index: %d" % i)
# E and Oe as standalone function definitions near Ct: look for 'function E(' / patterns
# print 2500 chars before and identify function definitions
seg = t[max(0, i-2500):i]
# find all 'function NAME(' in this segment
fns = re.findall(r'function ([A-Za-z_$][\w$]*)\(', seg)
out.append("function defs in 2500 chars before Ct: %s" % fns)
# also var/const assignments of single/double letter names
assigns = re.findall(r'(?:var|const|let) ([A-Z][\w$]*|Oe|E|Ct)\s*=', seg)
out.append("var/const assigns: %s" % assigns)
out.append("")
out.append("=== segment tail (last 1800 chars) ===")
out.append(re.sub(r"\s+", " ", seg[-1800:]))
open(r"C:\Scarlett\home\recon16_out.txt", "w").write("\n".join(out))
print("\n".join(out)[:4200])

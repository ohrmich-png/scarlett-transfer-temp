#!/usr/bin/env python3
"""Safe introspection of the laptop's router.py. Prints NAMES ONLY - never values."""
import sys, inspect
sys.path.insert(0, r'C:\Scarlett\home')
import router

print('MODULE NAMES:', [n for n in dir(router) if not n.startswith('__')])
for n in ('CONID', 'NONCE', 'SALT', 'ROUTER', 'USERNAME', 'PASSWORD'):
    v = getattr(router, n, None)
    print(n, '->', 'SET' if v else 'MISSING', type(v).__name__, (len(v) if v else 0))

rs = getattr(router, 'RouterSession', None)
print('RouterSession:', 'present' if rs else 'absent')
if rs:
    print('methods:', [m for m in dir(rs) if not m.startswith('_')])
    try:
        print('__init__ params:', list(inspect.signature(rs.__init__).parameters))
    except Exception as e:
        print('sig err', e)
    # does login() exist and what does it reference (names only)?
    if hasattr(rs, 'login'):
        print('login params:', list(inspect.signature(rs.login).parameters))

# any module-level functions that might do auth?
for n in dir(router):
    o = getattr(router, n)
    if callable(o) and not n.startswith('__') and inspect.isfunction(o):
        print('func:', n, list(inspect.signature(o).parameters))

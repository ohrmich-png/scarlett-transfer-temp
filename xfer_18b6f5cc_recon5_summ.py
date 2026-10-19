#!/usr/bin/env python3
"""Summarize recon5_out.json: gui status, scripts, relevant API paths, login hits."""
import json

d = json.load(open(r'C:\Scarlett\home\recon5_out.json'))
print('gui_status:', d['gui_status'], 'len:', d['gui_len'])
print('scripts:')
for s in d['scripts']:
    print('  ', s)
KW = ('login', 'session', 'auth', 'wireless', 'wifi', 'wlan', 'radio', 'band', 'ssid', 'wps')
for u, b in d['bundles'].items():
    print('=' * 30)
    print(u, '->', b['status'], b.get('len'))
    if 'api_paths' in b:
        rel = [p for p in b['api_paths'] if any(k in p.lower() for k in KW)]
        print('relevant api paths (%d of %d):' % (len(rel), len(b['api_paths'])))
        for p in rel:
            print('   ', p)
    for h in b.get('login_hits', [])[:8]:
        print('  LOGIN:', h[:240])
    for h in b.get('wireless_hits', [])[:8]:
        print('  WIFI:', h[:240])

import json, urllib.request, time

try:
    with urllib.request.urlopen("http://127.0.0.1:9223/json/list", timeout=10) as r:
        targets = json.load(r)
    pages = [t for t in targets if t.get("type") == "page"]
    print(f"{len(pages)} pages open:")
    for p in pages:
        print(" -", p.get("url", "")[:80])
except Exception as e:
    print("ERR:", e)

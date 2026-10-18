import subprocess, time, sys, json, urllib.request, urllib.parse

PORT = 9223
def cdp_call(ws_url, method, params=None, timeout=30):
    import websocket
    ws = websocket.create_connection(ws_url, timeout=timeout)
    ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == 1:
            ws.close()
            return msg.get("result", {})

# Open new tab via /json/new (needs PUT)
req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?https://chatgpt.com",
                             method="PUT")
with urllib.request.urlopen(req, timeout=15) as r:
    target = json.load(r)
print("opened:", target["url"][:50])
time.sleep(12)
# Evaluate in that page
ws_url = target["webSocketDebuggerUrl"]
res = cdp_call(ws_url, "Runtime.evaluate", {"expression": "document.title + ' || ' + (document.body ? document.body.innerText.slice(0,400) : 'no body')", "returnByValue": True})
print("PAGE:", str(res.get("result", {}).get("value", ""))[:500])

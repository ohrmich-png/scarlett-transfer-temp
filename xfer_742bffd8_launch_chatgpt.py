import subprocess, time, sys, json, urllib.request

# Launch headed debug Chrome if not running
import os
os.system('start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9223 --user-data-dir=C:\\Scarlett\\chrome-debug --remote-allow-origins=* about:blank')
time.sleep(8)

# Open chatgpt.com in new tab
req = urllib.request.Request("http://127.0.0.1:9223/json/new?https://chatgpt.com", method="PUT")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        target = json.load(r)
    print("opened OK")
    time.sleep(15)
    ws_url = target["webSocketDebuggerUrl"]
    import websocket
    ws = websocket.create_connection(ws_url, timeout=30)
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "document.title + ' || ' + (document.body ? document.body.innerText.slice(0,500) : 'no body')", "returnByValue": True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == 1:
            ws.close()
            val = str(msg.get("result", {}).get("result", {}).get("value", ""))
            print("PAGE:", val[:600])
            break
except Exception as e:
    print("ERR:", e)

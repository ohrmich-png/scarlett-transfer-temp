import subprocess, time, json, sys

def hcdp(*args):
    p = subprocess.run([sys.executable, 'C:\\Scarlett\\headless\\hcdp.py'] + list(args),
                       capture_output=True, text=True, timeout=60, cwd='C:\\Scarlett\\headless')
    return p.stdout + p.stderr

print("Opening chatgpt.com...")
print(hcdp('new', 'https://chatgpt.com')[:300])
time.sleep(10)
print("--- page state ---")
out = hcdp('eval', "document.title + ' || ' + (document.body ? document.body.innerText.slice(0,800) : 'no body')", "chatgpt")
print(out[:1200])

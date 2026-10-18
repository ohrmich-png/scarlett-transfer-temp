import subprocess, time, sys

def hcdp(*args):
    p = subprocess.run([sys.executable, 'C:\\Scarlett\\headless\\hcdp.py'] + list(args),
                       capture_output=True, text=True, timeout=60, cwd='C:\\Scarlett\\headless')
    return p.stdout + p.stderr

for i in range(6):
    time.sleep(10)
    out = hcdp('eval', "document.title + ' || ' + (document.body ? document.body.innerText.slice(0,400) : 'no body')", "chatgpt")
    print(f"[{i}]", out[:500].replace('\n', ' '))
    if 'Just a moment' not in out and 'no body' not in out:
        break

import sys
sys.path.insert(0, 'C:\\Scarlett\\headless')
from hcdp import CDP
import time, json

c = CDP(port=9224)
# Create a new page
target = c.new_target('https://chatgpt.com')
print("target:", target.get('targetId', 'ok'))
time.sleep(8)
# Get page content info
info = c.evaluate("document.title + ' | ' + document.body.innerText.slice(0,500)")
print("PAGE:", info[:600])

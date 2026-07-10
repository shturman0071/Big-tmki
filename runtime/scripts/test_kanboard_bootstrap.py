import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8770/api/kanboard/bootstrap",
    data=b"{}",
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp = urllib.request.urlopen(req, timeout=15)
print("status", resp.status)
print("cookies", [h for h in resp.headers.items() if h[0].lower() == "set-cookie"])
print(json.loads(resp.read().decode()))

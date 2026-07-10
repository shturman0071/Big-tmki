import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8770/api/agent/chat",
    data=json.dumps({"greeting": True}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
print(data.get("agent"), data.get("answer", "")[:100])
print("tts", bool((data.get("tts") or {}).get("audio_base64")))

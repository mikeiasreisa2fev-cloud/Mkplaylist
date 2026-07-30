import requests
import re
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Portal
BASE_DOMAIN = "https://app.pobreflix2.site"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        if self.token: return self.token
        try:
            url = f"{BASE_DOMAIN}/"
            params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {"username": f"guest_{self.device_id[:8]}", "password": "guest", "device_id": self.device_id}
            r = requests.post(url, params=params, json=payload, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                return self.token
        except: pass
        return None

    def get_channels_from_html(self, sid):
        """Extrai canais lendo a página web que você enviou."""
        channels = []
        try:
            url = f"{BASE_DOMAIN}/canais/?thema=1&server=speed-{sid}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                # 'Caça' o ID e o Nome no código do site
                matches = re.findall(r'href="https://app.pobreflix2.site/canais/(\d+)/".*?title="(.*?)"', res.text)
                for cid, name in matches:
                    channels.append({"id": cid, "name": name.replace("Assistir ", ""), "category_name": f"Canais [S{sid}]"})
        except: pass
        return channels

api = SpeedFlixAPI()

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    token = api.login()
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token: suffix += f"&Authorization=Bearer {token}"

    for sid in [1, 2, 3]:
        # Tenta ler o site que você enviou para pegar os canais
        channels = api.get_channels_from_html(sid)
        for ch in channels:
            cid = ch['id']
            name = f"{ch['name']} [S{sid}]"
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{name}')
            m3u.append(f"{BASE_DOMAIN}/?rest_route=/xui-pflix/v1/channels/{cid}/stream&server_id={sid}{suffix}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

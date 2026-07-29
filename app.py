import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Domínio que você forneceu
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Faz login de convidado para liberar canais e vídeos."""
        if self.token: return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Content-Type": "application/json"}
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_headers(self):
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Accept": "application/json"}
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Ativo no Railway</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Headers para o TiviMate abrir o vídeo com autorização
    token = api.login()
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token: suffix += f"&Authorization=Bearer {token}"

    for sid in [1, 2, 3]:
        for page in range(1, 10): # Busca até 1000 canais por servidor
            try:
                r = requests.get(f"{BASE_URL}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=api.get_headers(), timeout=15)
                if r.status_code != 200: break
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items: break
                
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{group}",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                
                if page >= int(data.get("data", {}).get("meta", {}).get("total_pages", 1)): break
            except: break
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0].split('?')[0]
    try:
        r = requests.get(f"{BASE_URL}/channels/{clean_id}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=api.get_headers(), timeout=10)
        url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
        if url: return redirect(url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    # O Railway usa a variável PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

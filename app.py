import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Servidor
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
APP_USER_AGENT = "okhttp/4.12.0"
APP_IDENTIFIER = "site.speedflix"

# Cache simples em memória
cache = {
    "channels": [],
    "last_update": 0
}

class SpeedFlixSession:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4())[:16]

    def login(self):
        try:
            payload = {
                "username": f"guest_{self.device_id}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            res = requests.post(f"{BASE_URL}/auth/login", json=payload, headers={"User-Agent": APP_USER_AGENT}, timeout=10)
            if res.status_code == 200:
                self.token = res.json().get("data", {}).get("token") or res.json().get("token")
                return self.token
        except: pass
        return None

    def get_headers(self):
        h = {"User-Agent": APP_USER_AGENT, "X-Requested-With": APP_IDENTIFIER}
        token = self.login()
        if token: h["Authorization"] = f"Bearer {token}"
        return h

session = SpeedFlixSession()

def fetch_all_channels():
    """Busca todos os canais dos 3 servidores e guarda no cache."""
    now = time.time()
    if cache["channels"] and (now - cache["last_update"] < 1800): # 30 min cache
        return cache["channels"]

    all_found = []
    for sid in [1, 2, 3]:
        for page in range(1, 6): # Busca até 5 páginas por servidor
            try:
                res = requests.get(f"{BASE_URL}/channels", params={
                    "server_id": sid, "per_page": 100, "page": page
                }, headers=session.get_headers(), timeout=10)
                if res.status_code != 200: break
                items = res.json().get("data", {}).get("items") or res.json().get("items") or []
                if not items: break
                
                for i in items:
                    i["sid"] = sid # Marca o servidor de origem
                all_found.extend(items)
            except: break
            
    cache["channels"] = all_found
    cache["last_update"] = now
    return all_found

@app.route("/")
def index():
    return "Servidor SpeedFlix Ativo. Use /playlist.m3u"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    channels = fetch_all_channels()
    
    # O sufixo '|User-Agent=...' instrui o TiviMate a usar os headers corretos
    m3u_headers = f"|User-Agent={APP_USER_AGENT}&X-Requested-With={APP_IDENTIFIER}"
    
    m3u = ["#EXTM3U"]
    for ch in channels:
        ch_id = ch.get("id")
        sid = ch.get("sid")
        name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
        group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
        logo = ch.get("image") or ""
        
        # tvg-id único para não bugar o EPG
        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
        # Link do stream + Headers para o TiviMate injetar na requisição do vídeo
        m3u.append(f"{host}/stream/{sid}/{ch_id}{m3u_headers}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    try:
        url = f"{BASE_URL}/channels/{cid}/stream"
        res = requests.get(url, params={"server_id": sid, "t": int(time.time())}, 
                          headers=session.get_headers(), timeout=10)
        if res.status_code == 200:
            video_url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
            if video_url:
                return redirect(video_url)
    except: pass
    return "Indisponível", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

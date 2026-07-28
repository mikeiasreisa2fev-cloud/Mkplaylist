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

class SpeedFlixSession:
    def __init__(self):
        self.token = None
        self.device_id = "550e8400-e29b-41d4-a716-446655440000" # ID Fixo para estabilidade

    def login(self):
        """Obtém o token Bearer necessário para canais e vídeos."""
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
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

def get_channels(server_id):
    """Puxa todos os canais de um servidor de forma exaustiva."""
    all_items = []
    for page in range(1, 15): # Aumentado para pegar até 1500 canais
        try:
            res = requests.get(f"{BASE_URL}/channels", params={
                "server_id": server_id, "per_page": 100, "page": page
            }, headers=session.get_headers(), timeout=12)
            if res.status_code != 200: break
            data = res.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            if not items: break
            all_items.extend(items)
            
            meta = data.get("data", {}).get("meta") or data.get("meta") or {}
            if page >= int(meta.get("total_pages", 1)): break
        except: break
    return all_items

@app.route("/")
def index():
    return "Status: Online. Use /playlist.m3u"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    token = session.login()
    
    # FORMATO ESPECIAL PARA TIVIMATE: Injeta headers na URL do stream
    # O TiviMate reconhece o '|' e usa o que vem depois como cabeçalho HTTP
    headers_suffix = f"|User-Agent={APP_USER_AGENT}&X-Requested-With={APP_IDENTIFIER}"
    if token:
        headers_suffix += f"&Authorization=Bearer {token}"
    
    m3u = ["#EXTM3U"]
    for sid in [1, 2, 3]:
        channels = get_channels(sid)
        for ch in channels:
            ch_id = ch.get("id")
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
            logo = ch.get("image") or ""
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            # O link aponta para o nosso proxy que vai buscar a URL final do vídeo
            m3u.append(f"{host}/stream/{sid}/{ch_id}{headers_suffix}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Pega a URL final do vídeo usando a autorização do Render."""
    try:
        res = requests.get(f"{BASE_URL}/channels/{cid}/stream", 
                          params={"server_id": sid, "t": int(time.time())}, 
                          headers=session.get_headers(), timeout=10)
        if res.status_code == 200:
            video_url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
            if video_url:
                # Retorna o link final. O TiviMate usará os headers do sufixo para abrir.
                return redirect(video_url)
    except: pass
    return "Offline", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

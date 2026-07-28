import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Servidor
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
HEADERS_BASE = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

class SpeedFlixSession:
    def __init__(self):
        self.token = None
        self.last_login = 0
        self.device_id = str(uuid.uuid4())[:16]

    def login(self):
        """Faz o login de convidado para obter o Bearer Token."""
        if self.token and (time.time() - self.last_login < 3600):
            return self.token
        
        try:
            # Dados de login que o app usa para convidados
            payload = {
                "username": f"guest_{self.device_id}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            res = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=HEADERS_BASE, timeout=15)
            if res.status_code == 200:
                data = res.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                self.last_login = time.time()
                return self.token
        except:
            pass
        return None

    def get_auth_headers(self):
        headers = HEADERS_BASE.copy()
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

session = SpeedFlixSession()

def get_all_channels(server_id):
    all_items = []
    for page in range(1, 10): # Percorre até 10 páginas (aprox 1000 canais)
        try:
            headers = session.get_auth_headers()
            res = requests.get(f"{BASE_URL}/channels", params={
                "server_id": server_id, "per_page": 100, "page": page
            }, headers=headers, timeout=15)
            
            if res.status_code != 200: break
            data = res.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            if not items: break
            all_items.extend(items)
            
            total_pages = data.get("data", {}).get("meta", {}).get("total_pages") or data.get("total_pages", 1)
            if page >= int(total_pages): break
        except: break
    return all_items

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    for sid in [1, 2, 3]:
        channels = get_all_channels(sid)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id: continue
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or f"SERVIDOR {sid}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{sid}/{ch_id}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Obtém o link de vídeo usando o Token de Autorização."""
    try:
        headers = session.get_auth_headers()
        timestamp = int(time.time())
        res = requests.get(f"{BASE_URL}/channels/{cid}/stream", 
                          params={"server_id": sid, "t": timestamp}, 
                          headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if video_url:
                return redirect(video_url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv")
    return Response(ET.tostring(tv), mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

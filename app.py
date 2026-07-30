import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Portal
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def get_headers(self, auth=True):
        h = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": APP_ID,
            "Accept": "application/json",
            "Connection": "Keep-Alive"
        }
        if auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def login(self):
        """Simula a entrada no app: Config -> Login."""
        try:
            # 1. Pede o config (O app sempre faz isso primeiro)
            requests.get(f"{BASE_URL}/app/config", headers=self.get_headers(False), timeout=10)
            
            # 2. Faz o login de convidado
            payload = {
                "username": f"guest_{self.device_id[:6]}",
                "password": "guest",
                "device_id": self.device_id
            }
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=self.get_headers(False), timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return True
        except: pass
        return False

    def get_servers(self):
        """Descobre quais servidores estao ativos (1, 2, 3, etc)."""
        try:
            r = requests.get(f"{BASE_URL}/servers", headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", {}).get("items") or r.json().get("items") or []
                # Pega os IDs (a) ou (id)
                return [s.get("a") or s.get("id") for s in items if (s.get("a") or s.get("id"))]
        except: pass
        return [1, 2, 3]

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>Proxy Railway Ativo</h1><p>Playlist: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    if not api.login():
        m3u.append("# ERRO: Falha na autenticacao (Login Error)")
        return Response("\n".join(m3u), mimetype="text/plain")

    # Suffix para o player injetar os headers no video
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}&Authorization=Bearer {api.token}"

    active_servers = api.get_servers()
    total_found = 0

    for sid in active_servers:
        # Pede os canais (usamos 200 por pagina para nao dar timeout)
        try:
            r = requests.get(f"{BASE_URL}/channels", 
                            params={"server_id": sid, "per_page": 200, "page": 1},
                            headers=api.get_headers(), timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or 'Canais').upper()
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                    total_found += 1
        except: continue

    if total_found == 0:
        m3u.append("# ERRO: Nenhum canal retornado pelos servidores.")
        m3u.append(f"# SERVIDORES TESTADOS: {active_servers}")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0]
    try:
        url = f"{BASE_URL}/channels/{clean_id}/stream"
        r = requests.get(url, params={"server_id": sid, "t": int(time.time())}, 
                        headers=api.get_headers(), timeout=10)
        if r.status_code == 200:
            v_url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
            if v_url: return redirect(v_url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

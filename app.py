import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Lista de domínios ativos para o SpeedFlix
DOMAINS = [
    "https://app.pobreflix2.site/wp-json/xui-pflix/v1",
    "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1",
    "https://speedflix02.com/wp-json/xui-pflix/v1"
]

USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.base_url = DOMAINS[0]
        self.device_id = "fb387652c" + str(uuid.uuid4())[:7] # ID mais parecido com Android

    def login(self):
        """Tenta o login de convidado em todos os domínios disponíveis."""
        for base in DOMAINS:
            try:
                payload = {
                    "username": f"guest_{self.device_id[:6]}",
                    "password": "guest",
                    "device_id": self.device_id
                }
                r = requests.post(f"{base}/auth/login", json=payload, 
                                 headers={"User-Agent": USER_AGENT}, timeout=8)
                if r.status_code == 200:
                    self.base_url = base
                    self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                    return self.token
            except: continue
        return None

    def get_headers(self):
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

api = SpeedFlixAPI()

@app.route("/")
def index():
    return f"<h1>Proxy SpeedFlix</h1><p>Status: Online</p><p>Link: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Tenta logar antes de começar
    api.login()
    
    # Cabeçalhos para o TiviMate abrir o vídeo
    token_suffix = f"&Authorization=Bearer%20{api.token}" if api.token else ""
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}{token_suffix}"

    total_canais = 0
    errors = []

    for sid in [1, 2, 3]:
        # Busca até 3 páginas para garantir que pegamos os 176, 192 e 127 canais
        for page in range(1, 4):
            try:
                r = requests.get(f"{api.base_url}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=api.get_headers(), timeout=12)
                
                if r.status_code != 200:
                    errors.append(f"Servidor {sid} Pagina {page} retornou erro {r.status_code}")
                    break
                
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                
                if not items: break
                
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = ch.get('category_name') or 'Canais'
                    group = f"{cat.upper()} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                    total_canais += 1
                
                # Se a API indicar que não tem mais páginas, para o loop
                meta = data.get("data", {}).get("meta") or data.get("meta") or {}
                if page >= int(meta.get("total_pages", 1)): break
            except Exception as e:
                errors.append(f"Erro no Servidor {sid}: {str(e)}")
                break

    if total_canais == 0:
        m3u.append("# ERRO: Nenhum canal capturado.")
        for err in errors:
            m3u.append(f"# DETALHE: {err}")
        m3u.append(f"# URL_USADA: {api.base_url}")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    clean_cid = cid.split('|')[0]
    try:
        # Gera o link do vídeo usando o token e o tempo atual
        r = requests.get(f"{api.base_url}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=api.get_headers(), timeout=10)
        
        if r.status_code == 200:
            data = r.json().get("data") or r.json()
            video_url = data.get("stream_url")
            if video_url:
                return redirect(video_url)
    except: pass
    return "Offline", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

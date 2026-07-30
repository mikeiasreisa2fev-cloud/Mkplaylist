import requests
from flask import Flask, Response, request
import os
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
        """Tenta login de convidado via rest_route para burlar bloqueios."""
        if self.token: return self.token
        try:
            url = f"{BASE_DOMAIN}/"
            params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {
                "username": f"guest_{self.device_id[:8]}", 
                "password": "guest", 
                "device_id": self.device_id
            }
            r = requests.post(url, params=params, json=payload, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_channels(self, sid):
        """Busca canais usando a técnica rest_route."""
        token = self.login()
        url = f"{BASE_DOMAIN}/"
        params = {
            "rest_route": "/xui-pflix/v1/channels",
            "server_id": sid,
            "per_page": 200
        }
        headers = {"User-Agent": USER_AGENT}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                # Extração flexível dos itens
                return data.get("data", {}).get("items") or data.get("items") or []
        except: pass
        return []

api = SpeedFlixAPI()

@app.route("/")
def index():
    return f"<h1>SpeedFlix Proxy</h1><p>Playlist: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    """Gera a playlist M3U unificada [S1, S2, S3]."""
    m3u = ["#EXTM3U"]
    
    token = api.login()
    if not token:
        m3u.append("# ERRO: Falha ao obter Token de Autorização.")
    
    # Headers que o TiviMate deve usar para abrir o link de vídeo
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token:
        suffix += f"&Authorization=Bearer {token}"

    total = 0
    for sid in [1, 2, 3]:
        channels = api.get_channels(sid)
        if not channels:
            m3u.append(f"# INFO: Servidor {sid} não retornou canais na API.")
            continue
            
        for ch in channels:
            cid = ch.get("id")
            if not cid: continue
            
            # Nome e Grupo identificados
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            cat = (ch.get('category_name') or 'Canais').upper()
            logo = ch.get("image") or ""
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
            
            # Link de vídeo direto via rest_route
            # Isso pula o proxy da sua hospedagem e usa o servidor original do SpeedFlix
            stream_url = f"{BASE_DOMAIN}/?rest_route=/xui-pflix/v1/channels/{cid}/stream&server_id={sid}"
            m3u.append(f"{stream_url}{suffix}")
            total += 1
            
    if total == 0:
        m3u.append("# ERRO: Todos os servidores retornaram lista vazia. O IP da sua hospedagem pode estar bloqueado.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

if __name__ == "__main__":
    # O Railway usa a porta 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

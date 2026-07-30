import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid
import json

app = Flask(__name__)

# Configurações do Portal
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

# Arquivo de cache para evitar bloqueio de IP do Render
CACHE_FILE = "/tmp/channels_cache.json"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = "box_" + str(uuid.uuid4())[:8]

    def get_headers(self):
        h = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Accept": "application/json"}
        if self.token: h["Authorization"] = f"Bearer {self.token}"
        return h

    def login(self):
        try:
            payload = {"username": f"guest_{self.device_id}", "password": "guest", "device_id": self.device_id}
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                return True
        except: pass
        return False

api = SpeedFlixAPI()

def get_channels_with_cache():
    """Tenta ler do cache local ou busca na API se o cache expirou."""
    # Se o cache existe e tem menos de 6 horas, usa ele
    if os.path.exists(CACHE_FILE):
        if (time.time() - os.path.getmtime(CACHE_FILE)) < 21600:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)

    api.login()
    all_channels = []
    for sid in [1, 2, 3]:
        # Busca as primeiras 4 páginas de cada servidor
        for page in range(1, 5):
            try:
                res = requests.get(f"{BASE_URL}/channels", 
                                 params={"server_id": sid, "per_page": 100, "page": page},
                                 headers=api.get_headers(), timeout=15)
                if res.status_code != 200: break
                items = res.json().get("data", {}).get("items") or res.json().get("items") or []
                if not items: break
                for i in items: i['sid'] = sid
                all_channels.extend(items)
                if page >= int(res.json().get("data", {}).get("meta", {}).get("total_pages", 1)): break
            except: break
    
    if all_channels:
        with open(CACHE_FILE, 'w') as f:
            json.dump(all_channels, f)
            
    return all_channels

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Ativo</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    channels = get_channels_with_cache()
    m3u = ["#EXTM3U"]
    
    # Adicionamos o token atualizado para os links de stream
    api.login()
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if api.token: suffix += f"&Authorization=Bearer {api.token}"

    for ch in channels:
        cid, sid = ch.get("id"), ch.get("sid")
        name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
        group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
        logo = ch.get("image") or ""
        
        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
        m3u.append(f"{host}stream/{sid}/{cid}{suffix}")

    if len(m3u) == 1:
        m3u.append("# ERRO: Servidor bloqueou o IP do Render (403).")
        m3u.append("# SOLUCAO: Abra o link do Render no 4G do celular uma vez para 'acordar' a sessao.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0]
    api.login()
    try:
        r = requests.get(f"{BASE_URL}/channels/{clean_id}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=api.get_headers(), timeout=10)
        url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
        if url: return redirect(url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Lista de domínios para tentar (se um der erro 403, ele tenta o outro)
DOMAINS = [
    "https://ycineflix.tudo30.shop",
    "https://app.pobreflix2.site",
    "https://speedflix.top"
]
API_PATH = "/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.active_base = DOMAINS[0]
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Tenta login nos domínios até conseguir um token."""
        for base in DOMAINS:
            try:
                payload = {
                    "username": f"guest_{self.device_id[:6]}",
                    "password": "guest",
                    "device_id": self.device_id,
                    "model": "Samsung SM-G998B"
                }
                headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID}
                # Tenta o config primeiro (limpa o caminho na Cloudflare)
                requests.get(f"{base}{API_PATH}/app/config", headers=headers, timeout=10)
                
                r = requests.post(f"{base}{API_PATH}/auth/login", json=payload, headers=headers, timeout=10)
                if r.status_code == 200:
                    self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                    self.active_base = base
                    return True
            except:
                continue
        return False

    def get_headers(self):
        h = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>Proxy Ativo</h1><p>M3U: /playlist.m3u</p><p>EPG: /epg.xml</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    if not api.login():
        m3u.append("# ERRO: Falha ao autenticar em todos os dominios.")
        return Response("\n".join(m3u), mimetype="text/plain")

    # Sufixo com headers para o TiviMate
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}&Authorization=Bearer {api.token}"

    found = 0
    for sid in [1, 2, 3]:
        try:
            # Tenta pegar 200 canais por servidor
            url = f"{api.active_base}{API_PATH}/channels"
            r = requests.get(url, params={"server_id": sid, "per_page": 200}, headers=api.get_headers(), timeout=15)
            if r.status_code == 200:
                items = r.json().get("data", {}).get("items") or r.json().get("items") or []
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or 'Canais').upper()
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{cat} [S{sid}]",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                    found += 1
        except:
            continue

    if found == 0:
        m3u.append(f"# ERRO: Nenhum canal retornado por {api.active_base}")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0]
    try:
        url = f"{api.active_base}{API_PATH}/channels/{clean_id}/stream"
        r = requests.get(url, params={"server_id": sid, "t": int(time.time())}, headers=api.get_headers(), timeout=10)
        v_url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
        if v_url: return redirect(v_url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    # Retorna XML vazio para evitar erros 500
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

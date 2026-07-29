import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid
import random

app = Flask(__name__)

# Domínio fornecido pelo usuário que agrupa os servidores
BASE_URL = "https://ycineflix.tudo30.shop"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def get_fake_headers(self):
        """Gera headers que simulam um dispositivo real do Brasil."""
        fake_ip = f"{random.choice([177, 179, 186, 187, 189, 191, 200, 201])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        return {
            "User-Agent": USER_AGENT,
            "X-Requested-With": APP_ID,
            "X-Forwarded-For": fake_ip,
            "X-Real-IP": fake_ip,
            "Referer": f"{BASE_URL}/",
            "Accept": "application/json"
        }

    def login(self):
        """Tenta o login de convidado usando o bypass rest_route do WordPress."""
        if self.token: return self.token
        try:
            # Técnica de Bypass: usa o parâmetro rest_route para pular bloqueios de URL
            url = f"{BASE_URL}/"
            params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {
                "username": f"guest_{self.device_id[:6]}",
                "password": "guest",
                "device_id": self.device_id
            }
            r = requests.post(url, params=params, json=payload, headers=self.get_fake_headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_api_data(self, endpoint, params=None):
        """Busca dados da API usando a técnica de bypass rest_route."""
        url = f"{BASE_URL}/"
        query = {"rest_route": f"/xui-pflix/v1/{endpoint}"}
        if params: query.update(params)
        
        headers = self.get_fake_headers()
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            return requests.get(url, params=query, headers=headers, timeout=15)
        except:
            return None

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>SpeedFlix Proxy Ativo</h1><p>Playlist: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Prepara o sufixo de autenticação para o TiviMate
    token = api.login()
    token_part = f"&Authorization=Bearer%20{token}" if token else ""
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}{token_part}"

    total = 0
    errors = []

    # Busca canais dos servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        # Tenta carregar até 5 páginas por servidor para garantir todos os canais
        for page in range(1, 6):
            res = api.get_api_data("channels", {"server_id": sid, "per_page": 100, "page": page})
            
            if not res or res.status_code != 200:
                code = res.status_code if res else "TIMEOUT"
                errors.append(f"Servidor {sid} Pagina {page} -> Erro {code}")
                break
            
            data = res.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            if not items: break
            
            for ch in items:
                cid = ch.get("id")
                if not cid: continue
                
                name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                cat = ch.get('category_name') or 'Canais'
                group = f"{cat.upper()} [S{sid}]"
                logo = ch.get("image") or ""
                
                m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                total += 1
                
            meta = data.get("data", {}).get("meta") or {}
            if page >= int(meta.get("total_pages", 1)): break

    if total == 0:
        m3u.append("# ERRO: Conexao recusada pelo servidor (403).")
        for err in errors: m3u.append(f"# DETALHE: {err}")
        m3u.append(f"# LOGIN: {'SUCESSO' if api.token else 'FALHA'}")
        m3u.append(f"# DOMINIO: {BASE_URL}")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    # Limpa o ID do canal removendo sufixos do player
    clean_cid = cid.split('|')[0].split('?')[0]
    
    # Solicita o link de vídeo real
    res = api.get_api_data(f"channels/{clean_cid}/stream", {"server_id": sid, "t": int(time.time())})
    if res and res.status_code == 200:
        data = res.json()
        video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
        if video_url:
            return redirect(video_url)
            
    return "Link Offline", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

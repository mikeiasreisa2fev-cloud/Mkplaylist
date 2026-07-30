import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid
import random

app = Flask(__name__)

# Domínios ativos
DOMAINS = [
    "https://ycineflix.tudo30.shop",
    "https://app.pobreflix2.site",
    "https://speedflix02.com"
]

USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

def get_br_headers(token=None):
    """Gera cabeçalhos simulando um celular Android no Brasil."""
    # IPs típicos de rede residencial brasileira (Vivo, Claro, etc)
    fake_ip = f"{random.choice([177, 179, 186, 187, 189, 191, 200, 201])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    h = {
        "User-Agent": USER_AGENT,
        "X-Requested-With": APP_ID,
        "X-Forwarded-For": fake_ip,
        "X-Real-IP": fake_ip,
        "Accept": "application/json",
        "Connection": "Keep-Alive"
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.active_base = DOMAINS[0]
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Tenta login usando a técnica rest_route para bypass."""
        for base in DOMAINS:
            try:
                # Bypass: acessa a API através de um parâmetro de busca
                url = f"{base}/"
                params = {"rest_route": "/xui-pflix/v1/auth/login"}
                payload = {
                    "username": f"guest_{self.device_id[:6]}",
                    "password": "guest",
                    "device_id": self.device_id
                }
                r = requests.post(url, params=params, json=payload, headers=get_br_headers(), timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    self.token = data.get("data", {}).get("token") or data.get("token")
                    self.active_base = base
                    return True
            except: continue
        return False

    def get_channels(self, sid):
        """Busca canais via rest_route."""
        url = f"{self.active_base}/"
        params = {
            "rest_route": "/xui-pflix/v1/channels",
            "server_id": sid,
            "per_page": 200
        }
        try:
            r = requests.get(url, params=params, headers=get_br_headers(self.token), timeout=15)
            if r.status_code == 200:
                data = r.json()
                return data.get("data", {}).get("items") or data.get("items") or []
        except: pass
        return []

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>Proxy Railway Ativo</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Tenta o login, mas continua mesmo se falhar (alguns servidores estao abertos)
    api.login()
    
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if api.token:
        suffix += f"&Authorization=Bearer {api.token}"

    total = 0
    for sid in [1, 2, 3]:
        items = api.get_channels(sid)
        for ch in items:
            cid = ch.get("id")
            if not cid: continue
            
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            cat = (ch.get('category_name') or 'Canais').upper()
            logo = ch.get("image") or ""
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
            total += 1

    if total == 0:
        m3u.append("# ERRO: Todos os dominios de acesso falharam.")
        m3u.append("# DETALHE: O servidor identificou o acesso como Datacenter.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0]
    try:
        url = f"{api.active_base}/"
        params = {"rest_route": f"/xui-pflix/v1/channels/{clean_id}/stream", "server_id": sid, "t": int(time.time())}
        r = requests.get(url, params=params, headers=get_br_headers(api.token), timeout=10)
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

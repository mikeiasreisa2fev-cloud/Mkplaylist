import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid
import random

app = Flask(__name__)

# Domínio principal e backups
DOMAINS = ["https://ycineflix.tudo30.shop", "https://app.pobreflix2.site"]
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]
        self.active_base = DOMAINS[0]

    def get_headers(self, auth=True):
        fake_ip = f"{random.randint(177, 201)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        h = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": APP_ID,
            "X-Forwarded-For": fake_ip,
            "Accept": "application/json"
        }
        if auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def login(self):
        if self.token: return True
        for base in DOMAINS:
            try:
                url = f"{base}/"
                params = {"rest_route": "/xui-pflix/v1/auth/login"}
                payload = {"username": f"guest_{self.device_id[:6]}", "password": "guest", "device_id": self.device_id}
                r = requests.post(url, params=params, json=payload, headers=self.get_headers(False), timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    self.token = data.get("data", {}).get("token") or data.get("token")
                    self.active_base = base
                    return True
            except: continue
        return False

    def get_data(self, endpoint, params=None):
        self.login()
        url = f"{self.active_base}/"
        query = {"rest_route": f"/xui-pflix/v1/{endpoint}"}
        if params: query.update(params)
        try:
            r = requests.get(url, params=query, headers=self.get_headers(), timeout=15)
            if r.status_code == 200:
                return r.json()
        except: pass
        return None

api = SpeedFlixAPI()

@app.route("/")
def index():
    status = "Logado" if api.login() else "Erro no Login"
    return f"<h1>SpeedFlix Proxy</h1><p>Status: {status}</p><p>Link: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    api.login()
    
    token_part = f"&Authorization=Bearer%20{api.token}" if api.token else ""
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}{token_part}"

    for sid in [1, 2, 3]:
        # Pega apenas a página 1 para ser rápido e evitar erro 500 no Render
        res = api.get_data("channels", {"server_id": sid, "per_page": 200, "page": 1})
        if res:
            items = res.get("data", {}).get("items") or res.get("items") or []
            for ch in items:
                cid = ch.get("id")
                if not cid: continue
                name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                cat = ch.get('category_name') or 'Canais'
                m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{cat.upper()} [S{sid}]",{name}')
                m3u.append(f"{host}stream/{sid}/{cid}{suffix}")

    if len(m3u) == 1:
        m3u.append("# ERRO: Servidor nao retornou dados. Tente atualizar a pagina inicial.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_cid = cid.split('|')[0].split('?')[0]
    res = api.get_data(f"channels/{clean_cid}/stream", {"server_id": sid, "t": int(time.time())})
    if res:
        url = res.get("data", {}).get("stream_url") or res.get("stream_url")
        if url: return redirect(url)
    return "Offline", 404

@app.route("/epg.xml")
def epg():
    # Retorna XML vazio para evitar sobrecarga
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

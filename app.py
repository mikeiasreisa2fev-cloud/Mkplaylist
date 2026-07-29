import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Domínios
BASE_URL = "https://app.pobreflix2.site"
API_PATH = "/wp-json/xui-pflix/v1"

# Headers Ultra-Reais
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "X-Requested-With": "site.speedflix",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/"
}

class SpeedFlixSession:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def refresh_session(self):
        """Simula a abertura do app para validar o IP no firewall."""
        try:
            # 1. Visita o site principal para pegar Cookies (PHPSESSID, etc)
            self.session.get(f"{BASE_URL}/", headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10)
            
            # 2. Carrega o Config (Isso valida a rota na Cloudflare)
            self.session.get(f"{BASE_URL}{API_PATH}/app/config", headers=HEADERS, timeout=10)
            
            # 3. Faz o Login de Convidado
            payload = {
                "username": f"guest_{self.device_id[:6]}",
                "password": "guest",
                "device_id": self.device_id
            }
            r = self.session.post(f"{BASE_URL}{API_PATH}/auth/login", json=payload, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                return True
        except: pass
        return False

    def get_headers(self):
        h = HEADERS.copy()
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

s = SpeedFlixSession()

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Ativo</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Valida a sessão antes de buscar
    s.refresh_session()
    
    # Headers para o TiviMate abrir o vídeo
    token_suffix = f"&Authorization=Bearer%20{s.token}" if s.token else ""
    suffix = f"|User-Agent={HEADERS['User-Agent']}&X-Requested-With=site.speedflix{token_suffix}"

    found = 0
    for sid in [1, 2, 3]:
        try:
            # Pede 500 canais de uma vez para não fazer muitas requisições
            url = f"{BASE_URL}{API_PATH}/channels"
            r = s.session.get(url, params={"server_id": sid, "per_page": 500}, headers=s.get_headers(), timeout=20)
            
            if r.status_code == 200:
                items = r.json().get("data", {}).get("items") or r.json().get("items") or []
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or 'Canais').upper()
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{cat} [S{sid}]",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                    found += 1
        except: continue

    if found == 0:
        return "#EXTM3U\n# ERRO: Bloqueio Total de IP no Render.\n# A UNICA SAIDA E USAR O 'RAILWAY.APP' OU 'ZEABUR.COM'."

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0]
    try:
        url = f"{BASE_URL}{API_PATH}/channels/{clean_id}/stream"
        r = s.session.get(url, params={"server_id": sid, "t": int(time.time())}, headers=s.get_headers(), timeout=10)
        video_url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
        if video_url: return redirect(video_url)
    except: pass
    return "Erro", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

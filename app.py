import requests
from flask import Flask, Response, redirect, request
import os
import time
import uuid
import random

app = Flask(__name__)

# Domínio que você forneceu como o portal principal
PORTAL_URL = "https://ycineflix.tudo30.shop"
API_PATH = "/wp-json/xui-pflix/v1"

# User-Agent de um celular Android real e moderno
USER_AGENT = "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"

class SpeedFlixManager:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]
        self.update_headers()

    def update_headers(self, with_auth=True):
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "X-Requested-With": "site.speedflix",
            "Accept": "application/json, text/plain, */*",
            "Origin": PORTAL_URL,
            "Referer": f"{PORTAL_URL}/"
        })
        if with_auth and self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def initialize(self):
        """Simula a abertura do aplicativo passo a passo."""
        try:
            # 1. Visita o portal para ganhar Cookies de sessão
            self.session.get(f"{PORTAL_URL}/", timeout=10)
            
            # 2. Carrega configurações iniciais (Isso libera o firewall)
            conf_res = self.session.get(f"{PORTAL_URL}{API_PATH}/app/config", timeout=10)
            
            # 3. Tenta Login de Convidado
            login_data = {
                "username": f"guest_{self.device_id[:6]}",
                "password": "guest",
                "device_id": self.device_id
            }
            log_res = self.session.post(f"{PORTAL_URL}{API_PATH}/auth/login", json=login_data, timeout=10)
            
            if log_res.status_code == 200:
                data = log_res.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                self.update_headers()
                return True
        except:
            pass
        return False

    def get_channels(self, sid):
        """Busca os canais usando a sessao validada."""
        try:
            url = f"{PORTAL_URL}{API_PATH}/channels"
            # Pedimos 150 por vez (valor seguro para não disparar o firewall)
            params = {"server_id": sid, "per_page": 150, "page": 1}
            r = self.session.get(url, params=params, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                return data.get("data", {}).get("items") or data.get("items") or []
        except:
            pass
        return []

manager = SpeedFlixManager()

@app.route("/")
def index():
    ready = manager.initialize()
    return f"<h1>SpeedFlix Proxy</h1><p>Sessão: {'Ativa' if ready else 'Erro'}</p><p>M3U: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Tenta validar a sessão
    if not manager.initialize() and not manager.token:
        # Se falhar totalmente, tenta um último recurso: pegar o config pra ver se libera
        manager.session.get(f"{PORTAL_URL}{API_PATH}/app/config")

    total = 0
    # Sufixo para o TiviMate enviar os headers corretos
    auth_suffix = f"&Authorization=Bearer%20{manager.token}" if manager.token else ""
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With=site.speedflix{auth_suffix}"

    for sid in [1, 2, 3]:
        channels = manager.get_channels(sid)
        for ch in channels:
            cid = ch.get("id")
            if not cid: continue
            
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            cat = (ch.get('category_name') or 'Canais').upper()
            logo = ch.get("image") or ""
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
            total += 1

    if total == 0:
        m3u.append(f"# ERRO: O servidor {PORTAL_URL} nao entregou canais.")
        m3u.append("# DICA: Abra a pagina inicial do seu App no Render pelo celular antes de carregar no TiviMate.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_id = cid.split('|')[0]
    try:
        url = f"{PORTAL_URL}{API_PATH}/channels/{clean_id}/stream"
        r = manager.session.get(url, params={"server_id": sid, "t": int(time.time())}, timeout=10)
        if r.status_code == 200:
            v_url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
            if v_url: return redirect(v_url)
    except: pass
    return "Erro", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

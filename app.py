import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Servidor
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self, force=False):
        """Obtém o token de acesso simulando o app original."""
        if self.token and not force:
            return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, 
                             headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                return self.token
        except: pass
        return None

    def get_headers(self):
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID}
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "Proxy SpeedFlix Ativo. Use /playlist.m3u no TiviMate."

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url # Já termina com '/'
    m3u = ["#EXTM3U"]
    
    # Sufixo para o TiviMate usar os headers corretos no proxy e no vídeo
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    
    for sid in [1, 2, 3]:
        try:
            # Busca canais (Pega 2 páginas de 100 para ser rápido e não dar erro 500)
            for page in range(1, 3):
                r = requests.get(f"{BASE_URL}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=api.get_headers(), timeout=15)
                if r.status_code != 200: break
                items = r.json().get("data", {}).get("items") or r.json().get("items") or []
                if not items: break
                
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    # Link modificado para aceitar o sufixo do TiviMate
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
        except: continue
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<cid>")
def stream_proxy(sid, cid):
    # O TiviMate envia o ID colado com os headers, aqui nós limpamos
    clean_cid = cid.split('|')[0].split('?')[0]
    
    try:
        headers = api.get_headers()
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json().get("data") or r.json()
            video_url = data.get("stream_url") or data.get("free_url")
            
            if video_url:
                # O SEGREDO: Injetar o token de autorização no link de REDIRECIONAMENTO
                # Isso faz o TiviMate abrir o vídeo com a chave correta.
                token = api.login()
                final_url = f"{video_url}|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
                if token:
                    final_url += f"&Authorization=Bearer%20{token}"
                
                return redirect(final_url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

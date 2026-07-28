import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Servidor - Pobreflix é o motor principal
BASE_URL = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Obtém o token de acesso Bearer simulando o app original."""
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            # Tenta login no domínio principal
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, 
                             headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
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
    return "<h1>Proxy SpeedFlix Ativo</h1><p>Playlist: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Headers para o TiviMate enviar ao Proxy e ao Stream final
    # O sufixo com '|' é o padrão que o TiviMate entende
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    token = api.login()
    if token:
        suffix += f"&Authorization=Bearer {token}"
    
    for sid in [1, 2, 3]:
        page = 1
        while True:
            try:
                r = requests.get(f"{BASE_URL}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=api.get_headers(), timeout=15)
                if r.status_code != 200: break
                
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items: break
                
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    # A rota usa <path:cid> para aceitar o sufixo do TiviMate sem dar 404
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                
                meta = data.get("data", {}).get("meta") or data.get("meta") or {}
                if page >= int(meta.get("total_pages", 1)): break
                page += 1
                time.sleep(0.1) # Evita bloqueio por excesso de requests
            except: break
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    # Limpa o ID do canal (o TiviMate manda o ID + Suffix no path)
    # Exemplo: cid="123|User-Agent=..." -> clean_cid="123"
    clean_cid = cid.split('|')[0].split('?')[0]
    
    try:
        headers = api.get_headers()
        # O parâmetro 't' (timestamp) é obrigatório para o link funcionar
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json().get("data") or r.json()
            video_url = data.get("stream_url") or data.get("free_url")
            
            if video_url:
                # TiviMate já enviará os headers configurados no M3U para este redirect
                return redirect(video_url)
        
        return f"Erro na API SpeedFlix: {r.status_code}", 404
    except Exception as e:
        return f"Erro de Conexão: {str(e)}", 500

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    # Render usa porta 10000 por padrão
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

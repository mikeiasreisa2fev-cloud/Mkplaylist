import requests
import re
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Portal
BASE_DOMAIN = "https://app.pobreflix2.site"
USER_AGENT_WEB = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
USER_AGENT_APP = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Tenta login de convidado para obter o token de stream."""
        if self.token: return self.token
        try:
            url = f"{BASE_DOMAIN}/?rest_route=/xui-pflix/v1/auth/login"
            payload = {"username": f"guest_{self.device_id[:8]}", "password": "guest", "device_id": self.device_id}
            r = requests.post(url, json=payload, headers={"User-Agent": USER_AGENT_APP}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_channels_from_html(self, sid):
        """Varre o site em busca de canais (Modo Scraper)."""
        channels = []
        try:
            # Usa o link de 'todos os canais' que você forneceu
            url = f"{BASE_DOMAIN}/canais/?thema=1&server=speed-{sid}"
            res = requests.get(url, headers={"User-Agent": USER_AGENT_WEB, "Referer": BASE_DOMAIN}, timeout=20)
            
            if res.status_code == 200:
                # Regex flexível para pegar ID e Nome
                # Tenta padrão 1: href com /canais/ID/ e title
                matches = re.findall(r'href=["\'][^"\']*/canais/(\d+)/?[^"\']*["\'][^>]*title=["\']([^"\']*)["\']', res.text)
                
                if not matches:
                    # Tenta padrão 2: link e alt da imagem
                    matches = re.findall(r'canais/(\d+)/.*?alt=["\']([^"\']*)["\']', res.text)

                for cid, name in matches:
                    channels.append({
                        "id": cid, 
                        "name": name.replace("Assistir ", "").strip(),
                        "cat": f"Canais [S{sid}]"
                    })
            else:
                return [f"ERRO_HTTP_{res.status_code}"]
        except Exception as e:
            return [f"ERRO_EXCEPTION_{str(e)}"]
        return channels

api = SpeedFlixAPI()

@app.route("/")
def index():
    return f"<h1>SpeedFlix Proxy Ativo</h1><p>Playlist: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Prepara autenticação para o vídeo
    token = api.login()
    suffix = f"|User-Agent={USER_AGENT_APP}&X-Requested-With={APP_ID}"
    if token: suffix += f"&Authorization=Bearer {token}"

    total = 0
    logs = []

    for sid in [1, 2, 3]:
        channels = api.get_channels_from_html(sid)
        for ch in channels:
            if isinstance(ch, str) and ch.startswith("ERRO"):
                logs.append(f"# DEBUG S{sid}: {ch}")
                continue
                
            cid = ch['id']
            name = f"{ch['name']} [S{sid}]"
            group = ch['cat'].upper()
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="{group}",{name}')
            # Link de vídeo direto via rest_route
            stream_url = f"{BASE_DOMAIN}/?rest_route=/xui-pflix/v1/channels/{cid}/stream&server_id={sid}"
            m3u.append(f"{stream_url}{suffix}")
            total += 1
            
    if total == 0:
        m3u.extend(logs)
        m3u.append("# ERRO: Nenhum canal encontrado. O IP do servidor pode estar bloqueado.")
        m3u.append(f"# SITE TESTADO: {BASE_DOMAIN}")
        
    return Response("\n".join(m3u), mimetype="text/plain")

if __name__ == "__main__":
    # Railway usa a porta 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

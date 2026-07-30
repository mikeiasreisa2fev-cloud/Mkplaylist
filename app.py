import requests
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Domínio Estável do SpeedFlix
BASE_URL = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SessionManager:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def get_auth(self):
        """Obtém o token de autorização Bearer."""
        if self.token: return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}", 
                "password": "guest", 
                "device_id": self.device_id
            }
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers={"User-Agent": USER_AGENT}, timeout=10)
            self.token = r.json().get("data", {}).get("token") or r.json().get("token")
            return self.token
        except: return None

manager = SessionManager()

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Ativo</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    """Gera a playlist M3U com links diretos dos servidores 1, 2 e 3."""
    m3u = ["#EXTM3U"]
    token = manager.get_auth()
    
    # Headers que o TiviMate deve injetar ao abrir o stream
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token: 
        suffix += f"&Authorization=Bearer {token}"

    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        try:
            # Pede a lista de canais para o servidor específico
            r = requests.get(f"{BASE_URL}/channels", params={"server_id": sid, "per_page": 300}, 
                            headers={"User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"}, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    # Nome do canal e Grupo identificados pelo Servidor
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or 'Canais').upper()
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                    # Link direto da fonte SpeedFlix (Bypass de Proxy)
                    # O sufixo permite que o TiviMate envie o Token Bearer na requisição do vídeo
                    m3u.append(f"https://app.pobreflix2.site/stream/{sid}/{cid}{suffix}")
            else:
                print(f"Erro no Servidor {sid}: {r.status_code}")
        except Exception as e:
            print(f"Falha ao conectar no Servidor {sid}: {e}")
            continue
        
    return Response("\n".join(m3u), mimetype="text/plain")

if __name__ == "__main__":
    # Define a porta padrão conforme o serviço de hospedagem
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

import requests
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Domínios
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def get_headers(self, token=None):
        h = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": APP_ID,
            "Accept": "application/json",
            "Connection": "Keep-Alive"
        }
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def login(self):
        """Tenta o login de convidado. Se falhar, retorna o erro para debug."""
        try:
            # Antes do login, o app oficial sempre chama o config
            requests.get(f"{BASE_URL}/app/config", headers=self.get_headers(), timeout=10)
            
            payload = {
                "username": f"guest_{self.device_id[:6]}",
                "password": "guest",
                "device_id": self.device_id
            }
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=self.get_headers(), timeout=10)
            
            if r.status_code == 200:
                self.token = r.json().get("data", {}).get("token") or r.json().get("token")
                return "SUCESSO"
            return f"ERRO {r.status_code}"
        except Exception as e:
            return f"FALHA: {str(e)}"

api = SpeedFlixAPI()

@app.route("/")
def index():
    login_status = api.login()
    return f"""
    <h1>Diagnóstico SpeedFlix</h1>
    <p><b>Status do Login:</b> {login_status}</p>
    <p><b>Link Playlist:</b> <code>{request.host_url}playlist.m3u</code></p>
    <p><i>Se o status for 'ERRO 403', o Render foi bloqueado permanentemente.</i></p>
    """

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Se nao conseguir logar, avisa na playlist
    if api.login() != "SUCESSO" and not api.token:
        m3u.append("# ERRO: Nao foi possivel autenticar no servidor SpeedFlix.")
        return Response("\n".join(m3u), mimetype="text/plain")

    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}&Authorization=Bearer {api.token}"

    for sid in [1, 2, 3]:
        try:
            # Tenta pegar a lista de canais
            r = requests.get(f"{BASE_URL}/channels", 
                             params={"server_id": sid, "per_page": 200},
                             headers=api.get_headers(api.token), timeout=15)
            
            if r.status_code == 200:
                items = r.json().get("data", {}).get("items") or r.json().get("items") or []
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or 'Canais').upper()
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{cat} [S{sid}]",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
        except: continue

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    clean_cid = cid.split('|')[0].split('?')[0]
    try:
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=api.get_headers(api.token), timeout=10)
        if r.status_code == 200:
            url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
            if url: return redirect(url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

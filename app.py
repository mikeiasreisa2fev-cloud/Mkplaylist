import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# CONFIGURAÇÕES
# Usando o domínio do portal que você passou, que costuma ser menos bloqueado
DOMAINS = ["https://ycineflix.tudo30.shop", "https://app.pobreflix2.site"]
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

# CACHE EM MEMÓRIA (Dura 2 horas)
# Isso evita que o SpeedFlix bloqueie o IP do Render por excesso de pedidos
CACHE = {"m3u": None, "time": 0}

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.base = DOMAINS[0]
        self.did = "speed_box_" + str(uuid.uuid4())[:8]

    def call(self, path, method="GET", params=None, json_data=None):
        """Faz chamadas à API usando a técnica de Bypass (rest_route)."""
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        # Bypass de Firewall do WordPress
        url = f"{self.base}/"
        q = {"rest_route": f"/xui-pflix/v1/{path}"}
        if params: q.update(params)

        try:
            if method == "POST":
                return requests.post(url, params=q, json=json_data, headers=headers, timeout=12)
            return requests.get(url, params=q, headers=headers, timeout=12)
        except:
            return None

    def login(self):
        """Realiza login de convidado para validar a sessão."""
        if self.token: return True
        for d in DOMAINS:
            self.base = d
            # O app oficial sempre pede o config antes do login
            self.call("app/config")
            
            res = self.call("auth/login", "POST", json_data={
                "username": f"guest_{self.did}", 
                "password": "guest", 
                "device_id": self.did
            })
            if res and res.status_code == 200:
                data = res.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return True
        return False

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Estabilizado</h1><p>Playlist: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    global CACHE
    now = time.time()
    
    # Se tivermos a lista salva a menos de 2 horas, entrega ela na hora!
    if CACHE["m3u"] and (now - CACHE["time"] < 7200):
        return Response(CACHE["m3u"], mimetype="text/plain")

    if not api.login():
        return "#EXTM3U\n# ERRO: O Render foi bloqueado pelo SpeedFlix (403).\n# Tente abrir este link no 4G do celular para testar."

    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Headers que o TiviMate usará para abrir o vídeo
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}&Authorization=Bearer {api.token}"

    for sid in [1, 2, 3]:
        # Busca as 2 primeiras páginas de cada servidor (aprox 400 canais)
        for p in [1, 2]:
            res = api.call("channels", params={"server_id": sid, "per_page": 100, "page": p})
            if res and res.status_code == 200:
                data = res.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items: break
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat}",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
            else:
                break
        time.sleep(1) # Pausa para não ser bloqueado

    result = "\n".join(m3u)
    if len(m3u) > 1:
        CACHE = {"m3u": result, "time": now} # Salva no Cache
        
    return Response(result, mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    """Obtém o link de vídeo real no momento do Play."""
    # Limpa o ID de qualquer sufixo do TiviMate
    clean_id = cid.split('|')[0].split('?')[0]
    
    res = api.call(f"channels/{clean_id}/stream", params={"server_id": sid, "t": int(time.time())})
    if res and res.status_code == 200:
        data = res.json()
        url = data.get("data", {}).get("stream_url") or data.get("stream_url")
        if url:
            return redirect(url)
            
    return "Offline", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

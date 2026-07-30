import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Domínio principal que você forneceu
BASE_URL = "https://app.pobreflix2.site"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Obtém o token de acesso usando a rota de bypass rest_route."""
        if self.token: return self.token
        try:
            # Bypass: acessa o login através de uma consulta de rota interna
            url = f"{BASE_URL}/"
            params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {
                "username": f"guest_{self.device_id[:6]}", 
                "password": "guest", 
                "device_id": self.device_id
            }
            r = requests.post(url, params=params, json=payload, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_channels(self, sid):
        """Busca canais usando a técnica rest_route."""
        token = self.login()
        url = f"{BASE_URL}/"
        # Usamos per_page=400 para tentar pegar todos de uma vez
        params = {
            "rest_route": "/xui-pflix/v1/channels",
            "server_id": sid,
            "per_page": 400
        }
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            if r.status_code == 200:
                data = r.json()
                return data.get("data", {}).get("items") or data.get("items") or []
        except: pass
        return []

api = SpeedFlixAPI()

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Ativo no Railway</h1><p>Playlist: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Headers para o TiviMate abrir o vídeo com autorização
    token = api.login()
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token: suffix += f"&Authorization=Bearer {token}"

    total = 0
    for sid in [1, 2, 3]:
        items = api.get_channels(sid)
        for ch in items:
            cid = ch.get("id")
            if not cid: continue
            
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            cat = (ch.get('category_name') or 'Canais').upper()
            logo = ch.get("image") or ""
            
            # tvg-id único para bater com o EPG
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
            # Link direto do servidor de vídeo oficial (Formato m3u8 que descobrimos no seu HTML)
            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8{suffix}")
            total += 1

    if total == 0:
        m3u.append("# ERRO: IP do Railway bloqueado. Tente abrir este link no 4G do celular.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera um EPG básico unificado."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Proxy")
    for sid in [1, 2, 3]:
        channels = api.get_channels(sid)
        for ch in channels[:40]: # Limite para não dar timeout
            cid = ch.get("id")
            c_elem = ET.SubElement(tv, "channel", id=f"s{sid}_{cid}")
            ET.SubElement(c_elem, "display-name").text = f"{ch.get('name')} [S{sid}]"
    return Response(ET.tostring(tv, encoding="utf-8", xml_declaration=True), mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

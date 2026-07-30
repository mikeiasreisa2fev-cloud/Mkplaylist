import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid
from datetime import datetime

app = Flask(__name__)

# Configurações do Portal
BASE_SITE = "https://app.pobreflix2.site"
API_BASE = f"{BASE_SITE}/wp-json/xui-pflix/v1"

HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept": "application/json",
    "Connection": "Keep-Alive"
}

class SpeedSession:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]
        self.last_login = 0

    def login(self):
        """Obtém ou renova o token de acesso Bearer."""
        now = time.time()
        if self.token and (now - self.last_login < 3000):
            return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            # Tenta login via bypass de rota (rest_route) que é mais estável
            r = requests.post(f"{BASE_SITE}/", params={"rest_route": "/xui-pflix/v1/auth/login"}, 
                             json=payload, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                self.last_login = now
                return self.token
        except: pass
        return None

    def fetch(self, endpoint, params=None):
        """Faz a requisição de dados com autorização."""
        token = self.login()
        h = HEADERS.copy()
        if token: h["Authorization"] = f"Bearer {token}"
        
        try:
            p = {"rest_route": f"/xui-pflix/v1/{endpoint}", **(params or {})}
            r = requests.get(f"{BASE_SITE}/", params=p, headers=h, timeout=15)
            if r.status_code == 200: return r.json()
        except: pass
        return None

speed_api = SpeedSession()

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Master Proxy (Railway)</h1><p>Playlist: <b>{h}playlist.m3u</b><br>EPG: <b>{h}epg.xml</b></p>"

@app.route("/playlist.m3u")
def m3u_route():
    m3u = ["#EXTM3U"]
    host = request.host_url
    token = speed_api.login()
    suffix = f"|User-Agent=okhttp/4.12.0&X-Requested-With=site.speedflix"
    if token: suffix += f"&Authorization=Bearer {token}"

    for sid in [1, 2, 3]:
        # Pega até 2 páginas por servidor (aprox 200 canais cada)
        for page in [1, 2]:
            data = speed_api.fetch("channels", {"server_id": sid, "per_page": 100, "page": page})
            if not data: break
            items = data.get("data", {}).get("items") or data.get("items") or []
            if not items: break
            
            for ch in items:
                cid = ch.get("id")
                name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                cat = (ch.get('category_name') or 'Canais').upper()
                logo = ch.get("image") or ""
                m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
            if len(items) < 100: break
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg_route():
    """Gera o EPG separado dos canais."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix-EPG")
    for sid in [1, 2]:
        data = speed_api.fetch("channels", {"server_id": sid, "per_page": 40})
        if data:
            items = data.get("data", {}).get("items") or data.get("items") or []
            for ch in items:
                cid = ch.get("id")
                uid = f"s{sid}_{cid}"
                ET.SubElement(tv, "channel", id=uid).append(ET.Element("display-name"))
                tv.find(f"channel[@id='{uid}']/display-name").text = f"{ch.get('name')} [S{sid}]"
                
                e_data = speed_api.fetch(f"channels/{cid}/epg", {"server_id": sid, "limit": 5})
                if e_data:
                    listings = e_data.get("data", {}).get("epg", {}).get("epg_listings", []) or []
                    for p in listings:
                        try:
                            start = datetime.fromtimestamp(int(p['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                            stop = datetime.fromtimestamp(int(p['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                            prog = ET.SubElement(tv, "programme", start=start, stop=stop, channel=uid)
                            ET.SubElement(prog, "title", lang="pt").text = p.get("title")
                        except: continue
    return Response(ET.tostring(tv, encoding="utf-8", xml_declaration=True), mimetype="application/xml")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_route(sid, cid):
    clean_id = cid.split('|')[0].split('?')[0]
    data = speed_api.fetch(f"channels/{clean_id}/stream", {"server_id": sid, "t": int(time.time())})
    if data:
        url = data.get("data", {}).get("stream_url") or data.get("stream_url")
        if url: return redirect(url)
    return "Offline", 404

if __name__ == "__main__":
    # O Railway usa a porta 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

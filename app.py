import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid
from datetime import datetime

app = Flask(__name__)

# Configurações do Servidor SpeedFlix
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixSession:
    def __init__(self):
        self.token = None
        self.last_login = 0
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self, force=False):
        now = time.time()
        if self.token and (now - self.last_login < 3600) and not force:
            return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Content-Type": "application/json"}
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                self.last_login = now
                return self.token
        except: pass
        return None

    def get_headers(self):
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Accept": "application/json"}
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

api = SpeedFlixSession()

def fetch_channels_list(sid):
    channels = []
    for page in range(1, 5): 
        try:
            r = requests.get(f"{BASE_URL}/channels", 
                            params={"server_id": sid, "per_page": 100, "page": page},
                            headers=api.get_headers(), timeout=15)
            if r.status_code != 200: break
            data = r.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            if not items: break
            for item in items:
                item['sid'] = sid
            channels.extend(items)
            meta = data.get("data", {}).get("meta") or data.get("meta") or {}
            if page >= int(meta.get("total_pages", 1)): break
        except: break
    return channels

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Master Proxy Ativo</h1><p>Playlist: <b>{h}playlist.m3u</b><br>EPG: <b>{h}epg.xml</b></p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    token = api.login()
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token: suffix += f"&Authorization=Bearer {token}"

    for sid in [1, 2, 3]:
        channels = fetch_channels_list(sid)
        for ch in channels:
            cid = ch.get("id")
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            cat = ch.get('category_name') or 'Canais'
            group = f"{cat.upper()} [S{sid}]"
            logo = ch.get("image") or ""
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    clean_cid = cid.split('|')[0].split('?')[0]
    try:
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=api.get_headers(), timeout=15)
        if r.status_code == 200:
            video_url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
            if video_url: return redirect(video_url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Proxy")
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import uuid

app = Flask(__name__)

BASE_URL = "https://speedflix02.com/wp-json/xui-pflix/v1"
# Headers que imitam o comportamento exato do App Android
DEFAULT_HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Connection": "Keep-Alive"
}

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4())[:16]

    def get_token(self):
        """Tenta obter um token de acesso de convidado."""
        if self.token: return self.token
        
        try:
            # O app tenta primeiro um login anônimo/guest
            payload = {
                "username": f"guest_{self.device_id}",
                "password": "guest",
                "device_id": self.device_id
            }
            res = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=DEFAULT_HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                # O token costuma vir em data.token ou data.access_token
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except:
            pass
        return None

    def call(self, endpoint, params=None, method="GET"):
        headers = DEFAULT_HEADERS.copy()
        token = self.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method == "GET":
                return requests.get(f"{BASE_URL}/{endpoint}", params=params, headers=headers, timeout=15)
            else:
                return requests.post(f"{BASE_URL}/{endpoint}", json=params, headers=headers, timeout=15)
        except:
            return None

api = SpeedFlixAPI()

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    
    # Servidores 1, 2 e 3
    total = 0
    for server_id in [1, 2, 3]:
        res = api.call("channels", params={"server_id": server_id, "per_page": 200})
        if res and res.status_code == 200:
            data = res.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            for ch in items:
                ch_id = ch.get("id")
                if not ch_id: continue
                name = ch.get("name") or ch.get("title")
                logo = ch.get("image") or ""
                group = ch.get("category_name") or "SpeedFlix"
                
                m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}/stream/{server_id}/{ch_id}")
                total += 1

    if total == 0:
        m3u.append("# ERRO: Servidor exige login manual. Abra o app SpeedFlix no celular uma vez na mesma rede.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv")
    # Para o EPG, pegamos apenas os primeiros 50 canais para não travar o Render (limite de memória)
    res = api.call("channels", params={"server_id": 1, "per_page": 50})
    if res and res.status_code == 200:
        items = res.json().get("data", {}).get("items") or []
        for ch in items:
            ch_id = ch.get("id")
            ET.SubElement(tv, "channel", id=str(ch_id)).append(ET.Element("display-name"))
            tv.find(f"channel[@id='{ch_id}']/display-name").text = ch.get("name")
            
            # Busca EPG do canal
            epg_res = api.call(f"channels/{ch_id}/epg", params={"server_id": 1, "limit": 10})
            if epg_res and epg_res.status_code == 200:
                listings = epg_res.json().get("data", {}).get("epg", {}).get("epg_listings", [])
                for prog in listings:
                    start = datetime.fromtimestamp(int(prog['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                    stop = datetime.fromtimestamp(int(prog['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                    p = ET.SubElement(tv, "programme", start=start, stop=stop, channel=str(ch_id))
                    ET.SubElement(p, "title").text = prog.get("title")

    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream(server_id, channel_id):
    res = api.call(f"channels/{channel_id}/stream", params={"server_id": server_id})
    if res and res.status_code == 200:
        url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
        if url: return redirect(url)
    return "Erro", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

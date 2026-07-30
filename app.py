import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
from datetime import datetime

app = Flask(__name__)

# Configurações de Domínio e Identificação
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept": "application/json"
}

def get_channels(server_id):
    """Busca a lista de canais de um servidor específico."""
    try:
        # Tenta o endpoint de sincronização que é mais completo
        url = f"{BASE_URL}/channels/sync"
        params = {"server_id": server_id}
        res = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        if res.status_code != 200:
            # Fallback para o endpoint normal
            url = f"{BASE_URL}/channels"
            params = {"server_id": server_id, "per_page": 500}
            res = requests.get(url, params=params, headers=HEADERS, timeout=15)
            
        if res.status_code == 200:
            data = res.json()
            return data.get("data", {}).get("items") or data.get("items") or []
    except:
        pass
    return []

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Proxy</h1><p>Playlist: {h}playlist.m3u</p><p>EPG: {h}epg.xml</p>"

@app.route("/playlist.m3u")
def playlist():
    """Gera a lista de canais unificada [S1, S2, S3]."""
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    for sid in [1, 2, 3]:
        items = get_channels(sid)
        for ch in items:
            cid = ch.get("id")
            if not cid: continue
            
            # Identificação no Nome e no Grupo
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
            logo = ch.get("image") or ""
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Extrai apenas o EPG dos canais (Focado no Servidor 1 e 2)."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix-EPG")
    
    # Buscamos os canais para criar os IDs no XML
    for sid in [1, 2]:
        channels = get_channels(sid)
        for ch in channels[:50]: # Limite de 50 canais por servidor para o Render nao travar
            cid = ch.get("id")
            unique_id = f"s{sid}_{cid}"
            
            chan_elem = ET.SubElement(tv, "channel", id=unique_id)
            ET.SubElement(chan_elem, "display-name").text = f"{ch.get('name')} [S{sid}]"
            
            # Busca a programação real
            try:
                e_url = f"{BASE_URL}/channels/{cid}/epg"
                e_res = requests.get(e_url, params={"server_id": sid, "limit": 5}, headers=HEADERS, timeout=5)
                if e_res.status_code == 200:
                    listings = e_res.json().get("data", {}).get("epg", {}).get("epg_listings", [])
                    for p in listings:
                        start = datetime.fromtimestamp(int(p['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                        stop = datetime.fromtimestamp(int(p['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                        prog = ET.SubElement(tv, "programme", start=start, stop=stop, channel=unique_id)
                        ET.SubElement(prog, "title", lang="pt").text = p.get("title")
            except: continue
            
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Gera o link de vídeo na hora do play."""
    try:
        url = f"{BASE_URL}/channels/{cid}/stream"
        res = requests.get(url, params={"server_id": sid, "t": int(time.time())}, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            v_url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
            if v_url: return redirect(v_url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

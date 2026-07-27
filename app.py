import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Lista de domínios para tentar burlar o bloqueio
DOMAINS = [
    "https://ycineflix.tudo30.shop",
    "https://app.pobreflix2.site",
    "https://speedflix02.com"
]
API_PATH = "/wp-json/xui-pflix/v1"

# Simula um celular Android real
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://ycineflix.tudo30.shop/",
    "Origin": "https://ycineflix.tudo30.shop"
}

def fetch_data(endpoint, params=None):
    """Tenta buscar dados nos domínios disponíveis."""
    for base in DOMAINS:
        url = f"{base}{API_PATH}/{endpoint}"
        try:
            res = requests.get(url, params=params, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return data.get("data") or data
        except:
            continue
    return None

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed = set()
    
    # Itera pelos servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        # Tenta o modo sync (mais rápido)
        data = fetch_data("channels/sync", {"server_id": sid})
        if not data:
            # Tenta o modo lista normal
            data = fetch_data("channels", {"server_id": sid, "per_page": 500})
            
        if data:
            items = data if isinstance(data, list) else data.get("items", [])
            for ch in items:
                ch_id = ch.get("id")
                if not ch_id or ch_id in processed: continue
                processed.add(ch_id)
                
                name = ch.get("name") or ch.get("title")
                logo = ch.get("image") or ""
                group = ch.get("category_name") or f"Servidor {sid}"
                
                m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}/stream/{sid}/{ch_id}")
    
    if len(m3u) <= 1:
        m3u.append("# ERRO: O RENDER ESTA BLOQUEADO.")
        m3u.append("# SOLUCAO: Crie uma conta no KOYEB.COM e suba este codigo la.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv", generator_info_name="YcineFlix")
    data = fetch_data("channels", {"server_id": 1, "per_page": 50})
    if data:
        items = data.get("items", [])
        for ch in items:
            ch_id = ch.get("id")
            ch_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(ch_elem, "display-name").text = ch.get("name") or ch.get("title")
            
    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    return Response(xml_data, mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    # Pega o link do vídeo na hora do play
    data = fetch_data(f"channels/{cid}/stream", {"server_id": sid})
    if data:
        url = data.get("stream_url")
        if url: return redirect(url)
    return "Offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

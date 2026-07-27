import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Configurações do SpeedFlix
BASE_URL = "https://speedflix02.com/wp-json/xui-pflix/v1"
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

def get_server_ids():
    """Descobre os IDs dos servidores ativos dinamicamente."""
    try:
        response = requests.get(f"{BASE_URL}/servers", headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # A API retorna Lbs<Ls57> -> { "success": true, "data": { "items": [...] } }
            envelope = data.get("data", {})
            items = envelope.get("items", [])
            ids = [s.get("a") or s.get("id") for s in items if (s.get("a") or s.get("id"))]
            if ids: return ids
    except:
        pass
    return [1, 2, 3] # Fallback se falhar

def get_channels(server_id):
    """Busca a lista de canais de um servidor específico."""
    channels = []
    page = 1
    while True:
        try:
            print(f"Buscando canais - Servidor {server_id}, Página {page}...")
            response = requests.get(f"{BASE_URL}/channels", params={
                "server_id": server_id,
                "page": page,
                "per_page": 100
            }, headers=HEADERS, timeout=15)
            
            if response.status_code != 200:
                break

            data = response.json()
            # Estrutura: { "success": true, "data": { "items": [...], "meta": { "total_pages": X } } }
            envelope = data.get("data", {})
            items = envelope.get("items")
            
            if not items:
                # Tenta pegar da raiz se não estiver dentro de 'data'
                items = data.get("items")
                
            if not items:
                break

            channels.extend(items)

            # Verifica paginação
            meta = envelope.get("meta", {})
            total_pages = meta.get("total_pages") or data.get("total_pages", 1)
            
            if page >= int(total_pages):
                break
            page += 1
        except Exception as e:
            print(f"Erro no servidor {server_id}: {e}")
            break
    return channels

def get_epg_data(channel_id, server_id):
    """Busca a programação (EPG) de um canal."""
    try:
        response = requests.get(f"{BASE_URL}/channels/{channel_id}/epg", params={
            "server_id": server_id,
            "limit": 20
        }, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Lbs<Lgw0> -> { "data": { "epg": { "epg_listings": [...] } } }
            epg_obj = data.get("data", {}).get("epg", {}) or data.get("epg", {})
            return epg_obj.get("epg_listings", [])
    except:
        pass
    return []

@app.route("/")
def index():
    host = request.host_url.rstrip('/')
    return f"""
    <h1>SpeedFlix Proxy Ativo</h1>
    <p>Use estes links no TiviMate:</p>
    <ul>
        <li><b>Playlist M3U:</b> <code>{host}/playlist.m3u</code></li>
        <li><b>Guia EPG:</b> <code>{host}/epg.xml</code></li>
    </ul>
    """

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed_ids = set()
    
    servers = get_server_ids()
    for server_id in servers:
        channels = get_channels(server_id)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id or ch_id in processed_ids:
                continue
            
            processed_ids.add(ch_id)
            name = ch.get("name") or ch.get("title") or f"Canal {ch_id}"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or "SpeedFlix"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{server_id}/{ch_id}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv", generator_info_name="SpeedFlix")
    processed_ids = set()
    
    servers = get_server_ids()
    for server_id in servers:
        channels = get_channels(server_id)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id or ch_id in processed_ids:
                continue
            processed_ids.add(ch_id)
            
            channel_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(channel_elem, "display-name").text = ch.get("name") or ch.get("title")
            
            listings = get_epg_data(ch_id, server_id)
            for prog in listings:
                start = prog.get("start_timestamp")
                stop = prog.get("stop_timestamp")
                if start and stop:
                    p = ET.SubElement(tv, "programme", 
                                     start=datetime.fromtimestamp(int(start)).strftime("%Y%m%d%H%M%S +0000"),
                                     stop=datetime.fromtimestamp(int(stop)).strftime("%Y%m%d%H%M%S +0000"),
                                     channel=str(ch_id))
                    ET.SubElement(p, "title", lang="pt").text = prog.get("title")
                    if prog.get("description"):
                        ET.SubElement(p, "desc", lang="pt").text = prog.get("description")

    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    return Response(xml_data, mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream_proxy(server_id, channel_id):
    try:
        res = requests.get(f"{BASE_URL}/channels/{channel_id}/stream", 
                          params={"server_id": server_id, "t": int(datetime.now().timestamp())},
                          headers=HEADERS, timeout=10)
        if res.status_code == 200:
            url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
            if url: return redirect(url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

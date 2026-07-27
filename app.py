import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Domínio principal que o app usa internamente
BASE_URL = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"

HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Accept-Language": "pt-BR",
    "Connection": "Keep-Alive"
}

def get_api_data(endpoint, params=None):
    try:
        # Tenta uma requisição limpa
        res = requests.get(f"{BASE_URL}/{endpoint}", params=params, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            data = res.json()
            # Retorna o campo data ou a raiz do json
            return data.get("data") or data
    except:
        return None

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed_ids = set()
    
    # Servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        # Usamos o modo 'sync' que retorna todos os canais de uma vez
        data = get_api_data("channels/sync", {"server_id": sid})
        if not data:
            # Se sync falhar, tenta o normal com muitos por página
            data = get_api_data("channels", {"server_id": sid, "per_page": 500})
            
        if data:
            items = data if isinstance(data, list) else data.get("items", [])
            for ch in items:
                ch_id = ch.get("id")
                if not ch_id or ch_id in processed_ids: continue
                processed_ids.add(ch_id)
                
                name = ch.get("name") or ch.get("title")
                logo = ch.get("image") or ""
                group = ch.get("category_name") or f"Servidor {sid}"
                
                m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}/stream/{sid}/{ch_id}")

    if len(m3u) <= 1:
        m3u.append("# ERRO: IP Bloqueado. O servidor nao retornou dados.")
        m3u.append(f"# Tentativa em: {BASE_URL}")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv")
    data = get_api_data("channels", {"server_id": 1, "per_page": 50})
    if data:
        items = data.get("items", [])
        for ch in items:
            ch_id = ch.get("id")
            ch_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(ch_elem, "display-name").text = ch.get("name")
            
            # Pega EPG básico
            epg_data = get_api_data(f"channels/{ch_id}/epg", {"server_id": 1, "limit": 5})
            if epg_data:
                listings = epg_data.get("epg", {}).get("epg_listings", []) or epg_data.get("epg_listings", [])
                for p in listings:
                    try:
                        start = datetime.fromtimestamp(int(p['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                        stop = datetime.fromtimestamp(int(p['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                        prog = ET.SubElement(tv, "programme", start=start, stop=stop, channel=str(ch_id))
                        ET.SubElement(prog, "title").text = p.get("title")
                    except: continue
                    
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream(server_id, channel_id):
    data = get_api_data(f"channels/{channel_id}/stream", {"server_id": server_id})
    if data:
        url = data.get("stream_url")
        if url: return redirect(url)
    return "Erro", 404

if __name__ == "__main__":
    # Koyeb usa a porta da variável de ambiente PORT
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

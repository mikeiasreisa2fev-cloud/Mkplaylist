import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Configurações do SpeedFlix
BASE_URL = "https://speedflix02.com/wp-json/xui-pflix/v1"
SERVERS = [1, 2, 3]

def get_channels(server_id):
    """Busca a lista de canais de um servidor específico."""
    channels = []
    page = 1
    while True:
        try:
            response = requests.get(f"{BASE_URL}/channels", params={
                "server_id": server_id,
                "page": page,
                "per_page": 100
            }, timeout=15)
            if response.status_code != 200:
                break

            data = response.json()
            # A API retorna os itens dentro de 'items' ou 'data.items'
            items = data.get("items") or data.get("data", {}).get("items")
            if not items:
                break

            channels.extend(items)

            total_pages = data.get("total_pages") or data.get("data", {}).get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1
        except Exception:
            break
    return channels

def get_epg_data(channel_id, server_id):
    """Busca a programação (EPG) de um canal."""
    try:
        response = requests.get(f"{BASE_URL}/channels/{channel_id}/epg", params={
            "server_id": server_id,
            "limit": 20
        }, timeout=10)
        if response.status_code == 200:
            data = response.json()
            epg_obj = data.get("epg") or data.get("data", {}).get("epg")
            if epg_obj:
                return epg_obj.get("epg_listings", [])
    except Exception:
        pass
    return []

@app.route("/")
def index():
    host = request.host_url.rstrip('/')
    return f"""
    <h1>SpeedFlix para TiviMate</h1>
    <p>Use os links abaixo no seu player:</p>
    <ul>
        <li><b>Playlist (M3U):</b> <code>{host}/playlist.m3u</code></li>
        <li><b>EPG (XML):</b> <code>{host}/epg.xml</code></li>
    </ul>
    """

@app.route("/playlist.m3u")
def playlist():
    """Gera a playlist M3U compatível com TiviMate."""
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]

    processed_ids = set()

    for server_id in SERVERS:
        channels = get_channels(server_id)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id or ch_id in processed_ids:
                continue

            processed_ids.add(ch_id)
            name = ch.get("name") or ch.get("title") or f"Canal {ch_id}"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or f"Servidor {server_id}"

            # Formato EXTINF: tvg-id para o EPG, tvg-logo para o ícone
            line = f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}'
            m3u.append(line)
            # Link de stream via proxy interno para pegar a URL atualizada no momento do play
            m3u.append(f"{host}/stream/{server_id}/{ch_id}")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera o guia de programação no padrão XMLTV."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix EPG")
    processed_ids = set()

    for server_id in SERVERS:
        channels = get_channels(server_id)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id or ch_id in processed_ids:
                continue

            processed_ids.add(ch_id)
            name = ch.get("name") or ch.get("title") or "Unknown"

            # Canal no XMLTV
            channel_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(channel_elem, "display-name").text = name

            # Programação
            listings = get_epg_data(ch_id, server_id)
            for prog in listings:
                start_ts = prog.get("start_timestamp")
                stop_ts = prog.get("stop_timestamp")
                title = prog.get("title")
                desc = prog.get("description")

                if start_ts and stop_ts and title:
                    start_time = datetime.fromtimestamp(int(start_ts)).strftime("%Y%m%d%H%M%S +0000")
                    stop_time = datetime.fromtimestamp(int(stop_ts)).strftime("%Y%m%d%H%M%S +0000")

                    prog_elem = ET.SubElement(tv, "programme",
                                             start=start_time,
                                             stop=stop_time,
                                             channel=str(ch_id))
                    ET.SubElement(prog_elem, "title", lang="pt").text = title
                    if desc:
                        ET.SubElement(prog_elem, "desc", lang="pt").text = desc

    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    return Response(xml_data, mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream_proxy(server_id, channel_id):
    """Redireciona para o link de stream real obtido da API."""
    try:
        t = int(time.time())
        response = requests.get(f"{BASE_URL}/channels/{channel_id}/stream", params={
            "server_id": server_id,
            "t": t
        }, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # O link real costuma estar em 'stream_url' ou dentro de 'data'
            stream_url = data.get("stream_url") or data.get("data", {}).get("stream_url")
            if stream_url:
                return redirect(stream_url)
    except Exception:
        pass

    return "Stream indisponível", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

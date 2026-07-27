import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Tente usar o domínio alternativo se o principal falhar
DOMAINS = ["https://speedflix02.com", "https://app.pobreflix2.site", "https://speedflix.top"]
BASE_PATH = "/wp-json/xui-pflix/v1"

HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

def get_base_url():
    for domain in DOMAINS:
        url = domain + BASE_PATH
        try:
            res = requests.get(f"{url}/app/config", headers=HEADERS, timeout=5)
            if res.status_code == 200:
                print(f"Usando Base URL: {url}")
                return url
        except:
            continue
    return DOMAINS[0] + BASE_PATH

BASE_URL = get_base_url()

def get_server_ids():
    try:
        response = requests.get(f"{BASE_URL}/servers", headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # envelope data logic
            items = data.get("data", {}).get("items", []) or data.get("items", [])
            ids = []
            for item in items:
                # O ID pode estar em 'a' ou 'id'
                sid = item.get("a") or item.get("id")
                if sid: ids.append(sid)
            if ids: return ids
    except Exception as e:
        print(f"Erro ao buscar servidores: {e}")
    return [1, 2, 3]

def get_channels(server_id):
    channels = []
    page = 1
    while True:
        try:
            response = requests.get(f"{BASE_URL}/channels", params={
                "server_id": server_id,
                "page": page,
                "per_page": 100
            }, headers=HEADERS, timeout=10)

            if response.status_code != 200:
                print(f"Erro {response.status_code} no servidor {server_id}")
                break

            data = response.json()
            envelope = data.get("data", {})
            items = envelope.get("items") or data.get("items")

            if not items: break

            channels.extend(items)

            meta = envelope.get("meta", {})
            total_pages = meta.get("total_pages") or data.get("total_pages", 1)

            if page >= int(total_pages): break
            page += 1
        except Exception as e:
            print(f"Erro ao buscar canais: {e}")
            break
    return channels

@app.route("/")
def index():
    host = request.host_url.rstrip('/')
    return f"Playlist: {host}/playlist.m3u<br>EPG: {host}/epg.xml"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]

    servers = get_server_ids()
    total_found = 0

    for server_id in servers:
        channels = get_channels(server_id)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id: continue

            name = ch.get("name") or ch.get("title") or f"Canal {ch_id}"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or "SpeedFlix"

            m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{server_id}/{ch_id}")
            total_found += 1

    if total_found == 0:
        m3u.append("# ERRO: Nenhum canal encontrado. Verifique a conexão com a API.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv", generator_info_name="SpeedFlix")
    servers = get_server_ids()
    for server_id in servers:
        channels = get_channels(server_id)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id: continue
            channel_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(channel_elem, "display-name").text = ch.get("name") or ch.get("title")

    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    return Response(xml_data, mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream_proxy(server_id, channel_id):
    try:
        res = requests.get(f"{BASE_URL}/channels/{channel_id}/stream",
                          params={"server_id": server_id},
                          headers=HEADERS, timeout=10)
        if res.status_code == 200:
            url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
            if url: return redirect(url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

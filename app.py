import requests
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Configurações baseadas nos links que você enviou
BASE_SITE = "https://app.pobreflix2.site"
API_PATH = "/wp-json/xui-pflix/v1"
SERVERS = ["speed-1", "speed-2", "speed-3"]

# Header de navegador comum para evitar bloqueio de IP
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://app.pobreflix2.site/canais/",
    "Connection": "keep-alive"
}

def get_channels_from_server(server_name):
    """Acessa o site e tenta extrair a lista de canais."""
    channels = []
    try:
        # Tenta primeiro via API usando o nome do servidor (1, 2 ou 3)
        sid = server_name.split("-")[1]
        url = f"{BASE_SITE}{API_PATH}/channels"
        params = {"server_id": sid, "per_page": 400}
        
        res = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            data = res.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            if items: return items

        # Se a API falhar (bloqueio de IP), tentamos "raspar" o HTML da página que você mandou
        page_url = f"{BASE_SITE}/canais/?thema=1&server={server_name}"
        res_page = requests.get(page_url, headers=HEADERS, timeout=15)
        if res_page.status_code == 200:
            # Busca padrões de IDs e nomes no HTML (ex: data-id="123" ou links /canais/123/)
            html = res_page.text
            # Esta é uma busca genérica, se o site mudar o layout pode precisar de ajuste
            found_ids = re.findall(r'href=".*/canais/(\d+)/"', html)
            for cid in set(found_ids):
                channels.append({"id": cid, "name": f"Canal {cid}", "server_id": sid})
    except Exception as e:
        print(f"Erro ao processar {server_name}: {e}")
    
    return channels

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed_ids = set()
    
    for sname in SERVERS:
        sid = sname.split("-")[1]
        canals = get_channels_from_server(sname)
        for c in canals:
            ch_id = c.get("id")
            if not ch_id or ch_id in processed_ids: continue
            processed_ids.add(ch_id)
            
            name = c.get("name") or c.get("title") or f"Canal {ch_id}"
            logo = c.get("image") or ""
            group = c.get("category_name") or f"Servidor {sid}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{sid}/{ch_id}")

    if len(m3u) <= 1:
        m3u.append("# ERRO: O servidor do Pobreflix bloqueou o Render.")
        m3u.append("# SOLUCAO: Use o servico gratuito KOYEB.COM para hospedar este script.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv")
    # Pega canais para o EPG
    sid = "1"
    url = f"{BASE_SITE}{API_PATH}/channels"
    try:
        res = requests.get(url, params={"server_id": sid, "per_page": 50}, headers=HEADERS, timeout=10)
        items = res.json().get("data", {}).get("items", []) or []
        for ch in items:
            ch_id = ch.get("id")
            ch_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(ch_elem, "display-name").text = ch.get("name")
    except: pass
    
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<string:server_id>/<int:channel_id>")
def stream(server_id, channel_id):
    try:
        # Obtém o link real de vídeo
        url = f"{BASE_SITE}{API_PATH}/channels/{channel_id}/stream"
        res = requests.get(url, params={"server_id": server_id}, headers=HEADERS, timeout=10)
        data = res.json()
        stream_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
        if stream_url:
            return redirect(stream_url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

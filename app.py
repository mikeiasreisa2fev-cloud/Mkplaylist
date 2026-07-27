import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Domínios em ordem de prioridade
DOMAINS = [
    "https://app.pobreflix2.site/wp-json/xui-pflix/v1",
    "https://speedflix02.com/wp-json/xui-pflix/v1",
    "https://speedflix.top/wp-json/xui-pflix/v1"
]

HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Connection": "keep-alive",
    "Accept-Language": "pt-BR",
    "Host": "app.pobreflix2.site" # Força o host para evitar bloqueio de proxy
}

def get_data(endpoint, params=None):
    """Tenta buscar dados nos diversos domínios de backup."""
    for base in DOMAINS:
        url = f"{base}/{endpoint}"
        try:
            # Atualiza o Host no header conforme o domínio testado
            current_host = base.split("//")[1].split("/")[0]
            headers = HEADERS.copy()
            headers["Host"] = current_host
            
            res = requests.get(url, params=params, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                # O servidor pode retornar os dados direto ou dentro de uma chave 'data'
                return data.get("data") or data
        except:
            continue
    return None

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    
    # O endpoint 'channels/sync' costuma liberar mais fácil que o 'channels' comum
    total_canais = 0
    for sid in [1, 2, 3]:
        # Tenta o modo Sync primeiro, depois o normal
        data = get_data("channels/sync", {"server_id": sid}) or get_data("channels", {"server_id": sid, "per_page": 400})
        
        if data:
            items = data.get("items") or (data if isinstance(data, list) else [])
            for ch in items:
                if not isinstance(ch, dict): continue
                ch_id = ch.get("id")
                if not ch_id: continue
                
                name = ch.get("name") or ch.get("title") or f"Canal {ch_id}"
                logo = ch.get("image") or ""
                group = ch.get("category_name") or f"Servidor {sid}"
                
                m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}/stream/{sid}/{ch_id}")
                total_canais += 1

    if total_canais == 0:
        m3u.append("# ERRO: O Render continua bloqueado pelo SpeedFlix.")
        m3u.append("# DICA: Tente criar este App no servico KOYEB.COM (e gratuito e os IPs nao sao bloqueados).")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv", generator_info_name="SpeedFlix")
    # Pega canais do servidor 1 para o EPG
    data = get_data("channels", {"server_id": 1, "per_page": 60})
    if data:
        items = data.get("items") or []
        for ch in items:
            ch_id = ch.get("id")
            channel_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(channel_elem, "display-name").text = ch.get("name") or ch.get("title")
    
    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    return Response(xml_data, mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream(server_id, channel_id):
    # Obtém o link de vídeo em tempo real
    data = get_data(f"channels/{channel_id}/stream", {"server_id": server_id})
    if data:
        url = data.get("stream_url")
        if url: return redirect(url)
    return "Link offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

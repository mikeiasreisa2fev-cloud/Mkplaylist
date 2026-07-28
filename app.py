import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Domínio principal que funcionou no Render
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"

# Headers oficiais para o servidor não bloquear o Render
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

def get_channels_for_server(server_id):
    """Busca canais de um servidor específico."""
    try:
        url = f"{BASE_URL}/channels"
        params = {
            "server_id": server_id,
            "per_page": 500, # Pega o máximo possível de uma vez para evitar erro 500
            "page": 1
        }
        res = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data.get("data", {}).get("items") or data.get("items") or []
    except Exception as e:
        print(f"Erro no servidor {server_id}: {e}")
    return []

@app.route("/")
def index():
    host = request.host_url.rstrip('/')
    return f"<h1>SpeedFlix Multi-Server</h1>Playlist: {host}/playlist.m3u"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        channels = get_channels_for_server(sid)
        for ch in channels:
            if not isinstance(ch, dict): continue
            ch_id = ch.get("id")
            if not ch_id: continue
            
            # Pega o nome original e adiciona o sufixo do servidor
            original_name = ch.get("name") or ch.get("title") or "Canal"
            channel_name = f"{original_name} [S{sid}]"
            
            logo = ch.get("image") or ""
            group = ch.get("category_name") or f"SERVIDOR {sid}"
            
            # Criamos um ID único combinando servidor + id do canal (ex: 1_550)
            # Isso garante que o TiviMate trate cada servidor como um canal diferente
            unique_id = f"{sid}_{ch_id}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{unique_id}" tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{group}",{channel_name}')
            # O link de stream aponta para o nosso proxy abaixo
            m3u.append(f"{host}/stream/{sid}/{ch_id}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera um EPG simplificado compatível com os novos nomes."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix")
    
    # Adicionamos apenas os canais do servidor 1 para o EPG não ficar pesado demais
    # e dar erro no Render
    channels = get_channels_for_server(1)[:100]
    for ch in channels:
        ch_id = ch.get("id")
        name = f"{ch.get('name') or ch.get('title')} [S1]"
        unique_id = f"1_{ch_id}"
        
        c_elem = ET.SubElement(tv, "channel", id=unique_id)
        ET.SubElement(c_elem, "display-name").text = name
            
    xml_data = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    return Response(xml_data, mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Obtém o link de vídeo real no momento do play."""
    try:
        url = f"{BASE_URL}/channels/{cid}/stream"
        res = requests.get(url, params={"server_id": sid}, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            data = res.json()
            stream_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if stream_url:
                return redirect(stream_url)
    except: pass
    return "Link indisponível", 404

if __name__ == "__main__":
    # O Render usa a porta 10000 por padrão ou a definida no ambiente
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

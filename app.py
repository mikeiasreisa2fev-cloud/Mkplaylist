import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Domínio principal
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"

# Headers oficiais
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

def get_channels_fast(server_id):
    """Busca canais de forma otimizada para evitar timeout no Render."""
    items_list = []
    try:
        # Tentamos buscar 500 canais de uma vez para reduzir o número de requisições
        url = f"{BASE_URL}/channels"
        params = {
            "server_id": server_id,
            "per_page": 500, 
            "page": 1
        }
        res = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            # Tenta encontrar a lista de itens em diferentes formatos que a API usa
            items = data.get("data", {}).get("items") or data.get("items")
            if items and isinstance(items, list):
                return items
    except Exception as e:
        print(f"Erro no servidor {server_id}: {e}")
    return items_list

@app.route("/")
def index():
    return "Servidor Online! Use /playlist.m3u no TiviMate."

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed_ids = set()
    
    try:
        # Percorre os servidores 1, 2 e 3
        for sid in [1, 2, 3]:
            channels = get_channels_fast(sid)
            for ch in channels:
                if not isinstance(ch, dict): continue
                ch_id = ch.get("id")
                if not ch_id or ch_id in processed_ids: continue
                
                processed_ids.add(ch_id)
                name = ch.get("name") or ch.get("title") or "Canal"
                logo = ch.get("image") or ""
                group = ch.get("category_name") or f"Servidor {sid}"
                
                m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}/stream/{sid}/{ch_id}")
    except Exception as e:
        return f"Erro ao gerar lista: {str(e)}", 500
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera um EPG simplificado para evitar erro 500 no Render."""
    tv = ET.Element("tv")
    try:
        # Busca apenas os primeiros canais do servidor 1 para o EPG ser rápido
        channels = get_channels_fast(1)[:50]
        for ch in channels:
            ch_id = ch.get("id")
            name = ch.get("name") or ch.get("title")
            c_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(c_elem, "display-name").text = name
    except:
        pass

    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Obtém o link final do vídeo."""
    try:
        url = f"{BASE_URL}/channels/{cid}/stream"
        res = requests.get(url, params={"server_id": sid}, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            v_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if v_url:
                return redirect(v_url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

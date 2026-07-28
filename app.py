import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Domínio principal
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"

# Headers oficiais para evitar bloqueios
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

def get_all_channels(server_id):
    """Busca TODOS os canais percorrendo todas as páginas do servidor."""
    all_channels = []
    page = 1
    max_pages = 20 # Limite de segurança
    
    while page <= max_pages:
        try:
            url = f"{BASE_URL}/channels"
            params = {
                "server_id": server_id,
                "per_page": 100,
                "page": page
            }
            res = requests.get(url, params=params, headers=HEADERS, timeout=15)
            
            if res.status_code != 200:
                break
                
            data = res.json()
            # Pega os itens da chave 'data' -> 'items' ou direto da raiz
            envelope = data.get("data", {})
            items = envelope.get("items") or data.get("items") or []
            
            if not items:
                break
                
            all_channels.extend(items)
            
            # Verifica se há mais páginas nos metadados
            total_pages = envelope.get("meta", {}).get("total_pages") or data.get("total_pages", 1)
            if page >= int(total_pages):
                break
                
            page += 1
            time.sleep(0.2) # Pausa rápida para não sobrecarregar
        except Exception:
            break
            
    return all_channels

@app.route("/")
def index():
    host = request.host_url.rstrip('/')
    return f"Playlist: {host}/playlist.m3u"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    
    for sid in [1, 2, 3]:
        channels = get_all_channels(sid)
        for ch in channels:
            if not isinstance(ch, dict): continue
            ch_id = ch.get("id")
            if not ch_id: continue
            
            # Adiciona o sufixo [S1], [S2] ou [S3] no nome
            name = f"{ch.get('name') or ch.get('title') or 'Canal'} [S{sid}]"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or f"SERVIDOR {sid}"
            
            # ID Único para o TiviMate não mesclar os canais
            unique_id = f"ser_{sid}_ch_{ch_id}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{unique_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{sid}/{ch_id}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Pega o link real com token de tempo para o vídeo rodar."""
    try:
        # Geramos o link de stream passando o tempo atual 't'
        # Isso é o que o App faz para validar a sessão
        timestamp = int(time.time())
        url = f"{BASE_URL}/channels/{cid}/stream"
        params = {"server_id": sid, "t": timestamp}
        
        res = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # Extrai a URL final do vídeo
            stream_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if stream_url:
                # O TiviMate seguirá este redirecionamento para o vídeo
                return redirect(stream_url)
    except Exception as e:
        print(f"Erro no stream: {e}")
        
    return "Erro ao carregar vídeo", 404

@app.route("/epg.xml")
def epg():
    """Gera um EPG básico."""
    tv = ET.Element("tv")
    # Apenas canais do servidor 1 para o EPG carregar rápido no Render
    channels = get_all_channels(1)[:100]
    for ch in channels:
        uid = f"ser_1_ch_{ch.get('id')}"
        name = f"{ch.get('name') or ch.get('title')} [S1]"
        c_elem = ET.SubElement(tv, "channel", id=uid)
        ET.SubElement(c_elem, "display-name").text = name
    
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

if __name__ == "__main__":
    # Render usa porta 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

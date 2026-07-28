import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

# Usando o novo domínio que você forneceu
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"

# Headers EXATOS do aplicativo Android oficial
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "X-Requested-With": "site.speedflix", # Identificador do App
    "Host": "ycineflix.tudo30.shop"
}

def get_channels(server_id):
    """Busca canais tentando burlar o bloqueio de IP."""
    try:
        # Aumentamos o per_page para 500 para pegar tudo de uma vez e evitar várias requisições
        url = f"{BASE_URL}/channels"
        params = {"server_id": server_id, "per_page": 500, "page": 1}
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            # Verifica se os canais estão na chave 'data' ou na raiz
            return data.get("data", {}).get("items") or data.get("items") or []
        else:
            print(f"Erro {response.status_code} no servidor {server_id}")
    except Exception as e:
        print(f"Falha na conexão: {e}")
    return []

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed_ids = set()
    
    # Tenta carregar canais dos 3 servidores
    for sid in [1, 2, 3]:
        channels = get_channels(sid)
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id or ch_id in processed_ids: continue
            processed_ids.add(ch_id)
            
            name = ch.get("name") or ch.get("title") or "Canal"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or f"Servidor {sid}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            # Link que passa por este script para pegar o vídeo real
            m3u.append(f"{host}/stream/{sid}/{ch_id}")
    
    if len(m3u) <= 1:
        m3u.append("# ERRO: Servidor bloqueou o Render. Tente abrir o link no seu 4G para testar.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera um EPG básico para os canais."""
    tv = ET.Element("tv")
    channels = get_channels(1)[:40] # Limita a 40 para não dar erro de memória no Render
    for ch in channels:
        ch_id = ch.get("id")
        ch_elem = ET.SubElement(tv, "channel", id=str(ch_id))
        ET.SubElement(ch_elem, "display-name").text = ch.get("name")
    
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Pega o link de vídeo real no momento que o TiviMate der o play."""
    try:
        url = f"{BASE_URL}/channels/{cid}/stream"
        res = requests.get(url, params={"server_id": sid}, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            video_url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
            if video_url:
                return redirect(video_url)
    except: pass
    return "Link indisponível", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

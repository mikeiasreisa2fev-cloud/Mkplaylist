import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Lista de domínios conhecidos para fallback
DOMAINS = ["https://speedflix02.com", "https://app.pobreflix2.site", "https://speedflix.top"]
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json",
    "Accept-Language": "pt-BR",
    "Connection": "Keep-Alive"
}

def get_working_base():
    """Testa qual domínio está respondendo e retorna a URL da API."""
    for d in DOMAINS:
        url = f"{d}/wp-json/xui-pflix/v1"
        try:
            # Tenta pegar o config sem token (permitido pela API)
            res = requests.get(f"{url}/app/config", headers=HEADERS, timeout=8)
            if res.status_code == 200:
                return url
        except:
            continue
    return f"{DOMAINS[0]}/wp-json/xui-pflix/v1"

BASE_URL = get_working_base()

def get_channels_from_api(server_id):
    """Tenta buscar canais simulando um acesso mobile."""
    channels = []
    try:
        # Nota: Algumas versões da API aceitam servidor como '1', '2' ou '3' 
        # mas só retornam dados se o 'per_page' for alto o suficiente
        res = requests.get(f"{BASE_URL}/channels", params={
            "server_id": server_id,
            "per_page": 500, # Tenta pegar tudo de uma vez
            "page": 1
        }, headers=HEADERS, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            # O SpeedFlix envelopa os dados em 'data' ou entrega direto
            items = data.get("data", {}).get("items") or data.get("items") or []
            return items
    except Exception as e:
        print(f"Erro na API: {e}")
    return []

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed = set()
    
    # Itera pelos servidores solicitados
    for sid in [1, 2, 3]:
        canals = get_channels_from_api(sid)
        for c in canals:
            ch_id = c.get("id")
            if not ch_id or ch_id in processed: continue
            processed.add(ch_id)
            
            name = c.get("name") or c.get("title") or f"Canal {ch_id}"
            logo = c.get("image") or ""
            group = c.get("category_name") or f"Servidor {sid}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{sid}/{ch_id}")
            
    if len(m3u) <= 1:
        # Se falhou, gera uma lista de teste para você ver se o Render está bloqueado
        m3u.append("# INFO: O servidor nao retornou canais. Pode ser bloqueio de IP do Render.")
        m3u.append(f"# URL TESTADA: {BASE_URL}")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv")
    # Pega apenas alguns canais para o EPG carregar rápido
    canals = get_channels_from_api(1)[:30]
    for c in canals:
        ch_id = c.get("id")
        ch_elem = ET.SubElement(tv, "channel", id=str(ch_id))
        ET.SubElement(ch_elem, "display-name").text = c.get("name") or c.get("title")
    
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:server_id>/<int:channel_id>")
def stream(server_id, channel_id):
    try:
        # No momento do clique, pegamos a URL real
        res = requests.get(f"{BASE_URL}/channels/{channel_id}/stream", 
                          params={"server_id": server_id}, headers=HEADERS, timeout=10)
        url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
        if url: return redirect(url)
    except: pass
    return "Nao disponível", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

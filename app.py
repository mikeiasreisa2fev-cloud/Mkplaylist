import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import random

app = Flask(__name__)

# Domínios oficiais
BASE_SITE = "https://app.pobreflix2.site"

def get_headers():
    # Gera um IP falso do Brasil para tentar passar pelo firewall
    fake_ip = f"189.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        "X-Forwarded-For": fake_ip,
        "X-Real-IP": fake_ip,
        "Accept": "application/json",
        "Connection": "keep-alive"
    }

def get_api_data(endpoint, params=None):
    """Usa o rest_route para tentar burlar o bloqueio de IP do Render."""
    url = f"{BASE_SITE}/"
    # Transforma o endpoint em rest_route (Ex: channels -> /xui-pflix/v1/channels)
    query_params = {"rest_route": f"/xui-pflix/v1/{endpoint}"}
    if params:
        query_params.update(params)
    
    try:
        # Usamos HTTPX que gerencia melhor os certificados que o Requests
        with httpx.Client(headers=get_headers(), follow_redirects=True, timeout=15.0) as client:
            res = client.get(url, params=query_params)
            if res.status_code == 200:
                data = res.json()
                return data.get("data") or data
    except Exception as e:
        print(f"Erro na conexão: {e}")
    return None

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed = set()
    
    # Servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        data = get_api_data("channels", {"server_id": sid, "per_page": 200})
        if data:
            items = data if isinstance(data, list) else data.get("items", [])
            for ch in items:
                ch_id = ch.get("id")
                if not ch_id or ch_id in processed: continue
                processed.add(ch_id)
                
                name = ch.get("name") or ch.get("title") or "Canal"
                logo = ch.get("image") or ""
                group = ch.get("category_name") or f"Servidor {sid}"
                
                m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}')
                m3u.append(f"{host}/stream/{sid}/{ch_id}")
    
    if len(m3u) <= 1:
        m3u.append("# ERRO: O Render continua bloqueado.")
        m3u.append("# A UNICA FORMA NO RENDER E USANDO UM PROXY OU MUDANDO PARA O KOYEB.COM")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    tv = ET.Element("tv")
    data = get_api_data("channels", {"server_id": 1, "per_page": 50})
    if data:
        items = data if isinstance(data, list) else data.get("items", [])
        for ch in items:
            ch_id = ch.get("id")
            ch_elem = ET.SubElement(tv, "channel", id=str(ch_id))
            ET.SubElement(ch_elem, "display-name").text = ch.get("name") or ch.get("title")
            
    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    data = get_api_data(f"channels/{cid}/stream", {"server_id": sid})
    if data and isinstance(data, dict):
        url = data.get("stream_url")
        if url: return redirect(url)
    return "Offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

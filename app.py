import requests
import re
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Links que você forneceu
BASE_URL = "https://app.pobreflix2.site"
SERVER_LINKS = {
    1: "https://app.pobreflix2.site/canais/?thema=1&server=speed-1",
    2: "https://app.pobreflix2.site/canais/?thema=1&server=speed-2",
    3: "https://app.pobreflix2.site/canais/?thema=1&server=speed-3"
}

# Headers de navegador real para não ser bloqueado
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": "https://app.pobreflix2.site/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

def get_channels_from_web(sid):
    """Extrai os canais lendo o HTML da pagina (Bypass de bloqueio de API)."""
    channels = []
    try:
        url = SERVER_LINKS.get(sid)
        res = requests.get(url, headers=HEADERS_WEB, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Busca links de canais: href contem '/canais/ID/'
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/canais/' in href:
                    # Extrai o ID do link
                    parts = href.strip('/').split('/')
                    if parts[-1].isdigit():
                        cid = parts[-1]
                        # Pega o nome do canal (esta no title ou no texto)
                        name = link.get('title') or link.text.strip()
                        if not name: continue
                        
                        # Tenta pegar a logo
                        img = link.find('img')
                        logo = img['src'] if img and img.has_attr('src') else ""
                        
                        channels.append({
                            "id": cid,
                            "name": name.replace("Assistir ", ""),
                            "logo": logo
                        })
    except: pass
    
    # Remove duplicados
    seen = set()
    unique = []
    for c in channels:
        if c['id'] not in seen:
            unique.append(c)
            seen.add(c['id'])
    return unique

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Scraper Ativo</h1><p>M3U: {h}playlist.m3u<br>EPG: {h}epg.xml</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    total = 0
    
    for sid in [1, 2, 3]:
        channels = get_channels_from_web(sid)
        for ch in channels:
            cid = ch['id']
            name = f"{ch['name']} [S{sid}]"
            group = f"CANAIS [S{sid}]"
            logo = ch['logo']
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}")
            total += 1
            
    if total == 0:
        m3u.append("# ERRO: Nao foi possivel ler os canais do site.")
        m3u.append("# Verifique se o site app.pobreflix2.site esta online.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Busca o link do video via API de Stream."""
    try:
        # O link do video ainda precisa da API
        url = f"https://app.pobreflix2.site/wp-json/xui-pflix/v1/channels/{cid}/stream"
        h = {"User-Agent": "okhttp/4.12.0", "X-Requested-With": "site.speedflix"}
        r = requests.get(url, params={"server_id": sid, "t": int(time.time())}, headers=h, timeout=10)
        if r.status_code == 200:
            data = r.json()
            video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if video_url: return redirect(video_url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    # EPG via Scraper e muito lento, retorna vazio por enquanto
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

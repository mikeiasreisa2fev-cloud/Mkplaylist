import requests
import re
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Configurações
BASE_URL = "https://app.pobreflix2.site"
API_PATH = "/wp-json/xui-pflix/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://app.pobreflix2.site/",
    "Connection": "keep-alive"
}

def get_channels_from_web(server_id):
    """Lê a página web de cada servidor e extrai os canais via código HTML."""
    channels = []
    # URL que você me passou para todos os canais de cada servidor
    url = f"{BASE_URL}/canais/?thema=1&server=speed-{server_id}"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            html = res.text
            # Regex para capturar ID, Nome e Imagem dos canais no código do Pobreflix
            # O padrão costuma ser: href=".../canais/ID/" e title="NOME"
            matches = re.findall(r'href="https://app.pobreflix2.site/canais/(\d+)/".*?title="(.*?)"', html)
            
            for cid, name in matches:
                # Tenta achar a imagem (logo) logo após o link
                img_match = re.search(fr'href="https://app.pobreflix2.site/canais/{cid}/".*?src="(.*?)"', html)
                logo = img_match.group(1) if img_match else ""
                
                channels.append({
                    "id": cid,
                    "name": name,
                    "logo": logo,
                    "group": f"CANAIS [S{server_id}]"
                })
    except Exception as e:
        print(f"Erro no Servidor {server_id}: {e}")
    
    return channels

@app.route("/")
def index():
    return f"<h1>SpeedFlix Web Proxy</h1><p>Playlist: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Headers para o TiviMate enviar ao dar Play
    suffix = f"|User-Agent={HEADERS['User-Agent']}&Referer={BASE_URL}/"

    for sid in [1, 2, 3]:
        channels = get_channels_from_web(sid)
        for ch in channels:
            cid = ch['id']
            name = f"{ch['name']} [S{sid}]"
            group = ch['group']
            logo = ch['logo']
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
            
    if len(m3u) == 1:
        m3u.append("# ERRO: O Render nao conseguiu ler o site. Pode ser bloqueio de IP.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<cid>")
def stream_proxy(sid, cid):
    # Limpa o ID se o TiviMate mandar sufixos
    clean_cid = cid.split('|')[0]
    try:
        # Pega o link real de vídeo via API (o site também usa esse endpoint internamente)
        url = f"{BASE_URL}{API_PATH}/channels/{clean_cid}/stream"
        res = requests.get(url, params={"server_id": sid, "t": int(time.time())}, headers=HEADERS, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if video_url:
                return redirect(video_url)
    except: pass
    return "Offline", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

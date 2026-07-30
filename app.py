import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Configurações extraídas do seu código-fonte
BASE_SITE = "https://app.pobreflix2.site"
STREAM_DOMAIN = "https://speed.megafilmeshd9.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": BASE_SITE + "/"
}

def get_channels_from_server(sid):
    """Varre o site e extrai todos os canais do servidor especificado."""
    channels = []
    # URL da página com a lista de todos os canais do servidor
    url = f"{BASE_SITE}/canais/?thema=1&server=speed-{sid}"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Busca todos os cards de canais
            cards = soup.find_all('a', class_='iptv-card')
            
            for card in cards:
                href = card.get('href', '')
                # Extrai o ID do link (ex: .../canais/11892477/ -> 11892477)
                cid_match = [s for s in href.split('/') if s.isdigit()]
                if not cid_match: continue
                cid = cid_match[0]
                
                # Pega o nome do canal
                title_elem = card.find('span', class_='iptv-card-title')
                name = title_elem.text.strip() if title_elem else f"Canal {cid}"
                
                # Pega a logo
                img_elem = card.find('img')
                logo = img_elem.get('src', '') if img_elem else ""
                
                channels.append({
                    "id": cid,
                    "name": name,
                    "logo": logo,
                    "server": sid
                })
    except Exception as e:
        print(f"Erro no scraping S{sid}: {e}")
    
    return channels

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Master Proxy</h1><p>M3U: {h}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Headers para o TiviMate enviar ao servidor de vídeo
    # O Pobreflix exige o Referer correto para o vídeo não travar
    suffix = f"|User-Agent={HEADERS['User-Agent']}&Referer={BASE_SITE}/"

    for sid in [1, 2, 3]:
        channels = get_channels_from_server(sid)
        for ch in channels:
            name = f"{ch['name']} [S{sid}]"
            group = f"CANAIS [S{sid}]"
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch["id"]}" tvg-logo="{ch["logo"]}" group-title="{group}",{name}')
            
            # Geramos o link direto do servidor de vídeo que descobri no seu código
            # Formato: https://speed.megafilmeshd9.com/midia/speed-X/ID.m3u8
            direct_stream = f"{STREAM_DOMAIN}/midia/speed-{sid}/{ch['id']}.m3u8"
            m3u.append(f"{direct_stream}{suffix}")
            
    if len(m3u) == 1:
        m3u.append("# ERRO: IP do Servidor Bloqueado. Tente abrir no celular primeiro.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    # Retorna XML vazio
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

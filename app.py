import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import time

app = Flask(__name__)

# Os links que você passou
BASE_URL = "https://app.pobreflix2.site"
SERVER_LINKS = {
    1: "https://app.pobreflix2.site/canais/?thema=1&server=speed-1",
    2: "https://app.pobreflix2.site/canais/?thema=1&server=speed-2",
    3: "https://app.pobreflix2.site/canais/?thema=1&server=speed-3"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://app.pobreflix2.site/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

def get_channels_from_html(sid):
    """Lê a página web e extrai os canais manualmente."""
    channels = []
    try:
        url = SERVER_LINKS.get(sid)
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Busca todos os links que apontam para um canal
            # Geralmente são do tipo: https://app.pobreflix2.site/canais/ID/
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '/canais/' in href and href.strip('/').split('/')[-1].isdigit():
                    cid = href.strip('/').split('/')[-1]
                    # Tenta pegar o nome dentro da tag title ou de um span/h2
                    name = link.get('title') or link.text.strip() or f"Canal {cid}"
                    
                    # Tenta pegar a imagem
                    img = link.find('img')
                    logo = img['src'] if img and img.has_attr('src') else ""
                    
                    channels.append({
                        "id": cid,
                        "name": name.replace("Assistir ", ""),
                        "logo": logo,
                        "group": f"SERVIDOR {sid}"
                    })
    except Exception as e:
        print(f"Erro no scraping do servidor {sid}: {e}")
    
    # Remove duplicados mantendo a ordem
    seen = set()
    unique_channels = []
    for c in channels:
        if c['id'] not in seen:
            unique_channels.append(c)
            seen.add(c['id'])
            
    return unique_channels

@app.route("/")
def index():
    return "<h1>SpeedFlix Web Scanner Ativo</h1><p>Playlist: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    for sid in [1, 2, 3]:
        channels = get_channels_from_html(sid)
        for ch in channels:
            name = f"{ch['name']} [S{sid}]"
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch["id"]}" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{name}')
            m3u.append(f"{host}stream/{sid}/{ch['id']}")
            
    if len(m3u) == 1:
        return "#EXTM3U\n# ERRO: O site nao permitiu a leitura do codigo (Block).\n# Tente hospedar no Railway.app."

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<cid>")
def stream(sid, cid):
    """Tenta obter o link de vídeo final via API."""
    try:
        # Aqui ainda tentamos a API, pois o link de vídeo só sai por ela
        api_url = f"https://app.pobreflix2.site/wp-json/xui-pflix/v1/channels/{cid}/stream"
        # Para o vídeo, usamos o User-Agent de celular que é mais aceito
        headers = {"User-Agent": "okhttp/4.12.0", "X-Requested-With": "site.speedflix"}
        res = requests.get(api_url, params={"server_id": sid, "t": int(time.time())}, headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if video_url:
                return redirect(video_url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

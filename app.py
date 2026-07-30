import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request
import os
import time

app = Flask(__name__)

# Links das paginas que voce passou (Modo Web)
SERVER_PAGES = {
    1: "https://app.pobreflix2.site/canais/?thema=1&server=speed-1",
    2: "https://app.pobreflix2.site/canais/?thema=1&server=speed-2",
    3: "https://app.pobreflix2.site/canais/?thema=1&server=speed-3"
}

# Domínio direto do servidor de vídeo (descoberto no seu código-fonte)
VIDEO_BASE = "https://speed.megafilmeshd9.com/midia"

# Headers de navegador real para o site nao desconfiar
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://app.pobreflix2.site/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

def scrape_channels(sid):
    """Entra no site, lê o HTML e extrai os canais um por um."""
    channels = []
    url = SERVER_PAGES.get(sid)
    try:
        # Aumentamos o tempo de espera (timeout) pois o site e pesado
        res = requests.get(url, headers=HEADERS, timeout=25)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Busca todos os blocos de canais (classe iptv-card que vimos no seu codigo)
            cards = soup.find_all('a', class_='iptv-card')
            
            for card in cards:
                href = card.get('href', '')
                # Extrai o ID do link (ex: .../canais/11892477/ -> 11892477)
                cid = "".join(filter(str.isdigit, href.split('/')[-2]))
                
                if cid:
                    # Pega o nome e a logo
                    name_elem = card.find('span', class_='iptv-card-title')
                    name = name_elem.text.strip() if name_elem else f"Canal {cid}"
                    
                    img_elem = card.find('img')
                    logo = img_elem.get('src', '') if img_elem else ""
                    
                    channels.append({
                        "id": cid,
                        "name": name,
                        "logo": logo,
                        "group": f"CANAIS [S{sid}]"
                    })
    except Exception as e:
        print(f"Erro no servidor {sid}: {e}")
    
    return channels

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Master Proxy Ativo</h1><p>Playlist: {h}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    total = 0
    
    # Sufixo para o TiviMate abrir o video sem travar
    suffix = "|User-Agent=Mozilla/5.0&Referer=https://app.pobreflix2.site/"

    for sid in [1, 2, 3]:
        canals = scrape_channels(sid)
        for ch in canals:
            # Nome com sufixo [S1], [S2] ou [S3]
            display_name = f"{ch['name']} [S{sid}]"
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch["id"]}" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{display_name}')
            # LINK DIRETO (O pulo do gato): Nao passa pelo seu servidor, abre direto da fonte!
            m3u.append(f"{VIDEO_BASE}/speed-{sid}/{ch['id']}.m3u8{suffix}")
            total += 1
            
    if total == 0:
        m3u.append("# ERRO: O site bloqueou a leitura visual (Scraping).")
        m3u.append("# Verifique se voce consegue abrir o site https://app.pobreflix2.site no seu PC.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

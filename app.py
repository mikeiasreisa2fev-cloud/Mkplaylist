import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
from datetime import datetime

app = Flask(__name__)

# Links das paginas que voce enviou
SERVER_PAGES = {
    1: "https://app.pobreflix2.site/canais/?thema=1&server=speed-1",
    2: "https://app.pobreflix2.site/canais/?thema=1&server=speed-2",
    3: "https://app.pobreflix2.site/canais/?thema=1&server=speed-3"
}

# Headers de um navegador real para evitar o erro 403
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": "https://app.pobreflix2.site/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

def scrape_channels(sid):
    """Entra no site e 'caça' os IDs e Nomes dos canais no código HTML."""
    channels = []
    try:
        url = SERVER_PAGES.get(sid)
        res = requests.get(url, headers=HEADERS_WEB, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # No site do Pobreflix, os canais estao em links dentro de divs da classe 'item'
            # Buscamos o padrao de link: /canais/ID/
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/canais/' in href:
                    cid = href.strip('/').split('/')[-1]
                    if cid.isdigit():
                        name = a.get('title') or a.text.strip()
                        if not name: continue
                        
                        # Tenta pegar a imagem do canal
                        img = a.find('img')
                        logo = img['src'] if img and img.has_attr('src') else ""
                        
                        channels.append({
                            "id": cid,
                            "name": name.replace("Assistir ", ""),
                            "logo": logo,
                            "group": f"CANAIS [S{sid}]"
                        })
    except Exception as e:
        print(f"Erro no servidor {sid}: {e}")
    
    # Remove duplicados
    seen = set()
    return [c for c in channels if not (c['id'] in seen or seen.add(c['id']))]

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>SpeedFlix Master Proxy</h1><p>Playlist: {h}playlist.m3u</p><p>EPG: {h}epg.xml</p>"

@app.route("/playlist.m3u")
def playlist():
    m3u = ["#EXTM3U"]
    host = request.host_url
    total = 0
    
    for sid in [1, 2, 3]:
        canals = scrape_channels(sid)
        for ch in canals:
            name = f"{ch['name']} [S{sid}]"
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch["id"]}" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{name}')
            # Link de redirecionamento para o video
            m3u.append(f"{host}stream/{sid}/{ch['id']}")
            total += 1
            
    if total == 0:
        m3u.append("# ERRO: O site bloqueou o acesso do servidor (403).")
        m3u.append("# Tente abrir o link da playlist no seu 4G para testar.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Busca o link real do m3u8 na hora de dar o play."""
    try:
        # A API de stream costuma ser mais aberta que a de lista
        api_url = f"https://app.pobreflix2.site/wp-json/xui-pflix/v1/channels/{cid}/stream"
        h = {"User-Agent": "okhttp/4.12.0", "X-Requested-With": "site.speedflix"}
        r = requests.get(api_url, params={"server_id": sid, "t": int(time.time())}, headers=h, timeout=10)
        if r.status_code == 200:
            url = r.json().get("data", {}).get("stream_url") or r.json().get("stream_url")
            if url: return redirect(url)
    except: pass
    return "Link Offline", 404

@app.route("/epg.xml")
def epg():
    """Extrai o guia de programacao dos canais do servidor 1."""
    tv = ET.Element("tv")
    channels = scrape_channels(1)[:40] # Limite para nao travar o Railway
    for ch in channels:
        cid = ch['id']
        c_elem = ET.SubElement(tv, "channel", id=f"s1_{cid}")
        ET.SubElement(c_elem, "display-name").text = f"{ch['name']} [S1]"
        
        # Busca EPG real via API
        try:
            e_url = f"https://app.pobreflix2.site/wp-json/xui-pflix/v1/channels/{cid}/epg"
            e_res = requests.get(e_url, params={"server_id": 1, "limit": 5}, headers={"User-Agent": "okhttp/4.12.0"}, timeout=5)
            if e_res.status_code == 200:
                listings = e_res.json().get("data", {}).get("epg", {}).get("epg_listings", [])
                for p in listings:
                    start = datetime.fromtimestamp(int(p['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                    stop = datetime.fromtimestamp(int(p['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                    prog = ET.SubElement(tv, "programme", start=start, stop=stop, channel=f"s1_{cid}")
                    ET.SubElement(prog, "title", lang="pt").text = p.get("title")
        except: continue

    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

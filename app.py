import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response, redirect, request
import os
import time

app = Flask(__name__)

# Domínio principal
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"

# Headers oficiais para o servidor liberar todos os dados
HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "X-Requested-With": "site.speedflix",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

def get_all_channels(server_id):
    """Busca TODOS os canais de um servidor, percorrendo todas as páginas."""
    all_items = []
    page = 1
    
    while True:
        try:
            print(f"Buscando Servidor {server_id} - Página {page}...")
            url = f"{BASE_URL}/channels"
            params = {
                "server_id": server_id,
                "per_page": 100, # Recomendado 100 por vez para não ser bloqueado
                "page": page
            }
            
            response = requests.get(url, params=params, headers=HEADERS, timeout=20)
            
            if response.status_code != 200:
                break
                
            data = response.json()
            # O SpeedFlix coloca os canais em data['items'] ou direto em data['items']
            envelope = data.get("data", {})
            items = envelope.get("items") or data.get("items") or []
            
            if not items:
                break
                
            all_items.extend(items)
            
            # Verifica se chegamos na última página
            meta = envelope.get("meta", {})
            total_pages = meta.get("total_pages") or data.get("total_pages", 1)
            
            if page >= int(total_pages):
                break
                
            page += 1
            time.sleep(0.5) # Pequena pausa para o servidor não nos banir
            
        except Exception as e:
            print(f"Erro na página {page}: {e}")
            break
            
    return all_items

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')
    m3u = ["#EXTM3U"]
    processed_ids = set()
    
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        channels = get_all_channels(sid)
        print(f"Servidor {sid}: Encontrados {len(channels)} canais.")
        
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id or ch_id in processed_ids: 
                continue
                
            processed_ids.add(ch_id)
            name = ch.get("name") or ch.get("title") or "Canal"
            logo = ch.get("image") or ""
            group = ch.get("category_name") or f"Servidor {sid}"
            
            m3u.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}/stream/{sid}/{ch_id}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera o EPG. Nota: Buscar EPG de muitos canais pode ser lento no Render."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix")
    
    # Pegamos apenas os canais do servidor 1 para o EPG carregar em tempo aceitável
    channels = get_all_channels(1)[:100] 
    
    for ch in channels:
        ch_id = ch.get("id")
        name = ch.get("name") or ch.get("title")
        
        c_elem = ET.SubElement(tv, "channel", id=str(ch_id))
        ET.SubElement(c_elem, "display-name").text = name
        
        # Busca a programação real desse canal
        try:
            url_epg = f"{BASE_URL}/channels/{ch_id}/epg"
            res_epg = requests.get(url_epg, params={"server_id": 1, "limit": 10}, headers=HEADERS, timeout=5)
            if res_epg.status_code == 200:
                listings = res_epg.json().get("data", {}).get("epg", {}).get("epg_listings", [])
                for prog in listings:
                    start = datetime.fromtimestamp(int(prog['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                    stop = datetime.fromtimestamp(int(prog['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                    p_elem = ET.SubElement(tv, "programme", start=start, stop=stop, channel=str(ch_id))
                    ET.SubElement(p_elem, "title", lang="pt").text = prog.get("title")
        except:
            continue

    return Response(ET.tostring(tv, encoding="utf-8"), mimetype="application/xml")

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    """Proxy para pegar o link de vídeo real."""
    try:
        url = f"{BASE_URL}/channels/{cid}/stream"
        res = requests.get(url, params={"server_id": sid}, headers=HEADERS, timeout=10)
        video_url = res.json().get("data", {}).get("stream_url") or res.json().get("stream_url")
        if video_url:
            return redirect(video_url)
    except: pass
    return "Offline", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

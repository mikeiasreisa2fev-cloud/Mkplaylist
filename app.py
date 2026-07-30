import requests
import json
import xml.etree.ElementTree as ET
from flask import Flask, Response, request
import os
import time
from datetime import datetime

app = Flask(__name__)

# Configurações do SpeedFlix / Pobreflix
BASE_API = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"
# Proxy para contornar bloqueio de IP de servidores de nuvem (Railway/Render)
PROXY_SERVICE = "https://api.allorigins.win/get?url="

def fetch_via_proxy(url):
    """Busca dados usando um serviço de proxy para esconder o IP do servidor."""
    try:
        # AllOrigins é um proxy público que retorna o conteúdo em 'contents'
        full_url = f"{PROXY_SERVICE}{requests.utils.quote(url)}"
        r = requests.get(full_url, timeout=20)
        if r.status_code == 200:
            content = r.json().get("contents")
            return json.loads(content)
    except Exception as e:
        print(f"Erro no Proxy: {e}")
    return None

@app.route("/")
def index():
    h = request.host_url
    return f"""
    <h1>SpeedFlix Master Proxy (Railway)</h1>
    <p>Adicione estes links no seu TiviMate:</p>
    <ul>
        <li><b>Playlist (M3U):</b> <code>{h}playlist.m3u</code></li>
        <li><b>EPG (XML):</b> <code>{h}epg.xml</code></li>
    </ul>
    """

@app.route("/playlist.m3u")
def playlist():
    """Gera a lista de canais unificada dos servidores 1, 2 e 3."""
    m3u = ["#EXTM3U"]
    
    # Cabeçalhos necessários para que o servidor original aceite a conexão do vídeo
    suffix = "|User-Agent=okhttp/4.12.0&Referer=https://app.pobreflix2.site/"

    total = 0
    # Percorre os servidores 1, 2 e 3 conforme solicitado
    for sid in [1, 2, 3]:
        # Tenta capturar até 500 canais por servidor em uma única chamada
        api_url = f"{BASE_API}/channels?server_id={sid}&per_page=500"
        data = fetch_via_proxy(api_url)
        
        if data:
            # A API pode retornar os itens em 'data.items' ou 'items'
            items = data.get("data", {}).get("items") or data.get("items") or []
            for ch in items:
                cid = ch.get("id")
                if not cid: continue
                
                # Nome do canal e Grupo identificados pelo servidor (ex: [S1])
                name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                cat = (ch.get('category_name') or 'Canais').upper()
                logo = ch.get("image") or ""
                
                m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                # Link direto do servidor de vídeo original (Bypass de Proxy)
                m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8{suffix}")
                total += 1

    if total == 0:
        m3u.append("# ERRO: Nenhum canal encontrado. O servidor pode ter bloqueado o Proxy.")
        
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/epg.xml")
def epg():
    """Gera o EPG (Guia de Programação) para os canais."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix-EPG")
    
    # Processa apenas os primeiros canais do servidor 1 e 2 para não dar timeout no Railway
    for sid in [1, 2]:
        api_url = f"{BASE_API}/channels?server_id={sid}&per_page=30"
        data = fetch_via_proxy(api_url)
        if data:
            items = data.get("data", {}).get("items") or data.get("items") or []
            for ch in items:
                cid = ch.get("id")
                uid = f"s{sid}_{cid}"
                
                # Entrada do canal no XML
                c_elem = ET.SubElement(tv, "channel", id=uid)
                ET.SubElement(c_elem, "display-name").text = f"{ch.get('name')} [S{sid}]"
                
                # Busca a programação (EPG) deste canal específico
                epg_url = f"{BASE_API}/channels/{cid}/epg?server_id={sid}&limit=5"
                e_data = fetch_via_proxy(epg_url)
                if e_data:
                    listings = e_data.get("data", {}).get("epg", {}).get("epg_listings", []) or []
                    for p in listings:
                        try:
                            # Converte timestamps para o formato padrão do TiviMate
                            start = datetime.fromtimestamp(int(p['start_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                            stop = datetime.fromtimestamp(int(p['stop_timestamp'])).strftime("%Y%m%d%H%M%S +0000")
                            
                            prog = ET.SubElement(tv, "programme", start=start, stop=stop, channel=uid)
                            ET.SubElement(prog, "title", lang="pt").text = p.get("title")
                            if p.get("description"):
                                ET.SubElement(prog, "desc", lang="pt").text = p.get("description")
                        except: continue
                    
    return Response(ET.tostring(tv, encoding="utf-8", xml_declaration=True), mimetype="application/xml")

if __name__ == "__main__":
    # O Railway usa a porta 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

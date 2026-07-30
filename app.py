import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Portal (Domínio que agrupa os servidores)
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Faz o login de convidado para obter o Bearer Token necessário."""
        if self.token: return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Content-Type": "application/json"}
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_headers(self):
        """Gera os cabeçalhos de autenticação."""
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Accept": "application/json"}
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

api = SpeedFlixAPI()

def fetch_channels_list(sid):
    """Busca a lista de canais de um servidor específico com paginação."""
    all_channels = []
    # Busca até 5 páginas por servidor para garantir que pegamos todos (aprox 500 canais)
    for page in range(1, 6):
        try:
            r = requests.get(f"{BASE_URL}/channels", 
                            params={"server_id": sid, "per_page": 100, "page": page},
                            headers=api.get_headers(), timeout=15)
            if r.status_code != 200: break
            data = r.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            if not items: break
            all_channels.extend(items)
            
            meta = data.get("data", {}).get("meta") or data.get("meta") or {}
            if page >= int(meta.get("total_pages", 1)): break
        except: break
    return all_channels

@app.route("/")
def index():
    h = request.host_url
    return f"<h1>Proxy SpeedFlix Ativo</h1><p>M3U: <b>{h}playlist.m3u</b></p><p>EPG: <b>{h}epg.xml</b></p>"

@app.route("/playlist.m3u")
def playlist():
    """Gera a playlist M3U unificando os servidores 1, 2 e 3."""
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Headers que o TiviMate deve usar para conseguir reproduzir o vídeo
    token = api.login()
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    if token: suffix += f"&Authorization=Bearer {token}"

    for sid in [1, 2, 3]:
        channels = fetch_channels_list(sid)
        for ch in channels:
            cid = ch.get("id")
            if not cid: continue
            
            # Nome e Categoria com identificação do Servidor
            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
            cat = (ch.get('category_name') or 'Canais').upper()
            group = f"{cat} [S{sid}]"
            logo = ch.get("image") or ""
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
            
    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    """Redireciona para o link de vídeo real gerado na hora."""
    clean_id = cid.split('|')[0].split('?')[0]
    try:
        r = requests.get(f"{BASE_URL}/channels/{clean_id}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=api.get_headers(), timeout=10)
        if r.status_code == 200:
            data = r.json()
            url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if url: return redirect(url)
    except: pass
    return "Erro", 404

@app.route("/epg.xml")
def epg():
    """Gera um arquivo EPG básico compatível com os canais."""
    tv = ET.Element("tv", generator_info_name="SpeedFlix Proxy")
    # Busca canais do servidor 1 para preencher o guia
    channels = fetch_channels_list(1)[:50]
    for ch in channels:
        cid = ch.get("id")
        c_elem = ET.SubElement(tv, "channel", id=f"s1_{cid}")
        ET.SubElement(c_elem, "display-name").text = f"{ch.get('name')} [S1]"
        
    return Response(ET.tostring(tv, encoding="utf-8", xml_declaration=True), mimetype="application/xml")

if __name__ == "__main__":
    # O Railway usa a porta da variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

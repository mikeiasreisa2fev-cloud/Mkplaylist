import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# ---------------- CONFIGURAÇÕES ----------------
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"
# ------------------------------------------------

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Obtém token de acesso Bearer"""
        if self.token:
            return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            headers = {
                "User-Agent": USER_AGENT,
                "X-Requested-With": APP_ID,
                "Content-Type": "application/json"
            }
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, 
                             headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                # Suporta ambos os formatos de resposta comum na API
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except Exception as e:
            print(f"Erro login: {e}")
        return None

    def get_headers(self):
        """Retorna cabeçalhos com autenticação"""
        headers = {
            "User-Agent": USER_AGENT, 
            "X-Requested-With": APP_ID,
            "Accept": "application/json"
        }
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

api = SpeedFlixAPI()

@app.route("/")
def index():
    return """
    <h1>Proxy SpeedFlix / YCineFlix Ativo ✅</h1>
    <p>Link da Playlist: <a href="/playlist.m3u">/playlist.m3u</a></p>
    <p>EPG: <a href="/epg.xml">/epg.xml</a></p>
    """

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Cabeçalhos para enviar ao player
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    token = api.login()
    if token:
        suffix += f"&Authorization=Bearer {token}"

    total_canais = 0
    # Servidores 1, 2 e 3 como solicitado
    for sid in [1, 2, 3]:
        page = 1
        while page <= 15:
            try:
                headers = api.get_headers()
                r = requests.get(f"{BASE_URL}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=headers, timeout=20)
                
                if r.status_code != 200:
                    break
                
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items:
                    break
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    name = f"{ch.get('name') or ch.get('title', 'Canal sem nome')} [S{sid}]"
                    cat = ch.get('category_name') or 'Canais Gerais'
                    group = f"{cat.upper()} [S{sid}]"
                    logo = ch.get("image") or ch.get("logo", "")
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                    total_canais += 1
                
                # Paginação
                meta = data.get("data", {}).get("meta") or data.get("meta", {})
                total_pages = int(meta.get("total_pages", 1))
                if page >= total_pages:
                    break
                page += 1
            except Exception as e:
                print(f"Erro carregar página {page} servidor {sid}: {e}")
                break

    if total_canais == 0:
        m3u.append("# ERRO: Nenhum canal retornado. Verifique autenticação ou domínio.")

    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    # Limpa parâmetros extras que podem vir do player
    clean_cid = cid.split('|')[0].split('?')[0]
    
    try:
        headers = api.get_headers()
        # Requisição para obter URL do stream
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            res_data = data.get("data", {})
            video_url = res_data.get("stream_url") or res_data.get("free_url") or \
                        data.get("stream_url") or data.get("free_url")
            
            if video_url:
                return redirect(video_url)
        
        return f"Erro ao obter stream (Status {r.status_code})", 404
    except Exception as e:
        return f"Erro de Conexão: {str(e)}", 500

@app.route("/epg.xml")
def epg():
    # EPG básico válido para players
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="YCineFlix Proxy"></tv>', 
        mimetype="application/xml"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

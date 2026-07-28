import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# Configurações do Servidor
# Usando o domínio fornecido pelo usuário que contém os servidores 1, 2 e 3
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """Obtém o token de acesso Bearer simulando o app original."""
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
            # Tenta realizar o login para obter o token de autorização
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, 
                             headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                res_data = data.get("data", {})
                self.token = res_data.get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_headers(self):
        """Monta os cabeçalhos necessários para as requisições da API."""
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
    return "<h1>Proxy SpeedFlix Ativo</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U"]
    
    # Sufixo para o TiviMate enviar os cabeçalhos corretos ao player final
    # Isso é essencial para que o servidor de vídeo aceite a conexão
    suffix = f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
    token = api.login()
    if token:
        suffix += f"&Authorization=Bearer {token}"

    total_canais = 0
    # Percorre os servidores 1, 2 e 3 conforme solicitado
    for sid in [1, 2, 3]:
        page = 1
        while page <= 15: # Loop para capturar todos os canais (paginação)
            try:
                headers = api.get_headers()
                r = requests.get(f"{BASE_URL}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=headers, timeout=20)
                
                if r.status_code != 200:
                    break
                
                data = r.json()
                # Extrai os canais da resposta JSON
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items:
                    break
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    # Nome do canal e grupo com identificação do servidor
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = ch.get('category_name') or 'Canais'
                    group = f"{cat.upper()} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    # O link do stream aponta para a rota interna que resolve a URL real
                    m3u.append(f"{host}stream/{sid}/{cid}{suffix}")
                    total_canais += 1
                
                # Verifica se há mais páginas
                meta = data.get("data", {}).get("meta") or data.get("meta") or {}
                total_pages = int(meta.get("total_pages", 1))
                if page >= total_pages:
                    break
                page += 1
            except:
                break

    # Se a lista vier vazia, adiciona um comentário de erro para debug
    if total_canais == 0:
        m3u.append("# ERRO: Nenhum canal encontrado. Verifique a conexao com o servidor.")

    return Response("\n".join(m3u), mimetype="text/plain")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    # O TiviMate envia os cabeçalhos colados no ID; aqui limpamos para pegar apenas o ID real
    clean_cid = cid.split('|')[0].split('?')[0]
    
    try:
        headers = api.get_headers()
        # O parâmetro 't' é um timestamp obrigatório para validar o acesso ao stream
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            res_data = data.get("data", {})
            # Extrai a URL final do vídeo (HLS/m3u8)
            video_url = res_data.get("stream_url") or res_data.get("free_url") or \
                        data.get("stream_url") or data.get("free_url")
            
            if video_url:
                # Redireciona o TiviMate para a URL real do vídeo
                return redirect(video_url)
        
        return f"Erro ao obter stream (Status {r.status_code})", 404
    except Exception as e:
        return f"Erro de Conexão: {str(e)}", 500

@app.route("/epg.xml")
def epg():
    # Retorna um arquivo XML vazio mas válido para o TiviMate
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="SpeedFlix Proxy"></tv>', 
                    mimetype="application/xml")

if __name__ == "__main__":
    # Render usa a porta 10000 por padrão
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

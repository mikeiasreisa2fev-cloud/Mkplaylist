import requests
from flask import Flask, Response, redirect, request
import os
import time
import uuid
import json

app = Flask(__name__)

# ✅ CONFIGURAÇÕES EXATAS DA SUA API
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0 (Android; Mobile; rv:100.0)"
APP_ID = "site.xuipflix.pflix"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]
        self.debug_log = []

    def log(self, msg):
        self.debug_log.append(msg)
        print(f"[DEBUG] {msg}")

    def login(self):
        """Login com campos CORRETOS: user/pass conforme documentação"""
        if self.token:
            return self.token
            
        self.log(f"Tentando login: device_id={self.device_id}")
        try:
            payload = {
                "user": f"guest_{self.device_id[:8]}",
                "pass": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            headers = {
                "User-Agent": USER_AGENT,
                "X-Requested-With": APP_ID,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=headers, timeout=25)
            self.log(f"Login status: {r.status_code}")
            self.log(f"Resposta login: {r.text[:500]}")

            if r.status_code == 200:
                try:
                    data = r.json()
                    # TIRA O TOKEN DE DIVERSOS LOCAIS COMUNS
                    self.token = (data.get("token") or 
                                 data.get("data", {}).get("token") or 
                                 data.get("access_token"))
                    if self.token:
                        self.log(f"✅ Token obtido: {self.token[:30]}...")
                        return self.token
                    else:
                        self.log("❌ JSON OK mas SEM TOKEN!")
                except json.JSONDecodeError:
                    self.log("❌ Resposta não é JSON válido")
        except Exception as e:
            self.log(f"❌ Erro requisição: {str(e)}")
        return None

    def get_headers(self):
        headers = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": APP_ID,
            "Accept": "application/json"
        }
        token = self.login()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            self.log(f"Cabeçalho Auth: Bearer {token[:25]}...")
        return headers

api = SpeedFlixAPI()

@app.route("/")
def index():
    # Mostra o log de debug direto na página inicial
    log_html = "<br>".join(api.debug_log) or "Nenhum log ainda."
    return f"""
    <h1>🔍 DIAGNÓSTICO YCINEFLIX</h1>
    <p><a href="/playlist.m3u" style="font-size:20px; font-weight:bold;">➡️ Testar Playlist</a></p>
    <p><a href="/debug">Ver /debug</a> | <a href="/epg.xml">EPG</a></p>
    <hr><h3>Últimos logs:</h3><p>{log_html}</p>
    """

@app.route("/debug")
def debug():
    """Testa diretamente acesso à API e mostra TUDO que acontece"""
    resp = []
    resp.append("=== TESTE DE CONEXÃO ===\n")
    
    resp.append("\n1. Testando raiz da API...")
    try:
        r = requests.get(BASE_URL, timeout=10)
        resp.append(f"Status: {r.status_code} | Tamanho: {len(r.text)}")
    except Exception as e:
        resp.append(f"Erro: {e}")
    
    resp.append("\n2. Testando login...")
    token = api.login()
    resp.append(f"Token: {token if token else 'FALHOU'}")
    
    resp.append("\n3. Testando /channels...")
    try:
        headers = api.get_headers()
        r = requests.get(f"{BASE_URL}/channels", params={"per_page": 10}, headers=headers, timeout=20)
        resp.append(f"Status: {r.status_code}")
        resp.append(f"Tipo conteúdo: {r.headers.get('Content-Type','')}")
        resp.append(f"Resposta bruta (primeiros 600 chars):\n{r.text[:600]}")
    except Exception as e:
        resp.append(f"Erro: {e}")

    return Response("\n".join(resp), mimetype="text/plain", status=200)

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total_canais = 0
    api.debug_log.clear()

    try:
        headers = api.get_headers()
        api.log(f"Cabeçalhos enviados: {list(headers.keys())}")
        
        # Primeiro teste SEM server_id; depois com server_id=1,2,3
        for sid in [None, 1, 2, 3]:
            params = {"per_page": 200, "page": 1}
            if sid: params["server_id"] = sid
            
            api.log(f"Buscando canais com parâmetros: {params}")
            r = requests.get(f"{BASE_URL}/channels", params=params, headers=headers, timeout=25)
            api.log(f"Status {r.status_code} | Recb: {len(r.text)} bytes")

            if r.status_code != 200:
                api.log("❌ Resposta não 200")
                continue

            try:
                data = r.json()
            except:
                api.log("❌ Não é JSON!")
                m3u.append(f"# ERRO: Resposta não JSON (sid={sid})")
                continue

            # Tenta extrair itens de TODOS os caminhos possíveis
            items = (data.get("items") or 
                     data.get("data", {}).get("items") or 
                     data.get("result", {}).get("items") or [])
            api.log(f"Itens encontrados: {len(items)}")

            if not items:
                continue

            for ch in items:
                cid = ch.get("id")
                if not cid: continue
                name = ch.get("name") or ch.get("title") or "Sem Nome"
                cat = ch.get("category_name") or ch.get("category") or "CANAIS"
                logo = ch.get("image") or ch.get("logo", "")
                srv = ch.get("server_id") or sid or 1

                m3u.append(f'#EXTINF:-1 tvg-id="ch_{cid}" tvg-logo="{logo}" group-title="{cat.upper()}",{name}')
                m3u.append(f'{host}stream/{srv}/{cid}')
                total_canais += 1
            break # Se encontrou canais, para de testar outros servidores

    except Exception as e:
        api.log(f"❌ Erro geral: {str(e)}")
        m3u.append(f"# ERRO GERAL: {str(e)}")

    if total_canais == 0:
        m3u.append("# AVISO: Nenhum canal carregado.")
        m3u.append("# Logs em /debug ou nos logs do servidor")
        m3u.append(f"# Último erro: {api.debug_log[-2:] if api.debug_log else 'sem log'}")

    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    clean_cid = cid.split("?")[0].split("|")[0]
    try:
        headers = api.get_headers()
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream",
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            stream_url = (data.get("data", {}).get("stream_url") or 
                         data.get("stream_url") or 
                         data.get("data", {}).get("url"))
            if stream_url:
                return redirect(stream_url)
        return f"Stream erro {r.status_code}", 404
    except Exception as e:
        return f"Erro: {str(e)}", 500

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="YCineFlix"></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

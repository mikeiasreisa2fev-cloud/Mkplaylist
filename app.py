import requests
from flask import Flask, Response, redirect, request
import os
import time
import uuid

app = Flask(__name__)

# 🔹 CONFIGURAÇÕES EXATAS PARA SUA API
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
APP_ID = "site.xuipflix.app"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        """✅ LOGIN CORRIGIDO - CAMPO CERTO = user / pass (não username!)"""
        if self.token:
            return self.token
        try:
            # 🔴 ALTERAÇÃO CRUCIAL: A API ESPERA "user" e "pass" NÃO username/password!
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
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=headers, timeout=20)
            print(f"STATUS LOGIN: {r.status_code} | RESPOSTA: {r.text[:200]}") # Debug
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("token") or data.get("data", {}).get("token")
                print(f"✅ TOKEN OBTIDO: {self.token[:30]}...")
                return self.token
            print("❌ FALHA NO LOGIN!")
        except Exception as e:
            print(f"ERRO LOGIN: {str(e)}")
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
        return headers

api = SpeedFlixAPI()

@app.route("/")
def index():
    return """
    <h1>✅ PROXY YCINEFLIX CORRIGIDO</h1>
    <p>Playlist: <a href="/playlist.m3u" target="_blank">/playlist.m3u</a></p>
    <p>EPG: <a href="/epg.xml">/epg.xml</a></p>
    <p>⚠️ Se ainda vazio: verifique logs no Render!</p>
    """

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total_canais = 0

    # 🔹 TENTA PEGAR TODOS OS CANAIS SEM FILTRO DE SERVIDOR PRIMEIRO
    try:
        headers = api.get_headers()
        # ✅ REQUISIÇÃO CORRIGIDA: SEM server_id ERRADO NO INICIO
        r = requests.get(f"{BASE_URL}/channels", params={"per_page": 500}, headers=headers, timeout=30)
        print(f"STATUS CANAIS: {r.status_code} | TAMANHO: {len(r.text)}")
        
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", {}).get("items") or data.get("items") or []
            print(f"🔍 CANAIS ENCONTRADOS: {len(items)}")

            for ch in items:
                cid = ch.get("id")
                if not cid: continue

                name = ch.get("name") or ch.get("title") or "Canal Sem Nome"
                cat = ch.get("category_name") or "CANAIS"
                logo = ch.get("image") or ch.get("logo", "")
                sid = ch.get("server_id", 1) # Usa o servidor que vem do canal mesmo!

                # ✅ LINK DO STREAM APONTA PARA SEU PROXY
                m3u.append(f'#EXTINF:-1 tvg-id="ch_{cid}" tvg-logo="{logo}" group-title="{cat.upper()}",{name}')
                m3u.append(f'{host}stream/{sid}/{cid}\n')
                total_canais += 1

    except Exception as e:
        print(f"❌ ERRO AO CARREGAR CANAIS: {str(e)}")

    if total_canais == 0:
        m3u.append("# ERRO: Nenhum canal carregado! Verifique LOGIN acima nos logs.")

    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    clean_cid = cid.split("?")[0]

    try:
        headers = api.get_headers()
        # ✅ PEGA O LINK REAL DO STREAM
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=20)

        if r.status_code == 200:
            data = r.json()
            stream_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if stream_url:
                return redirect(stream_url)

        return f"ERRO STREAM: {r.status_code}", 404
    except Exception as e:
        return f"ERRO: {str(e)}", 500

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="YCineFlix"></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

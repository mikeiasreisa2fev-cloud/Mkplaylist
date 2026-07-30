from flask import Flask, Response, redirect, request
import os
import time
import requests

app = Flask(__name__)

# Configurações para o Redirect de Vídeo
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

@app.route("/")
def index():
    return "<h1>Proxy SpeedFlix Ativo no Railway</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def serve_playlist():
    if os.path.exists("playlist.m3u"):
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "#EXTM3U\n# Erro: Lista ainda nao gerada no GitHub.", 200

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    clean_cid = cid.split('|')[0].split('?')[0]
    try:
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID}
        r = requests.get(f"{BASE_URL}/channels/{clean_cid}/stream", 
                        params={"server_id": sid, "t": int(time.time())},
                        headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            if video_url:
                # Sufixo para o TiviMate abrir o vídeo com os headers corretos
                return redirect(video_url + f"|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}")
    except: pass
    return "Erro", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

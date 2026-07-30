from flask import Flask, Response, redirect, request
import os

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>SpeedFlix Proxy Ativo</h1><p>M3U: /playlist.m3u</p><p>EPG: /epg.xml</p>"

@app.route("/playlist.m3u")
def playlist():
    if os.path.exists("playlist.m3u"):
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "#EXTM3U\n# Erro: Lista ainda nao gerada. Aguarde o GitHub Actions.", 200

@app.route("/stream/<int:sid>/<int:cid>")
def stream(sid, cid):
    # Link direto para o vídeo que descobrimos no seu código-fonte
    url = f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8"
    # Headers necessários para o vídeo não travar
    suffix = "|User-Agent=okhttp/4.12.0&Referer=https://app.pobreflix2.site/"
    return redirect(url + suffix)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

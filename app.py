import os
from flask import Flask, Response, request

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Proxy Ativo</h1><p>M3U: /playlist.m3u</p>"

@app.route("/playlist.m3u")
def serve_playlist():
    if os.path.exists("playlist.m3u"):
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "#EXTM3U\n# Erro: Lista nao gerada. Rode o Action no GitHub.", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

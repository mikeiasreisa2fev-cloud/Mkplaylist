import os
from flask import Flask, Response, request

app = Flask(__name__)

@app.route("/")
def index():
    host = request.host_url
    return f"""
    <h1>SpeedFlix Proxy Ativo</h1>
    <p>Adicione no TiviMate:</p>
    <ul>
        <li><b>Playlist:</b> <code>{host}playlist.m3u</code></li>
        <li><b>EPG:</b> <code>{host}epg.xml</code></li>
    </ul>
    """

@app.route("/playlist.m3u")
def serve_playlist():
    """Serve a lista de canais gerada pelo GitHub."""
    file_path = "playlist.m3u"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "#EXTM3U\n# Erro: Lista nao gerada. Rode o Action no GitHub.", 200

@app.route("/epg.xml")
def serve_epg():
    """Serve o guia de programação gerado pelo GitHub."""
    file_path = "epg.xml"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/xml")
    return '<?xml version="1.0" encoding="UTF-8"?><tv></tv>', 200

if __name__ == "__main__":
    # Railway usa a porta 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

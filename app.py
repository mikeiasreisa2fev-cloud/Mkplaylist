import os
from flask import Flask, Response, request

app = Flask(__name__)

@app.route("/")
def index():
    host = request.host_url
    return f"""
    <h1>SpeedFlix Proxy (Static Mode)</h1>
    <p>Adicione no TiviMate:</p>
    <ul>
        <li><b>Playlist:</b> <code>{host}playlist.m3u</code></li>
        <li><b>EPG:</b> <code>{host}epg.xml</code></li>
    </ul>
    """

@app.route("/playlist.m3u")
def serve_playlist():
    """Serve o arquivo M3U gerado pelo GitHub Actions."""
    file_path = "playlist.m3u"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    
    # Mensagem de erro caso o GitHub ainda não tenha gerado o arquivo
    return "#EXTM3U\n# Erro: A lista ainda nao foi gerada. Por favor, ative o Action no GitHub.", 200

@app.route("/epg.xml")
def epg():
    """Serve um arquivo EPG básico."""
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="SpeedFlix Proxy"></tv>', 
                    mimetype="application/xml")

if __name__ == "__main__":
    # O Railway usa a porta definida na variável PORT ou a 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

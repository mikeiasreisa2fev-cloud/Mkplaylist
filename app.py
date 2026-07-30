import os
from flask import Flask, Response, request

app = Flask(__name__)

@app.route("/")
def index():
    host = request.host_url
    return f"""
    <h1>SpeedFlix Proxy Ativo (Modo Estático)</h1>
    <p>Use este link no TiviMate:</p>
    <code>{host}playlist.m3u</code>
    """

@app.route("/playlist.m3u")
def serve_playlist():
    """Entrega o arquivo gerado pelo GitHub Actions."""
    file_path = "playlist.m3u"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    
    return "#EXTM3U\n# Erro: O arquivo playlist.m3u ainda nao foi gerado no GitHub.", 200

@app.route("/epg.xml")
def epg():
    """Entrega o EPG gerado pelo GitHub Actions."""
    file_path = "epg.xml"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/xml")
            
    return '<?xml version="1.0" encoding="UTF-8"?><tv></tv>', 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

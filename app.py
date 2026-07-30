import os
from flask import Flask, Response, request

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>SpeedFlix Online</h1>"

@app.route("/playlist.m3u")
def playlist():
    if os.path.exists("playlist.m3u"):
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "#EXTM3U\n# Erro: Lista ainda nao gerada.", 200

@app.route("/epg.xml")
def epg():
    if os.path.exists("epg.xml"):
        with open("epg.xml", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/xml")
    return '<?xml version="1.0" encoding="UTF-8"?><tv></tv>', 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

import os
from flask import Flask, Response, request

app = Flask(__name__)

@app.route("/")
def index():
    """Página inicial com informações de ajuda."""
    host = request.host_url
    return f"""
    <h1>SpeedFlix Proxy (Static Mode)</h1>
    <p>O servidor está online!</p>
    <p>Use os links abaixo no seu player (TiviMate):</p>
    <ul>
        <li><b>Playlist:</b> <code>{host}playlist.m3u</code></li>
        <li><b>EPG:</b> <code>{host}epg.xml</code></li>
    </ul>
    <hr>
    <p><i>Nota: Se a playlist aparecer vazia, certifique-se de rodar o 'Action' no seu GitHub.</i></p>
    """

@app.route("/playlist.m3u")
def serve_playlist():
    """Entrega o arquivo playlist.m3u gerado pelo script do GitHub Actions."""
    file_path = "playlist.m3u"
    
    # Verifica se o arquivo existe (ele é criado pelo update_list.py no GitHub)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return Response(content, mimetype="text/plain")
    
    # Se o GitHub ainda não gerou o arquivo, avisa o usuário
    return "#EXTM3U\n# Erro: O arquivo playlist.m3u ainda nao foi gerado pelo GitHub Actions.", 200

@app.route("/epg.xml")
def epg():
    """Retorna um arquivo EPG básico para não dar erro no player."""
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="SpeedFlix Proxy"></tv>', 
                    mimetype="application/xml")

if __name__ == "__main__":
    # O Railway define a porta automaticamente na variável de ambiente PORT (geralmente 8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

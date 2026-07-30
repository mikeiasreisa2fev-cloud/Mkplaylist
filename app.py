from flask import Flask, Response, redirect, request
import os
import requests
import time

app = Flask(__name__)

# Configurações para o Redirect de Vídeo
# Usamos o domínio que o app usa internamente
BASE_API = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"

@app.route("/")
def index():
    return f"<h1>SpeedFlix Proxy Ativo no Railway</h1><p>Playlist M3U: <code>{request.host_url}playlist.m3u</code></p>"

@app.route("/playlist.m3u")
def serve_playlist():
    """Serve o arquivo playlist.m3u que foi gerado e salvo pelo GitHub Actions."""
    file_path = "playlist.m3u"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return Response(content, mimetype="text/plain")
    
    # Se o arquivo não existir, retorna um erro amigável para o TiviMate
    return "#EXTM3U\n# Erro: O arquivo playlist.m3u ainda nao foi gerado no GitHub.", 200

@app.route("/stream/<int:sid>/<path:cid>")
def stream_proxy(sid, cid):
    """
    Esta rota é chamada quando você clica em um canal no TiviMate.
    Ela busca o link real do vídeo e entrega para o player.
    """
    # Limpa o ID do canal removendo sufixos do player
    clean_cid = cid.split('|')[0].split('?')[0]
    
    try:
        # Headers necessários para o servidor liberar o link do vídeo
        headers = {
            "User-Agent": USER_AGENT,
            "X-Requested-With": APP_ID
        }
        
        # Faz a chamada para pegar o link m3u8 real
        # O parâmetro 't' é um timestamp para validar a sessão
        url = f"{BASE_API}/channels/{clean_cid}/stream"
        r = requests.get(url, params={"server_id": sid, "t": int(time.time())}, 
                        headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            video_url = data.get("data", {}).get("stream_url") or data.get("stream_url")
            
            if video_url:
                # O SEGREDO: Redireciona para o vídeo original adicionando os headers que o TiviMate entende
                # O símbolo '|' faz o TiviMate usar o que vem depois como cabeçalho HTTP
                auth_url = f"{video_url}|User-Agent={USER_AGENT}&X-Requested-With={APP_ID}"
                return redirect(auth_url)
                
    except Exception as e:
        print(f"Erro no stream: {e}")
        
    return "Link de vídeo indisponível ou IP bloqueado", 404

if __name__ == "__main__":
    # O Railway define a porta automaticamente na variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

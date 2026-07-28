import requests
from flask import Flask, Response
import os

app = Flask(__name__)

SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
SESS = requests.Session()
SESS.headers.update({"User-Agent": USER_AGENT})

@app.route("/")
def index():
    return "<h1>Diagnóstico HTML</h1><p>Acesse /ver-html para ver o código bruto.</p>"

@app.route("/ver-html")
def ver_html():
    resp = []
    for srv in SERVERS:
        resp.append(f"\n===== {srv['name']} =====\nURL: {srv['url']}\n")
        try:
            r = SESS.get(srv["url"], timeout=20)
            resp.append(f"STATUS: {r.status_code}\n")
            resp.append(f"TAMANHO: {len(r.text)} bytes\n")
            # Salva só o início para não ficar gigante
            resp.append(f"--- INÍCIO DO HTML ---\n{r.text[:1500]}...\n")
            resp.append(f"--- FIM DO TRECHO ---\n")
        except Exception as e:
            resp.append(f"ERRO: {e}\n")
    return Response("\n".join(resp), mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

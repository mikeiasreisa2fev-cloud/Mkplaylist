from flask import Flask, Response, redirect, request
import cloudscraper
from bs4 import BeautifulSoup
import re
import os
import time

app = Flask(__name__)

SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

# Scraper anti-bloqueio
SCRAPER = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True},
    delay=3,
    interpreter="js2py"
)

def pegar_html(url):
    for tentativa in range(4):
        try:
            if tentativa > 0: time.sleep(2.5 * tentativa)
            r = SCRAPER.get(url, timeout=30)
            r.raise_for_status()
            if len(r.text) < 1200 or "Verificando" in r.text:
                print(f"[Desafio {tentativa+1}] {url[:60]}")
                continue
            return r.text
        except Exception as e:
            print(f"[Erro {tentativa+1}] {url[:60]}: {str(e)}")
    return ""

def extrair_links(html):
    soup = BeautifulSoup(html, "html.parser")
    res = {"categorias": [], "canais": []}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        nome = a.get_text(strip=True)
        if not nome or len(nome) < 2 or href.startswith("javascript"): continue
        if not href.startswith("http"):
            href = "https://app.pobreflix2.site" + href
        if any(p in href.lower() for p in ["/categoria", "categorias", "cat="]):
            res["categorias"].append({"nome": nome, "url": href})
        elif any(p in href.lower() for p in ["/canal", "player", "id=", "assistir"]):
            res["canais"].append({"nome": nome, "url": href})
    # Remover duplicatas
    vistos = set()
    for tipo in res:
        res[tipo] = [x for x in res[tipo] if not (x["url"] in vistos or vistos.add(x["url"]))]
    return res

def achar_stream(url_canal):
    html = pegar_html(url_canal)
    if not html: return None
    padroes = [
        r'https?://[^\s"\']+\.m3u8[^\s"\']*',
        r'stream_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'streamUrl\s*:\s*["\']([^"\']+)["\']',
        r'file\s*:\s*["\']([^"\']+)["\']'
    ]
    for p in padroes:
        m = re.search(p, html, re.I)
        if m: return m.group(1) or m.group(0)
    return None

# 📱 ROTAS — FORMATO 100% TIVIMATE
@app.route("/")
def home():
    return "<h1>✅ Playlist Pronta para TiviMate</h1><p>Use: /playlist.m3u</p>"

@app.route("/teste")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_html(srv["url"])
        saida.append("✅ OK" if html else "❌ Bloqueado")
        if html: saida.append(f"Tamanho: {len(html)}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url.rstrip('/')  # Remove barra final
    m3u = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-TARGETDURATION:15"]
    total = 0
    for srv in SERVERS:
        html = pegar_html(srv["url"])
        if not html: continue
        dados = extrair_links(html)
        # Categorias
        for cat in dados["categorias"][:10]:
            hcat = pegar_html(cat["url"])
            if not hcat: continue
            canais = extrair_links(hcat)["canais"]
            for ch in canais:
                m3u.append(f'#EXTINF:-1 tvg-id="ch{total}" tvg-logo="" group-title="{cat["nome"]} | {srv["name"]}",{ch["nome"]}')
                m3u.append(f'{host}/stream/{srv["id"]}/{total}?u={ch["url"]}')
                total += 1
        # Canais diretos se sem categorias
        for ch in dados["canais"]:
            m3u.append(f'#EXTINF:-1 tvg-id="ch{total}" tvg-logo="" group-title="Direto {srv["name"]}",{ch["nome"]}')
            m3u.append(f'{host}/stream/{srv["id"]}/{total}?u={ch["url"]}')
            total += 1
    if total == 0:
        m3u.append("#EXTINF:-1,ERRO: Nenhum canal encontrado")
    return Response(
        "\n".join(m3u) + "\n",
        mimetype="application/vnd.apple.mpegurl; charset=utf-8",
        headers={"Content-Disposition": "inline; filename=playlist.m3u; charset=utf-8"}
    )

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    u = request.args.get("u")
    if not u: return "URL inválida", 400
    link = achar_stream(u)
    return redirect(link, code=302) if link else Response("#ERRO: Stream não encontrada", status=404)

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml; charset=utf-8")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

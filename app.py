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

# 🔹 SCRAPER QUE CONTORNA CLOUDFLARE/BOT PROTECTION
SCRAPER = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "windows",
        "desktop": True
    },
    delay=5,
    interpreter="js2py"
)

def pegar_html(url):
    for tentativa in range(4):
        try:
            if tentativa > 0:
                time.sleep(2.5 * tentativa)
            r = SCRAPER.get(url, timeout=30)
            r.raise_for_status()
            if len(r.text) < 1200 or "Verificando" in r.text:
                print(f"[⚠️ DESAFIO] Tentativa {tentativa+1} - {url[:60]}")
                continue
            return r.text
        except Exception as e:
            print(f"[❌ ERRO {tentativa+1}] {url[:60]}: {str(e)}")
    return ""

def extrair_links(html):
    soup = BeautifulSoup(html, "html.parser")
    res = {"categorias": [], "canais": []}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        nome = a.get_text(strip=True)
        if not nome or len(nome) < 2 or href.startswith("javascript"):
            continue
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

# 📱 ROTAS
@app.route("/")
def home():
    return "<h1>✅ CloudScraper Ativo</h1><p>Diagnóstico: <a href='/teste'>/teste</a></p><p>Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/teste")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_html(srv["url"])
        if not html:
            saida.append("❌ Ainda bloqueado / offline")
            continue
        saida.append(f"✅ Página carregada: {len(html)} caracteres")
        dados = extrair_links(html)
        saida.append(f"📁 Categorias: {len(dados['categorias'])}")
        for c in dados["categorias"][:4]: saida.append(f"   ↳ {c['nome']}")
        saida.append(f"📺 Canais diretos: {len(dados['canais'])}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0
    for srv in SERVERS:
        html = pegar_html(srv["url"])
        if not html:
            m3u.append(f"# ❌ {srv['name']}: Sem acesso")
            continue
        dados = extrair_links(html)
        if dados["categorias"]:
            for cat in dados["categorias"][:10]:
                hcat = pegar_html(cat["url"])
                if not hcat: continue
                canais = extrair_links(hcat)["canais"]
                for ch in canais:
                    m3u.append(f'#EXTINF:-1 group-title="{cat["nome"]} | {srv["name"]}",{ch["nome"]}')
                    m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                    total += 1
        elif dados["canais"]:
            for ch in dados["canais"]:
                m3u.append(f'#EXTINF:-1 group-title="Direto {srv["name"]}",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
    if total == 0:
        m3u.append("# ❌ Nenhum canal extraído")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    u = request.args.get("u")
    if not u: return "Faltou parâmetro", 400
    link = achar_stream(u)
    return redirect(link) if link else "Não encontrado", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

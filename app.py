from flask import Flask, Response, redirect, request
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

# ✅ Servidores
SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

# 🔹 Sessão imitando navegador real
SESS = requests.Session()
SESS.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://app.pobreflix2.site/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
})

def pegar_html(url):
    try:
        r = SESS.get(url, timeout=20)
        r.encoding = "utf-8"
        return r.text
    except Exception as e:
        print(f"[ERRO] {url[:60]}: {str(e)}")
        return ""

def extrair_links(html, tipo):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    regras = {
        "categoria": ["/categoria", "categorias", "cat="],
        "canal": ["/canal", "canal?", "player", "id="]
    }[tipo]
    for a in soup.find_all("a", href=True):
        href = a["href"]
        nome = a.get_text(strip=True)
        if not nome or len(nome) < 2: continue
        if any(p in href for p in regras):
            if not href.startswith("http"):
                href = "https://app.pobreflix2.site" + href
            links.append({"nome": nome, "url": href})
    # Remover duplicatas
    return list({l["url"]: l for l in links}.values())

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
    return "<h1>✅ Proxy Leve 100% Requisições</h1><p>Teste: <a href='/teste'>/teste</a> | Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/teste")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_html(srv["url"])
        if not html:
            saida.append("❌ Falha ao carregar")
            continue
        saida.append(f"✅ OK: {len(html)} caracteres")
        cats = extrair_links(html, "categoria")
        saida.append(f"📁 Categorias: {len(cats)}")
        for c in cats[:3]: saida.append(f"   → {c['nome']}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0
    for srv in SERVERS:
        html = pegar_html(srv["url"])
        if not html: continue
        cats = extrair_links(html, "categoria")
        if not cats:
            canais = extrair_links(html, "canal")
            for ch in canais:
                m3u.append(f'#EXTINF:-1 group-title="Direto {srv["name"]}",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
            continue
        for cat in cats[:12]:
            hcat = pegar_html(cat["url"])
            canais = extrair_links(hcat, "canal")
            for ch in canais:
                m3u.append(f'#EXTINF:-1 group-title="{cat["nome"]} | {srv["name"]}",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
    if total == 0:
        m3u.append("# ❌ Nenhum canal — verifique /teste")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    u = request.args.get("u")
    if not u: return "Erro", 400
    link = achar_stream(u)
    return redirect(link) if link else "Não encontrado", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

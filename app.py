from flask import Flask, Response, redirect, request
from pyppeteer import launch
from bs4 import BeautifulSoup
import asyncio
import time
import os
import re

app = Flask(__name__)

SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

async def carregar_pagina(url):
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,720",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        page = await browser.newPage()
        await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0.0.0 Safari/537.36")
        await page.goto(url, {"waitUntil": "networkidle2", "timeout": 40000})
        await asyncio.sleep(6) # Tempo extra para carregar tudo
        return await page.content()
    except Exception as e:
        print(f"[ERRO] {str(e)}")
        return ""
    finally:
        if browser: await browser.close()

def pegar_html(url):
    return asyncio.run(carregar_pagina(url))

# 🔧 FUNÇÃO CHAVE: PEGA TODOS OS LINKS RELEVANTES (não depende de classes)
def extrair_todos_links(html, tipo="categoria"):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    palavras_chave = {
        "categoria": ["/categoria", "categorias", "cat="],
        "canal": ["/canal", "canal?", "id=", "player"]
    }[tipo]

    for a in soup.find_all("a", href=True):
        href = a["href"]
        texto = a.get_text(strip=True)
        if not texto or len(texto) < 2: continue
        if any(p in href.lower() for p in palavras_chave):
            if not href.startswith("http"):
                href = "https://app.pobreflix2.site" + href
            links.append({"nome": texto, "url": href})

    # Remove duplicatas
    vistos = set()
    unicos = []
    for l in links:
        if l["url"] not in vistos:
            vistos.add(l["url"])
            unicos.append(l)
    return unicos

def encontrar_stream(url_canal):
    html = pegar_html(url_canal)
    if not html: return None
    padroes = [
        r'https?://[^\s"\']+\.m3u8[^\s"\']*',
        r'stream_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'streamUrl\s*:\s*["\']([^"\']+)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
    ]
    for p in padroes:
        m = re.search(p, html, re.I)
        if m: return m.group(1) or m.group(0)
    return None

# 📱 ROTAS
@app.route("/")
def home():
    return "<h1>✅ Corrigido: Extração de Links Geral</h1><p>Teste: <a href='/verificar'>/verificar</a></p>"

@app.route("/verificar")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_html(srv["url"])
        if not html:
            saida.append("❌ Falha")
            continue
        saida.append(f"✅ OK: {len(html)} bytes")
        cats = extrair_todos_links(html, "categoria")
        saida.append(f"📁 Categorias: {len(cats)}")
        for c in cats[:5]: saida.append(f"   → {c['nome']} | {c['url'][:60]}...")
        canais = extrair_todos_links(html, "canal")
        saida.append(f"📺 Canais diretos: {len(canais)}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0
    for srv in SERVERS:
        html = pegar_html(srv["url"])
        if not html: continue
        cats = extrair_todos_links(html, "categoria")
        if not cats:
            # Se não achar categorias, tenta pegar canais direto
            canais = extrair_todos_links(html, "canal")
            for ch in canais:
                m3u.append(f'#EXTINF:-1 tvg-logo="" group-title="Direto {srv["name"]}",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
            continue
        for cat in cats[:10]:
            hcat = pegar_html(cat["url"])
            canais = extrair_todos_links(hcat, "canal")
            for ch in canais:
                m3u.append(f'#EXTINF:-1 tvg-logo="" group-title="{cat["nome"]} | {srv["name"]}",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
    if total == 0:
        m3u.append("# ❌ Ainda sem canais. Veja /verificar")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    u = request.args.get("u")
    if not u: return "Erro", 400
    link = encontrar_stream(u)
    return redirect(link) if link else "Não encontrado", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

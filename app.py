from flask import Flask, Response, redirect, request
from pyppeteer import launch
from bs4 import BeautifulSoup
import asyncio
import time
import os
import re

app = Flask(__name__)

# ✅ SEUS SERVIDORES
SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

# 🔧 NAVEGADOR ASSÍNCRONO LEVE E COMPATÍVEL
async def pegar_pagina_pyppeteer(url):
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--disable-blink-features=AutomationControlled"
            ],
            defaultViewport=None
        )
        page = await browser.newPage()
        await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
        await page.goto(url, {"waitUntil": "networkidle2", "timeout": 30000})
        await asyncio.sleep(4) # Espera JS carregar
        conteudo = await page.content()
        print(f"[✓] Carregado: {url[:60]} | Tamanho: {len(conteudo)}")
        return conteudo
    except Exception as e:
        print(f"[✗] Erro {url[:60]}: {str(e)}")
        return ""
    finally:
        if browser:
            await browser.close()

def pegar_pagina(url):
    """Wrapper síncrono para Flask"""
    return asyncio.run(pegar_pagina_pyppeteer(url))

def extrair_categorias(html):
    soup = BeautifulSoup(html, "html.parser")
    cats = []
    seletores = ["a[href*='categorias']", ".category-item a", ".list-group a", "div.card a"]
    for sel in seletores:
        for a in soup.select(sel):
            nome = a.get_text(strip=True)
            href = a.get("href")
            if nome and href and not "javascript" in href:
                if not href.startswith("http"):
                    href = "https://app.pobreflix2.site" + href
                cats.append({"nome": nome, "url": href})
        if cats: break
    return cats

def extrair_canais(html):
    soup = BeautifulSoup(html, "html.parser")
    canais = []
    seletores = ["a[href*='canal']", ".channel-link", ".video-item a", ".item a"]
    for sel in seletores:
        for a in soup.select(sel):
            nome = a.get_text(strip=True)
            href = a.get("href")
            if not nome or len(nome) < 3 or not href: continue
            if not href.startswith("http"):
                href = "https://app.pobreflix2.site" + href
            img = a.find("img")
            logo = img.get("data-src") or img.get("src", "") if img else ""
            if logo and not logo.startswith("http"):
                logo = "https://app.pobreflix2.site" + logo
            canais.append({"nome": nome, "url": href, "logo": logo})
        if canais: break
    return canais

def achar_stream(url):
    html = pegar_pagina(url)
    if not html: return None
    patterns = [
        r'https?://[^\s"\']+\.m3u8[^\s"\']*',
        r'stream_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'streamUrl\s*:\s*["\']([^"\']+)["\']'
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m: return m.group(0) if isinstance(m.group(0), str) else m.group(1)
    return None

# 📱 ROTAS
@app.route("/")
def home():
    return "<h1>✅ Proxy Pyppeteer Estável</h1><p>Teste: <a href='/teste'>/teste</a> | Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/teste")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_pagina(srv["url"])
        if not html:
            saida.append("❌ Falha ao carregar")
            continue
        saida.append(f"✅ OK: {len(html)} bytes")
        cats = extrair_categorias(html)
        saida.append(f"📁 Categorias: {len(cats)}")
        for c in cats[:3]: saida.append(f"   → {c['nome']}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0
    for srv in SERVERS:
        html = pegar_pagina(srv["url"])
        if not html: continue
        cats = extrair_categorias(html)
        for cat in cats[:12]:
            hcat = pegar_pagina(cat["url"])
            if not hcat: continue
            canais = extrair_canais(hcat)
            for ch in canais:
                m3u.append(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{cat["nome"]} [{srv["name"]}]",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
    if total == 0:
        m3u.append("# ❌ Nenhum canal. Verifique /teste")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    url = request.args.get("u")
    if not url: return "Erro", 400
    link = achar_stream(url)
    return redirect(link) if link else "Não encontrado", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

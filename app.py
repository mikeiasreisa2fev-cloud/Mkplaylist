from flask import Flask, Response, redirect, request
from pyppeteer import launch
from bs4 import BeautifulSoup
import asyncio
import time
import os
import re

app = Flask(__name__)

# ✅ SEUS SERVIDORES PÚBLICOS
SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

# 🔧 NAVEGADOR VIRTUAL (SEM DEPENDÊNCIAS EXTRAS)
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
                "--disable-extensions",
                "--disable-images"
            ],
            defaultViewport=None,
            executablePath=None # Auto-detect
        )
        page = await browser.newPage()
        await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
        await page.goto(url, {"waitUntil": "domcontentloaded", "timeout": 30000})
        await asyncio.sleep(5) # Garante JS total
        return await page.content()
    except Exception as e:
        print(f"[ERRO] {url[:50]}: {str(e)}")
        return ""
    finally:
        if browser:
            try: await browser.close()
            except: pass

def pegar_html(url):
    """Wrapper seguro para Flask"""
    return asyncio.run(carregar_pagina(url))

def extrair_categorias(html):
    """Usa parser NATIVO do Python (SEM LXML)"""
    soup = BeautifulSoup(html, "html.parser")
    cats = []
    seletores = [
        "a[href*='categorias']", ".category-item a", 
        ".list-group a", "div.card a", ".menu a"
    ]
    for sel in seletores:
        for a in soup.select(sel):
            nome = a.get_text(strip=True)
            href = a.get("href")
            if nome and href and not "javascript:" in href:
                if not href.startswith("http"):
                    href = "https://app.pobreflix2.site" + href
                cats.append({"nome": nome, "url": href})
        if cats: break
    return cats

def extrair_canais(html):
    soup = BeautifulSoup(html, "html.parser")
    canais = []
    seletores = [
        "a[href*='canal']", ".channel-link", 
        ".video-item a", ".item-card a", ".card a"
    ]
    for sel in seletores:
        for a in soup.select(sel):
            nome = a.get_text(strip=True)
            href = a.get("href")
            if not nome or len(nome) < 3 or not href: continue
            if not href.startswith("http"):
                href = "https://app.pobreflix2.site" + href
            img = a.find("img")
            logo = ""
            if img:
                logo = img.get("data-src") or img.get("src", "")
                if logo and not logo.startswith("http"):
                    logo = "https://app.pobreflix2.site" + logo
            canais.append({"nome": nome, "url": href, "logo": logo})
        if canais: break
    return canais

def encontrar_stream(url_canal):
    html = pegar_html(url_canal)
    if not html: return None
    padroes = [
        r'https?://[^\s"\']+\.m3u8[^\s"\']*',
        r'stream_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'streamUrl\s*:\s*["\']([^"\']+)["\']',
        r'source\s*src=["\']([^"\']+)["\']'
    ]
    for p in padroes:
        m = re.search(p, html, re.IGNORECASE)
        if m: return m.group(1) or m.group(0)
    return None

# 📱 ROTAS DA APLICAÇÃO
@app.route("/")
def home():
    return """
    <h1>✅ Proxy Anti-Bloqueio (Python Puro)</h1>
    <p>Teste rápido: <a href='/verificar'>/verificar</a></p>
    <p>Playlist final: <a href='/playlist.m3u'>/playlist.m3u</a></p>
    """

@app.route("/verificar")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_html(srv["url"])
        if not html:
            saida.append("❌ Falha ao carregar página")
            continue
        saida.append(f"✅ Página OK: {len(html)} caracteres")
        cats = extrair_categorias(html)
        saida.append(f"📁 Categorias achadas: {len(cats)}")
        for cat in cats[:3]: saida.append(f"   ↳ {cat['nome']}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def gerar_playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3\n#EXT-INFO: Proxy MK PLAYLIST"]
    total = 0
    for servidor in SERVERS:
        html_base = pegar_html(servidor["url"])
        if not html_base:
            m3u.append(f"# AVISO: Não foi possível ler {servidor['name']}")
            continue
        categorias = extrair_categorias(html_base)
        if not categorias:
            m3u.append(f"# AVISO: Sem categorias em {servidor['name']}")
            continue
        for cat in categorias[:10]: # Limite segurança
            html_cat = pegar_html(cat["url"])
            if not html_cat: continue
            lista_canais = extrair_canais(html_cat)
            for ch in lista_canais:
                m3u.append(
                    f'#EXTINF:-1 tvg-id="ch{total}" tvg-logo="{ch["logo"]}" '
                    f'group-title="{cat["nome"]} | {servidor["name"]}",{ch["nome"]}'
                )
                m3u.append(f"{host}stream/{servidor['id']}/{total}?u={ch['url']}")
                total += 1
    if total == 0:
        m3u.append("\n# ❌ NENHUM CANAL ENCONTRADO")
        m3u.append("# Acesse /verificar para diagnóstico")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def rotear_stream(sid, cid):
    url = request.args.get("u")
    if not url: return "Parâmetro obrigatório 'u'", 400
    link_final = encontrar_stream(url)
    if link_final: return redirect(link_final)
    return "Link de stream não encontrado", 404

@app.route("/epg.xml")
def epg_vazio():
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="MK Proxy"/>',
        mimetype="application/xml"
    )

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)

from flask import Flask, Response, redirect, request
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
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

# 🔧 NAVEGADOR CAMUFLADO (NÃO DETECTADO COMO BOT)
def criar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") # 🔑 SEGREDO
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")

    driver = uc.Chrome(
        options=chrome_options,
        headless=True,
        use_subprocess=False
    )
    driver.set_page_load_timeout(30)
    return driver

def log_debug(msg):
    print(f"[LOG {time.ctime()}] {msg}")

def pegar_pagina(url):
    driver = None
    try:
        driver = criar_driver()
        log_debug(f"Acessando: {url}")
        driver.get(url)
        
        # Espera o conteúdo realmente aparecer
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body, main, .container"))
        )
        time.sleep(4) # Garante JS total
        
        return driver.page_source
    except Exception as e:
        log_debug(f"FALHA: {str(e)}")
        return ""
    finally:
        if driver:
            try: driver.quit()
            except: pass

def extrair_cats(html):
    soup = BeautifulSoup(html, "html.parser")
    r = []
    for sel in ["a[href*='categorias']", ".category a", ".list-group a", "div.card a"]:
        for a in soup.select(sel):
            nome = a.get_text(strip=True)
            href = a.get("href")
            if nome and href and not "javascript" in href:
                if not href.startswith("http"):
                    href = "https://app.pobreflix2.site" + href
                r.append({"nome": nome, "url": href})
        if r: break
    return r

def extrair_canais(html):
    soup = BeautifulSoup(html, "html.parser")
    r = []
    for sel in ["a[href*='canal']", ".channel-item a", ".video-card a", ".item a"]:
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
            r.append({"nome": nome, "url": href, "logo": logo})
        if r: break
    return r

def achar_stream(url):
    h = pegar_pagina(url)
    if not h: return None
    for p in [r'https?://[^\s"\']+\.m3u8[^\s"\']*', r'stream_url\s*[:=]\s*["\']([^"\']+)["\']']:
        m = re.search(p, h, re.I)
        if m: return m.group(0) if isinstance(m.group(0), str) else m.group(1)
    return None

# 📱 ROTAS
@app.route("/")
def home():
    return "<h1>✅ Proxy Anti-Bloqueio Ativo</h1><p>Teste: <a href='/teste'>/teste</a> | Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/teste")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n=== {srv['name']} ===")
        html = pegar_pagina(srv["url"])
        if not html:
            saida.append("❌ Falha ao carregar")
            continue
        saida.append(f"✅ OK: {len(html)} bytes")
        cats = extrair_cats(html)
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
        cats = extrair_cats(html)
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

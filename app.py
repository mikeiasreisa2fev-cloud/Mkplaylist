from flask import Flask, Response, redirect, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
import re

app = Flask(__name__)

# ✅ SERVIDORES PÚBLICOS QUE VOCÊ PASSOU
SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

# 🔧 Configura Chrome para rodar no Render (sem interface)
def criar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def pegar_canais_servidor(servidor):
    canais = []
    try:
        driver = criar_driver()
        driver.get(servidor["url"])
        time.sleep(6) # Espera JS carregar
        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, "html.parser")
        print(f"✅ Lendo {servidor['name']}")

        # Pega TODAS as categorias
        categorias = soup.select("a[href*='categorias']") or soup.select("div a")
        for cat in categorias:
            cat_url = cat.get("href")
            if not cat_url or "javascript:" in cat_url: continue
            if not cat_url.startswith("http"):
                cat_url = "https://app.pobreflix2.site" + cat_url

            try:
                d2 = criar_driver()
                d2.get(cat_url)
                time.sleep(4)
                cat_html = d2.page_source
                d2.quit()
                s_cat = BeautifulSoup(cat_html, "html.parser")
                grupo = cat.get_text(strip=True) or "CANAIS"

                # Pega canais na categoria
                items = s_cat.select("a[href*='canal']") or s_cat.select(".item a") or s_cat.select("div a")
                for item in items:
                    nome = item.get_text(strip=True)
                    href = item.get("href")
                    if not nome or not href: continue
                    if not href.startswith("http"):
                        href = "https://app.pobreflix2.site" + href

                    logo = ""
                    img = item.find("img")
                    if img:
                        logo = img.get("data-src") or img.get("src", "")
                        if logo and not logo.startswith("http"):
                            logo = "https://app.pobreflix2.site" + logo

                    canais.append({
                        "nome": nome,
                        "grupo": f"{grupo} [{servidor['name']}]",
                        "url_pagina": href,
                        "logo": logo,
                        "sid": servidor["id"]
                    })
            except Exception as ec:
                print(f"⚠️ Erro cat: {ec}")
    except Exception as e:
        print(f"❌ Erro servidor {servidor['id']}: {e}")
    return canais

def pegar_stream(url_canal):
    try:
        driver = criar_driver()
        driver.get(url_canal)
        time.sleep(5)
        html = driver.page_source
        driver.quit()
        m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
        if m: return m.group(1)
        m = re.search(r'stream_url\s*[=:]\s*["\']([^"\']+)["\']', html)
        if m: return m.group(1)
    except Exception as e:
        print(f"Erro stream: {e}")
    return None

# 🚀 ROTAS
@app.route("/")
def index():
    return "<h1>✅ Proxy SPEED-1/2/3 Ativo</h1><p>Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0
    for srv in SERVERS:
        for ch in pegar_canais_servidor(srv):
            m3u.append(f'#EXTINF:-1 tvg-id="s{ch["sid"]}_{total}" tvg-logo="{ch["logo"]}" group-title="{ch["grupo"]}",{ch["nome"]}')
            m3u.append(f'{host}stream/{ch["sid"]}/{total}?page={ch["url_pagina"]}')
            total += 1
    if total == 0:
        m3u.append("# ❌ Nenhum canal. Aguarde 1ª carga ou verifique logs.")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    page_url = request.args.get("page")
    if not page_url: return "Faltou parametro", 400
    link = pegar_stream(page_url)
    if link: return redirect(link)
    return "Link nao encontrado", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

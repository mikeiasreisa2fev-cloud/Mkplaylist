import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, redirect, request
import os
import time
import re

app = Flask(__name__)

# 🔹 CONFIGURAÇÕES DOS SERVIDORES PÚBLICOS
SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SESS = requests.Session()
SESS.headers.update({"User-Agent": USER_AGENT})

def pegar_links_stream(url_canal):
    """Entra na página do canal e extrai o link final .m3u8 ou stream"""
    try:
        r = SESS.get(url_canal, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Tenta achar embutido no JS ou source
        scripts = soup.find_all("script")
        for sc in scripts:
            if sc.string:
                # Padrões comuns de stream
                m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', sc.string)
                if m:
                    return m.group(1)
                m = re.search(r'stream_url\s*[=:]\s*["\']([^"\']+)["\']', sc.string)
                if m:
                    return m.group(1)
        
        # Tenta tag video > source
        vid = soup.find("video")
        if vid:
            src = vid.get("src")
            if src: return src
            src_tag = vid.find("source")
            if src_tag: return src_tag.get("src")
            
    except Exception as e:
        print(f"Erro canal {url_canal}: {e}")
    return None

def pegar_canais_servidor(servidor):
    """Varre categorias e canais de um servidor"""
    canais = []
    try:
        r = SESS.get(servidor["url"], timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        print(f"✅ Lendo {servidor['name']} — status {r.status_code}")

        # Ajuste o seletor CSS se a página mudar: busca links de categorias
        categorias = soup.select("a[href*='categorias']")
        if not categorias:
            categorias = soup.select("div a")

        for cat in categorias:
            cat_url = cat.get("href")
            if not cat_url or "javascript:" in cat_url:
                continue
            if not cat_url.startswith("http"):
                cat_url = "https://app.pobreflix2.site" + cat_url

            try:
                rcat = SESS.get(cat_url, timeout=15)
                s_cat = BeautifulSoup(rcat.text, "html.parser")
                grupo = cat.get_text(strip=True) or "CANAIS"

                # Busca canais dentro da categoria
                items = s_cat.select("a[href*='canal'], div.item a, .channel-item a")
                for item in items:
                    nome = item.get_text(strip=True)
                    href = item.get("href")
                    if not nome or not href:
                        continue
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
                print(f"Erro cat {cat_url}: {ec}")
    except Exception as e:
        print(f"Erro servidor {servidor['id']}: {e}")
    return canais

# ---------------- ROTAS FLASK ----------------
@app.route("/")
def index():
    return """
    <h1>✅ PROXY SEM LOGIN - POBREFLIX / YCINEFLIX</h1>
    <p>Servidores: SPEED-1, SPEED-2, SPEED-3</p>
    <p>Playlist: <a href="/playlist.m3u">/playlist.m3u</a></p>
    <p>Debug: <a href="/teste">/teste</a></p>
    """

@app.route("/teste")
def teste():
    res = []
    for srv in SERVERS:
        res.append(f"\n=== {srv['name']} ===")
        canais = pegar_canais_servidor(srv)
        res.append(f"Encontrados: {len(canais)} canais")
        if canais:
            res.append("Exemplo: " + canais[0]["nome"] + " -> " + canais[0]["url_pagina"])
    return Response("\n".join(res), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0

    for srv in SERVERS:
        lista = pegar_canais_servidor(srv)
        for ch in lista:
            m3u.append(f'#EXTINF:-1 tvg-id="s{ch["sid"]}_{total}" tvg-logo="{ch["logo"]}" group-title="{ch["grupo"]}",{ch["nome"]}')
            m3u.append(f'{host}stream/{ch["sid"]}/{total}?page={ch["url_pagina"]}')
            total += 1

    if total == 0:
        m3u.append("# Nenhum canal carregado. Verifique /teste ou se o site mudou layout.")

    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    page_url = request.args.get("page")
    if not page_url:
        return "Faltou parâmetro", 400
    try:
        stream_url = pegar_links_stream(page_url)
        if stream_url:
            return redirect(stream_url)
        return "Link não encontrado", 404
    except Exception as e:
        return f"Erro: {e}", 500

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="ProxySemLogin"></tv>', mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

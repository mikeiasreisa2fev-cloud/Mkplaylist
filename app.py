from flask import Flask, Response, redirect, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
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

# 🔧 CONFIGURAÇÃO OTIMIZADA PARA RENDER
def criar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-images") # 🚀 Carrega mais rápido
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0 Safari/537.36")
    chrome_options.page_load_strategy = 'eager' # Não espera recursos inúteis
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    driver.set_page_load_timeout(25)
    driver.implicitly_wait(8)
    return driver

def log_debug(msg):
    print(f"[DEBUG {time.strftime('%H:%M:%S')}] {msg}")

def pegar_conteudo_seguro(url):
    """Baixa página com espera explícita e tratamento de erros"""
    driver = None
    try:
        driver = criar_driver()
        log_debug(f"Acessando: {url[:70]}...")
        driver.get(url)
        
        # ✅ ESPERA INTELIGENTE: Espera o body + conteúdo dinâmico
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3) # Segurança extra para JS
        
        html = driver.page_source
        log_debug(f"✓ Página carregada: {len(html)} bytes")
        return html
    except Exception as e:
        log_debug(f"✗ Falha: {str(e)}")
        return ""
    finally:
        if driver:
            try: driver.quit()
            except: pass

def extrair_categorias(html_base):
    """Seletores ajustados para a estrutura real do site"""
    soup = BeautifulSoup(html_base, "html.parser")
    cats = []
    
    # 🔍 TENTA VÁRIOS SELETORES (compatibilidade total)
    seletores = [
        "a[href*='categorias']",
        ".category-item a",
        ".list-group-item",
        "div.card a",
        ".menu-item a",
        "a[class*='cat']"
    ]
    
    for sel in seletores:
        elementos = soup.select(sel)
        if elementos:
            log_debug(f"Encontrados {len(elementos)} categorias com seletor: {sel}")
            for el in elementos:
                nome = el.get_text(strip=True)
                href = el.get("href")
                if nome and href and not "javascript:" in href:
                    if not href.startswith("http"):
                        href = "https://app.pobreflix2.site" + href
                    cats.append({"nome": nome, "url": href})
            break
    return cats

def extrair_canais_da_categoria(html_cat):
    soup = BeautifulSoup(html_cat, "html.parser")
    canais = []
    
    seletores_canais = [
        "a[href*='canal']",
        ".channel-link",
        ".video-item a",
        ".card-body a",
        ".item-card a",
        "div.col a"
    ]
    
    for sel in seletores_canais:
        items = soup.select(sel)
        if items:
            log_debug(f"→ {len(items)} canais encontrados")
            for item in items:
                nome = item.get_text(strip=True)
                href = item.get("href")
                if not nome or not href or len(nome) < 2:
                    continue
                if not href.startswith("http"):
                    href = "https://app.pobreflix2.site" + href
                
                logo = ""
                img = item.find("img")
                if img:
                    logo = img.get("data-src") or img.get("src") or ""
                    if logo and not logo.startswith("http"):
                        logo = "https://app.pobreflix2.site" + logo
                canais.append({"nome": nome, "url": href, "logo": logo})
            break
    return canais

def buscar_link_stream(url_canal):
    html = pegar_conteudo_seguro(url_canal)
    if not html: return None
    
    # Padrões de busca de stream
    patterns = [
        r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        r'streamUrl\s*:\s*["\']([^"\']+)["\']',
        r'stream_url\s*[=:]\s*["\']([^"\']+)["\']',
        r'source\s*src=["\']([^"\']+)["\']',
        r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']'
    ]
    
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            link = m.group(1)
            if link:
                log_debug(f"✓ Stream encontrado: {link[:60]}...")
                return link
    return None

# 📱 ROTAS DA APLICAÇÃO
@app.route("/")
def home():
    return """
    <h1>🔧 Proxy Diagnóstico Pobreflix</h1>
    <ul>
        <li><a href='/teste-simples'>🔍 Teste de Leitura</a></li>
        <li><a href='/playlist.m3u'>📺 Playlist M3U</a></li>
        <li><a href='/epg.xml'>📅 EPG</a></li>
    </ul>
    <p>Verifique os logs do Render para detalhes de execução!</p>
    """

@app.route("/teste-simples")
def teste():
    res = []
    for srv in SERVERS:
        res.append(f"\n===== {srv['name']} =====")
        html = pegar_conteudo_seguro(srv["url"])
        if not html:
            res.append("❌ Não foi possível carregar")
            continue
        res.append(f"✅ HTML carregado: {len(html)} bytes")
        categorias = extrair_categorias(html)
        res.append(f"📁 Categorias: {len(categorias)}")
        for cat in categorias[:3]:
            res.append(f"  ↳ {cat['nome']}")
    return Response("\n".join(res), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3\n#EXT-IMPORTANT: A primeira carga demora"]
    total = 0

    for servidor in SERVERS:
        log_debug(f"\n=== PROCESSANDO {servidor['name']} ===")
        html_principal = pegar_conteudo_seguro(servidor["url"])
        if not html_principal:
            m3u.append(f"# ERRO: Falha ao ler {servidor['name']}")
            continue

        categorias = extrair_categorias(html_principal)
        if not categorias:
            m3u.append(f"# AVISO: Sem categorias em {servidor['name']}")
            continue

        for cat in categorias[:15]: # Limite segurança
            html_cat = pegar_conteudo_seguro(cat["url"])
            if not html_cat: continue
            
            canais = extrair_canais_da_categoria(html_cat)
            for ch in canais:
                m3u.append(
                    f'#EXTINF:-1 tvg-id="s{servidor["id"]}_{total}" '
                    f'tvg-logo="{ch["logo"]}" group-title="{cat["nome"].upper()} [{servidor["name"]}]",{ch["nome"]}'
                )
                m3u.append(f'{host}stream/{servidor["id"]}/{total}?u={ch["url"]}')
                total += 1

    if total == 0:
        m3u.append("\n# ❌ NENHUM CANAL ENCONTRADO")
        m3u.append("# Acesse /teste-simples para ver o que está acontecendo")
        m3u.append("# Verifique logs no Render")

    log_debug(f"✅ Playlist finalizada: {total} canais")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream_rotear(sid, cid):
    url_canal = request.args.get("u")
    if not url_canal:
        return "Parâmetro 'u' obrigatório", 400
    link_final = buscar_link_stream(url_canal)
    if link_final:
        return redirect(link_final)
    return "Link de stream não encontrado", 404

@app.route("/epg.xml")
def epg_vazio():
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><tv generator-info-name="ProxyPobreflix"/>',
        mimetype="application/xml"
    )

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)

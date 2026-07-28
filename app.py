from flask import Flask, Response, redirect, request
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re
import os
import time

app = Flask(__name__)

SERVERS = [
    {"id": 1, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-1", "name": "SPEED-1"},
    {"id": 2, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2", "name": "SPEED-2"},
    {"id": 3, "url": "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-3", "name": "SPEED-3"},
]

# 🔹 SESSÃO CAMUFLADA (COMO NAVEGADOR REAL)
ua = UserAgent()
SESS = requests.Session()
SESS.headers.update({
    "User-Agent": ua.random,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "TE": "trailers"
})

def pegar_html(url):
    """Tenta várias vezes, com delay e renovação de agente"""
    for tentativa in range(3):
        try:
            if tentativa > 0:
                time.sleep(2 + tentativa)
                SESS.headers["User-Agent"] = ua.random
            
            r = SESS.get(url, timeout=25, allow_redirects=True)
            r.raise_for_status()
            r.encoding = "utf-8"
            texto = r.text
            
            # 🚨 DETECÇÃO DE BLOQUEIO/JS OBRIGATÓRIO
            if len(texto) < 1000 or "Verificando" in texto or "Cloudflare" in texto or "captcha" in texto.lower():
                print(f"[BLOQUEIO] Tentativa {tentativa+1} - {url[:60]}")
                continue
                
            return texto
        except Exception as e:
            print(f"[ERRO {tentativa+1}] {url[:60]}: {str(e)}")
    return ""

def extrair_links(html):
    """Busca GENÉRICA por TODOS os links com conteúdo válido"""
    soup = BeautifulSoup(html, "html.parser")
    resultado = {"categorias": [], "canais": []}
    
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        nome = a.get_text(strip=True)
        
        if not nome or len(nome) < 2 or href.startswith("javascript"):
            continue
        if not href.startswith("http"):
            href = "https://app.pobreflix2.site" + href
            
        # CLASSIFICA
        if any(p in href.lower() for p in ["/categoria", "categorias", "cat="]):
            resultado["categorias"].append({"nome": nome, "url": href})
        elif any(p in href.lower() for p in ["/canal", "player", "id=", "ver"]):
            resultado["canais"].append({"nome": nome, "url": href})
    
    # REMOVE DUPLICATAS
    for tipo in resultado:
        vistos = set()
        resultado[tipo] = [x for x in resultado[tipo] if not (x["url"] in vistos or vistos.add(x["url"]))]
    return resultado

def achar_stream(url_canal):
    html = pegar_html(url_canal)
    if not html: return None
    padroes = [
        r'https?://[^"\']+\.m3u8[^"\']*',
        r'stream_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'streamUrl\s*:\s*["\']([^"\']+)["\']',
        r'source\s+src=["\']([^"\']+)["\']'
    ]
    for p in padroes:
        m = re.search(p, html, re.I)
        if m: return m.group(1) or m.group(0)
    return None

# 📱 ROTAS
@app.route("/")
def home():
    return "<h1>✅ Anti-Bloqueio Total</h1><p>Diagnóstico: <a href='/teste'>/teste</a></p><p>Playlist: <a href='/playlist.m3u'>/playlist.m3u</a></p>"

@app.route("/teste")
def teste():
    saida = []
    for srv in SERVERS:
        saida.append(f"\n===== {srv['name']} =====")
        html = pegar_html(srv["url"])
        if not html:
            saida.append("❌ BLOQUEADO ou OFFLINE")
            continue
        saida.append(f"✅ Página: {len(html)} caracteres")
        dados = extrair_links(html)
        saida.append(f"📁 Categorias: {len(dados['categorias'])}")
        for c in dados["categorias"][:4]: saida.append(f"   ↳ {c['nome']}")
        saida.append(f"📺 Canais diretos: {len(dados['canais'])}")
        for ch in dados["canais"][:4]: saida.append(f"   ↳ {ch['nome']}")
    return Response("\n".join(saida), mimetype="text/plain")

@app.route("/playlist.m3u")
def playlist():
    host = request.host_url
    m3u = ["#EXTM3U\n#EXT-X-VERSION:3"]
    total = 0
    for srv in SERVERS:
        html = pegar_html(srv["url"])
        if not html:
            m3u.append(f"# ❌ {srv['name']}: Bloqueado")
            continue
        dados = extrair_links(html)
        
        # Tenta por categorias
        if dados["categorias"]:
            for cat in dados["categorias"][:10]:
                hcat = pegar_html(cat["url"])
                if not hcat: continue
                canais_cat = extrair_links(hcat)["canais"]
                for ch in canais_cat:
                    m3u.append(f'#EXTINF:-1 group-title="{cat["nome"]} | {srv["name"]}",{ch["nome"]}')
                    m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                    total += 1
        # Se não, usa canais diretos
        elif dados["canais"]:
            for ch in dados["canais"]:
                m3u.append(f'#EXTINF:-1 group-title="Direto {srv["name"]}",{ch["nome"]}')
                m3u.append(f"{host}stream/{srv['id']}/{total}?u={ch['url']}")
                total += 1
    if total == 0:
        m3u.append("\n# ❌ Nenhum canal extraído — site bloqueou requisições")
    return Response("\n".join(m3u), mimetype="application/vnd.apple.mpegurl")

@app.route("/stream/<int:sid>/<path:cid>")
def stream(sid, cid):
    u = request.args.get("u")
    if not u: return "URL inválida", 400
    link = achar_stream(u)
    return redirect(link) if link else "Stream não encontrada", 404

@app.route("/epg.xml")
def epg():
    return Response('<?xml version="1.0"?><tv></tv>', mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

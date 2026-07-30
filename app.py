import requests
import re
from bs4 import BeautifulSoup
from flask import Flask, Response, request
import os
import time

app = Flask(__name__)

# Domínios extraídos das suas informações
TARGET_DOMAIN = "https://ycineflix.tudo30.shop"
VIDEO_BASE = "https://speed.megafilmeshd9.com/midia"

# Headers de navegador real (Chrome no Windows) para evitar detecção de robô
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Connection": "keep-alive"
}

def get_channels_smart(sid):
    """Obtém os canais simulando uma sessão de usuário real com cookies."""
    channels = []
    # Usamos uma sessão para manter os cookies ativos durante a navegação
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # 1. Visita a página inicial para ganhar os cookies de segurança (Bypass Cloudflare/WAF)
        session.get(f"{TARGET_DOMAIN}/", timeout=10)
        
        # 2. Acessa a página específica de canais do servidor solicitado
        url = f"{TARGET_DOMAIN}/canais/?thema=1&server=speed-{sid}"
        res = session.get(url, timeout=20)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Busca todos os links de canais no código-fonte
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                # Procura o padrão de ID de canal no link (/canais/NUMERO/)
                if '/canais/' in href:
                    cid_match = re.search(r'/canais/(\d+)/', href)
                    if cid_match:
                        cid = cid_match.group(1)
                        # Nome do canal (limpa o prefixo 'Assistir')
                        name = link.get('title') or link.text.strip() or f"Canal {cid}"
                        name = name.replace("Assistir ", "").strip()
                        # Logo do canal
                        img = link.find('img')
                        logo = img['src'] if img and img.has_attr('src') else ""
                        
                        channels.append({
                            "id": cid,
                            "name": name,
                            "logo": logo
                        })
    except Exception as e:
        print(f"Erro ao ler Servidor {sid}: {e}")
        
    return channels

@app.route("/")
def index():
    return f"<h1>SpeedFlix Proxy Ativo</h1><p>Link M3U: {request.host_url}playlist.m3u</p>"

@app.route("/playlist.m3u")
def playlist():
    """Gera a playlist M3U unificada com identificação de servidor [S1, S2, S3]."""
    m3u = ["#EXTM3U"]
    host = request.host_url
    
    # Sufixo para o TiviMate enviar os cabeçalhos corretos ao servidor de vídeo
    # Isso evita que o vídeo fique reconectando ou dê erro de acesso
    suffix = f"|User-Agent={HEADERS['User-Agent']}&Referer={TARGET_DOMAIN}/"

    total = 0
    # Percorre os servidores 1, 2 e 3 conforme solicitado
    for sid in [1, 2, 3]:
        canals = get_channels_smart(sid)
        for ch in canals:
            # Nome e Grupo identificados pelo Servidor
            name = f"{ch['name']} [S{sid}]"
            group = f"CANAIS [S{sid}]"
            
            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{ch["id"]}" tvg-logo="{ch["logo"]}" group-title="{group}",{name}')
            # Link direto para o arquivo .m3u8 no servidor de vídeo (descoberto no HTML)
            m3u.append(f"{VIDEO_BASE}/speed-{sid}/{ch['id']}.m3u8{suffix}")
            total += 1

    # Mensagem de erro caso o IP do Railway seja bloqueado pelo site
    if total == 0:
        m3u.append("# ERRO: Bloqueio de Firewall detectado.")
        m3u.append("# O servidor SpeedFlix nao permitiu que o Railway lesse a lista.")

    return Response("\n".join(m3u), mimetype="text/plain")

if __name__ == "__main__":
    # Railway utiliza a porta 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

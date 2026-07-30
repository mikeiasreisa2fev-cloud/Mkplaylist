import requests
import json
import uuid
import time
import re

def fetch_via_proxy(url):
    """Busca dados usando o proxy AllOrigins para esconder o IP do GitHub."""
    proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(url)}"
    try:
        r = requests.get(proxy_url, timeout=30)
        if r.status_code == 200:
            # O AllOrigins retorna o conteúdo original dentro da chave 'contents'
            content = r.json().get('contents')
            return json.loads(content)
    except Exception as e:
        print(f"Erro no Proxy ao acessar {url}: {e}")
    return None

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínio principal da API
    BASE_API = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
    
    device_id = str(uuid.uuid4()).replace('-', '')[:16]

    print("--- Iniciando Captura via Proxy ---")
    
    # 1. Login de Convidado para obter o Token
    print("Tentando realizar login via Proxy...")
    login_url = f"{BASE_API}/auth/login?username=guest_{device_id[:6]}&password=guest&device_id={device_id}"
    data_login = fetch_via_proxy(login_url)
    
    token = None
    if data_login:
        token = data_login.get("data", {}).get("token") or data_login.get("token")
        print("Login realizado com sucesso via Proxy!")
    else:
        print("Aviso: Falha no login via Proxy, tentando buscar canais sem token...")

    total_geral = 0
    # 2. Percorrer os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"Buscando canais do Servidor {sid}...")
        # Pedimos 500 canais para pegar tudo de uma vez
        chan_url = f"{BASE_API}/channels?server_id={sid}&per_page=500"
        if token:
            chan_url += f"&Authorization=Bearer {token}"
            
        data_chans = fetch_via_proxy(chan_url)
        
        if data_chans:
            items = data_chans.get("data", {}).get("items") or data_chans.get("items") or []
            if items:
                print(f"Sucesso! Encontrados {len(items)} canais no Servidor {sid}")
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    # Identificação clara [S1], [S2] ou [S3]
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or f'SERVIDOR {sid}').upper()
                    logo = ch.get("image") or ""
                    
                    # Monta a linha do canal na lista M3U
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                    # Link direto para o vídeo m3u8 que descobrimos ser o mais estável
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                    total_geral += 1
            else:
                print(f"Servidor {sid} retornou lista vazia através do Proxy.")
        else:
            print(f"Falha ao conectar no servidor {sid} via Proxy.")

    # 3. Salvar o arquivo final
    if total_geral > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"--- SUCESSO: {total_geral} canais salvos em playlist.m3u ---")
    else:
        print("ERRO CRÍTICO: Nenhum canal capturado.")
        # Cria um arquivo com erro para facilitar o diagnóstico
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n# ERRO: O Proxy não conseguiu capturar os canais.\n# Verifique o log das Actions no GitHub.")

if __name__ == "__main__":
    get_channels()

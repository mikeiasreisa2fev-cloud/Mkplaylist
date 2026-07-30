import requests
import uuid
import time
import json

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínio que você forneceu que contém os servidores
    BASE_URL = "https://ycineflix.tudo30.shop"
    API_PATH = "/wp-json/xui-pflix/v1"
    
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    
    headers_base = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json",
        "Connection": "Keep-Alive"
    }

    session = requests.Session()
    session.headers.update(headers_base)

    print(f"Iniciando captura via {BASE_URL}...")
    
    token = None
    try:
        # 1. Configuração inicial (limpa o cache do servidor)
        session.get(f"{BASE_URL}{API_PATH}/app/config", timeout=10)
        
        # 2. Login de Convidado via rest_route (Bypass)
        login_params = {"rest_route": "/xui-pflix/v1/auth/login"}
        payload = {
            "username": f"guest_{device_id[:8]}",
            "password": "guest",
            "device_id": device_id,
            "model": "Samsung SM-G998B",
            "version": "13"
        }
        
        r_login = session.post(f"{BASE_URL}/", params=login_params, json=payload, timeout=10)
        if r_login.status_code == 200:
            data = r_login.json()
            token = data.get("data", {}).get("token") or data.get("token")
            print("Login de Convidado: SUCESSO")
    except Exception as e:
        print(f"Falha no login: {e}")

    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})

    total_canais = 0
    # 3. Pega os canais dos servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        page = 1
        while page <= 10: # Busca até 1000 canais por servidor
            try:
                params = {
                    "rest_route": "/xui-pflix/v1/channels",
                    "server_id": sid,
                    "per_page": 100,
                    "page": page
                }
                r = session.get(f"{BASE_URL}/", params=params, timeout=15)
                
                if r.status_code != 200: break
                
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items: break
                
                print(f"S{sid} Pagina {page}: {len(items)} canais encontrados.")
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or f'SERVIDOR {sid}').upper()
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                    # LINK PARA O SEU RAILWAY
                    m3u.append(f"https://mkplaylist-production.up.railway.app/stream/{sid}/{cid}")
                    total_canais += 1
                
                # Checa se tem mais páginas
                meta = data.get("data", {}).get("meta") or data.get("meta") or {}
                if page >= int(meta.get("total_pages", 1)): break
                page += 1
                time.sleep(0.5)
            except: break

    if total_canais == 0:
        m3u.append("# ERRO: Servidor bloqueou a captura no GitHub.")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    print(f"Fim do processo! {total_canais} canais guardados no repositório.")

if __name__ == "__main__":
    get_channels()

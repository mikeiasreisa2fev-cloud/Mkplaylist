import requests
import uuid
import time

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínios ativos para tentar
    DOMAINS = ["https://app.pobreflix2.site", "https://ycineflix.tudo30.shop"]
    # URL DO SEU RAILWAY (Para os links de stream)
    RAILWAY_URL = "https://mkplaylist-production.up.railway.app"
    
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    headers_base = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json"
    }

    session = requests.Session()
    session.headers.update(headers_base)

    total_canais = 0
    
    for base in DOMAINS:
        print(f"Tentando captura via {base}...")
        try:
            # 1. 'Visita' a home para ganhar Cookies
            session.get(f"{base}/", timeout=10)
            
            # 2. Login de Convidado via rest_route
            login_url = f"{base}/"
            login_params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {
                "username": f"guest_{device_id[:6]}",
                "password": "guest",
                "device_id": device_id
            }
            
            r_login = session.post(login_url, params=login_params, json=payload, timeout=10)
            token = None
            if r_login.status_code == 200:
                token = r_login.json().get("data", {}).get("token") or r_login.json().get("token")
                print("Login: SUCESSO")
            
            if token:
                session.headers.update({"Authorization": f"Bearer {token}"})

            # 3. Pega os canais dos servidores 1, 2 e 3
            for sid in [1, 2, 3]:
                # Usamos o modo 'sync' que retorna tudo de uma vez
                params = {"rest_route": "/xui-pflix/v1/channels", "server_id": sid, "per_page": 500}
                r = session.get(f"{base}/", params=params, timeout=15)
                
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("data", {}).get("items") or data.get("items") or []
                    print(f"S{sid}: {len(items)} canais encontrados.")
                    
                    for ch in items:
                        cid = ch.get("id")
                        if not cid: continue
                        name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                        cat = (ch.get('category_name') or f'SERVIDOR {sid}').upper()
                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{cat} [S{sid}]",{name}')
                        m3u.append(f"{RAILWAY_URL}/stream/{sid}/{cid}")
                        total_canais += 1
            
            if total_canais > 0: break # Se conseguiu em um domínio, não precisa tentar o outro
            
        except Exception as e:
            print(f"Erro em {base}: {e}")
            continue

    if total_canais == 0:
        m3u.append("# ERRO: Servidor bloqueou a captura no GitHub.")
    
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Fim! {total_canais} canais salvos.")

if __name__ == "__main__":
    get_channels()

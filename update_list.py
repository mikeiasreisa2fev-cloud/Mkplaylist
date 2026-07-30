import requests
import uuid
import json
import time

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínios para tentativa (prioridade para o que você forneceu)
    DOMAINS = ["https://ycineflix.tudo30.shop", "https://app.pobreflix2.site"]
    # URL DO SEU RAILWAY (Verifique se este é o link correto no seu painel Railway)
    RAILWAY_URL = "https://mkplaylist-production.up.railway.app"
    
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    headers_base = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json"
    }

    total_geral = 0
    
    for base_url in DOMAINS:
        print(f"Tentando capturar via: {base_url}")
        token = None
        try:
            # 1. Login de Convidado via rest_route (Bypass)
            login_url = f"{base_url}/"
            login_params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {"username": f"guest_{device_id[:6]}", "password": "guest", "device_id": device_id}
            
            r_login = requests.post(login_url, params=login_params, json=payload, headers=headers_base, timeout=15)
            if r_login.status_code == 200:
                data = r_login.json()
                token = data.get("data", {}).get("token") or data.get("token")
                print(f"Login em {base_url}: SUCESSO")
        except:
            print(f"Login em {base_url}: FALHA")

        # 2. Busca os canais (Servidores 1, 2 e 3)
        for sid in [1, 2, 3]:
            try:
                headers = headers_base.copy()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                
                # Técnica rest_route para burlar bloqueio
                params = {
                    "rest_route": "/xui-pflix/v1/channels",
                    "server_id": sid,
                    "per_page": 400 # Tenta pegar tudo de uma vez
                }
                
                r = requests.get(f"{base_url}/", params=params, headers=headers, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("data", {}).get("items") or data.get("items") or []
                    
                    if items:
                        print(f"Servidor {sid}: Encontrados {len(items)} canais.")
                        for ch in items:
                            cid = ch.get("id")
                            if not cid: continue
                            
                            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                            cat = (ch.get('category_name') or f'Servidor {sid}').upper()
                            group = f"{cat} [S{sid}]"
                            logo = ch.get("image") or ""
                            
                            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                            m3u.append(f"{RAILWAY_URL}/stream/{sid}/{cid}")
                            total_geral += 1
                    else:
                        print(f"Servidor {sid}: Retornou lista vazia.")
            except Exception as e:
                print(f"Erro no servidor {sid}: {e}")
        
        # Se conseguiu capturar canais em um domínio, não precisa tentar o próximo
        if total_geral > 0:
            break

    # Se falhou tudo, coloca o backup para a lista não ficar vazia
    if total_geral == 0:
        print("ERRO: Nenhum canal capturado em nenhum domínio.")
        m3u.append('#EXTINF:-1 tvg-id="s1_11892477",Globo AC FHD [S1]')
        m3u.append(f"{RAILWAY_URL}/stream/1/11892477")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Fim do processo! {total_geral} canais salvos.")

if __name__ == "__main__":
    get_channels()

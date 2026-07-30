import requests
import json
import uuid

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínios para tentativa
    base_url = "https://app.pobreflix2.site"
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    
    headers = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json"
    }

    print("Tentando obter Token de acesso...")
    token = None
    try:
        login_url = f"{base_url}/?rest_route=/xui-pflix/v1/auth/login"
        payload = {"username": f"guest_{device_id[:8]}", "password": "guest", "device_id": device_id}
        r_login = requests.post(login_url, json=payload, headers=headers, timeout=15)
        if r_login.status_code == 200:
            token = r_login.json().get("data", {}).get("token") or r_login.json().get("token")
            print("Token obtido com sucesso!")
    except Exception as e:
        print(f"Falha no login: {e}")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    total_geral = 0
    for sid in [1, 2, 3]:
        print(f"Buscando canais do Servidor {sid}...")
        try:
            # Bypass usando rest_route
            api_url = f"{base_url}/"
            params = {
                "rest_route": "/xui-pflix/v1/channels",
                "server_id": sid,
                "per_page": 400
            }
            
            r = requests.get(api_url, params=params, headers=headers, timeout=20)
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                
                print(f"Encontrados {len(items)} canais no servidor {sid}")
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    # Padronização de nomes conforme solicitado
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or f'Servidor {sid}').upper()
                    group = f"{cat} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    # Link redirecionado pelo seu app no Railway
                    m3u.append(f"https://mkplaylist-production.up.railway.app/stream/{sid}/{cid}")
                    total_geral += 1
            else:
                print(f"Servidor {sid} retornou erro {r.status_code}")
        except Exception as e:
            print(f"Erro ao processar servidor {sid}: {e}")

    if total_geral == 0:
        print("AVISO: Nenhum canal foi encontrado em nenhum servidor.")
        m3u.append("# ERRO: O servidor SpeedFlix recusou a conexao do GitHub.")
    
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Processo finalizado. Total de canais salvos: {total_geral}")

if __name__ == "__main__":
    get_channels()

import requests
import uuid
import json
import time

def get_channels():
    m3u = ["#EXTM3U"]
    base_api = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    
    headers = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json"
    }

    print("Tentando realizar login...")
    token = None
    try:
        login_url = f"{base_api}/auth/login"
        payload = {"username": f"guest_{device_id[:6]}", "password": "guest", "device_id": device_id}
        r = requests.post(login_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            token = r.json().get("data", {}).get("token") or r.json().get("token")
            print("Login realizado com sucesso!")
    except Exception as e:
        print(f"Erro no login: {e}")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    total_geral = 0
    for sid in [1, 2, 3]:
        print(f"Buscando canais do Servidor {sid}...")
        try:
            url = f"{base_api}/channels"
            params = {"server_id": sid, "per_page": 500}
            res = requests.get(url, params=params, headers=headers, timeout=25)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                print(f"Sucesso! Encontrados {len(items)} canais no S{sid}")
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or f'Servidor {sid}').upper()
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{cat} [S{sid}]",{name}')
                    # LINK PARA O SEU RAILWAY (Ajuste o link abaixo se o seu for diferente)
                    m3u.append(f"https://mkplaylist-production.up.railway.app/stream/{sid}/{cid}")
                    total_geral += 1
            else:
                print(f"Erro {res.status_code} no servidor {sid}")
        except Exception as e:
            print(f"Falha no servidor {sid}: {e}")

    if total_geral > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"Fim! {total_geral} canais salvos.")
    else:
        print("Erro: Nenhum canal capturado.")

if __name__ == "__main__":
    get_channels()

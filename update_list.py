import requests
import uuid
import json
import time
import random

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínios para tentativa
    DOMAINS = ["https://app.pobreflix2.site", "https://ycineflix.tudo30.shop"]
    
    # Gerar um IP brasileiro falso para enganar o firewall
    fake_ip = f"{random.choice([177, 179, 186, 187, 189, 191, 200, 201])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    headers_base = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "X-Forwarded-For": fake_ip,
        "Accept": "application/json"
    }

    session = requests.Session()
    session.headers.update(headers_base)

    total_geral = 0
    
    for base in DOMAINS:
        print(f"Tentando capturar via {base}...")
        token = None
        try:
            # 1. Login de Convidado via rest_route (Bypass de Firewall)
            login_url = f"{base}/"
            login_params = {"rest_route": "/xui-pflix/v1/auth/login"}
            payload = {"username": f"guest_{device_id[:6]}", "password": "guest", "device_id": device_id}
            
            r_login = session.post(login_url, params=login_params, json=payload, timeout=15)
            if r_login.status_code == 200:
                token = r_login.json().get("data", {}).get("token") or r_login.json().get("token")
                print("Login realizado com sucesso!")
        except: pass

        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})

        # 2. Busca os canais (Servidores 1, 2 e 3)
        for sid in [1, 2, 3]:
            try:
                # Técnica rest_route para canais
                params = {"rest_route": "/xui-pflix/v1/channels", "server_id": sid, "per_page": 500}
                r = session.get(f"{base}/", params=params, timeout=20)
                
                if r.status_code == 200:
                    data = r.json()
                    items = data.get("data", {}).get("items") or data.get("items") or []
                    
                    if items:
                        print(f"S{sid}: Encontrados {len(items)} canais.")
                        for ch in items:
                            cid = ch.get("id")
                            if not cid: continue
                            
                            name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                            cat = (ch.get('category_name') or f'SERVIDOR {sid}').upper()
                            logo = ch.get("image") or ""
                            
                            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                            # Link direto conforme as imagens que você mandou
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                            total_geral += 1
            except: continue
        
        if total_geral > 0: break # Se conseguiu em um portal, não tenta o próximo

    # 3. Salva a lista
    if total_geral > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"Sucesso! {total_geral} canais salvos.")
    else:
        print("Erro: Nenhum canal capturado.")
        # Cria um arquivo com erro para você ver no Railway
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n# ERRO: O servidor do SpeedFlix bloqueou o GitHub.\n# Verifique o log das Actions.")

if __name__ == "__main__":
    get_channels()

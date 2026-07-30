import requests
import uuid
import json
import time

def get_channels_from_app():
    m3u = ["#EXTM3U"]
    # Domínio principal que fornece os dados para o aplicativo
    BASE_API = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
    
    # Simulação de um dispositivo Android real
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    headers = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json"
    }

    print("--- Autenticando no Aplicativo SpeedFlix ---")
    token = None
    try:
        # Faz o 'Login de Convidado' para abrir a porta do servidor
        login_url = f"{BASE_API}/auth/login"
        payload = {
            "username": f"guest_{device_id[:6]}", 
            "password": "guest", 
            "device_id": device_id
        }
        r = requests.post(login_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            token = r.json().get("data", {}).get("token") or r.json().get("token")
            print("Autenticação realizada com sucesso!")
    except:
        print("Aviso: Falha no login, tentando captura direta...")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    total_canais = 0
    # Servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"Buscando Banco de Dados do Servidor {sid}...")
        
        # Pedimos 500 canais por servidor (para pegar os 176, 192 e 127 de uma vez)
        url = f"{BASE_API}/channels"
        params = {"server_id": sid, "per_page": 500}
        
        try:
            res = requests.get(url, params=params, headers=headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                # O XUI pode retornar em 'items' ou 'data.items'
                items = data.get("data", {}).get("items") or data.get("items") or []
                
                if items:
                    print(f"Sucesso! {len(items)} canais capturados no S{sid}")
                    for ch in items:
                        cid = ch.get("id")
                        if not cid: continue
                        
                        # Nome, Categoria e Logo extraídos diretamente do app
                        name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                        cat = (ch.get('category_name') or 'CANAIS').upper()
                        logo = ch.get("image") or ""
                        
                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{cat} [S{sid}]",{name}')
                        # Link direto para o vídeo m3u8 (o mais estável)
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        total_canais += 1
                else:
                    print(f"Aviso: Servidor {sid} retornou lista vazia.")
            else:
                print(f"Erro {res.status_code} no Servidor {sid}")
        except Exception as e:
            print(f"Falha de conexão no S{sid}: {e}")

    # Salva o arquivo M3U no seu repositório
    if total_canais > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"--- PLAYLIST GERADA: {total_canais} canais salvos ---")
    else:
        print("ERRO: Não foi possível capturar os canais do app.")

if __name__ == "__main__":
    get_channels_from_app()

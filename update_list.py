import requests
import uuid
import json
import time

def get_channels():
    # Início da lista M3U
    m3u = ["#EXTM3U"]

    # Domínio do portal que agrupa os servidores
    BASE_URL = "https://ycineflix.tudo30.shop"
    API_PATH = "/wp-json/xui-pflix/v1"

    # Identificação única para simular um dispositivo Android
    device_id = str(uuid.uuid4()).replace('-', '')[:16]

    headers = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json",
        "Connection": "Keep-Alive"
    }

    print(f"--- Iniciando Captura via {BASE_URL} ---")

    # 1. Realizar Login de Convidado para obter o Token Bearer
    print("Solicitando Token de acesso...")
    token = None
    try:
        # O app costuma chamar o config antes do login
        requests.get(f"{BASE_URL}{API_PATH}/app/config", headers=headers, timeout=10)

        login_url = f"{BASE_URL}{API_PATH}/auth/login"
        payload = {
            "username": f"guest_{device_id[:6]}",
            "password": "guest",
            "device_id": device_id,
            "model": "Samsung SM-G998B",
            "version": "13"
        }
        r = requests.post(login_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            token = data.get("data", {}).get("token") or data.get("token")
            print("Token obtido com sucesso!")
    except Exception as e:
        print(f"Erro no login: {e}")

    # Se conseguimos o token, adicionamos aos cabeçalhos de autorização
    if token:
        headers["Authorization"] = f"Bearer {token}"

    total_geral = 0

    # 2. Percorrer os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"Buscando canais do Servidor {sid}...")
        try:
            # Pedimos 500 canais por servidor para capturar todos de uma vez
            url = f"{BASE_URL}{API_PATH}/channels"
            params = {"server_id": sid, "per_page": 500}

            res = requests.get(url, params=params, headers=headers, timeout=25)

            if res.status_code == 200:
                data = res.json()
                # A API pode retornar os itens em 'data.items' ou 'items'
                items = data.get("data", {}).get("items") or data.get("items") or []

                print(f"S{sid}: Encontrados {len(items)} canais.")

                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue

                    # Nome do canal e Grupo identificados pelo servidor (ex: [S1])
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or f'Servidor {sid}').upper()
                    group = f"{cat} [S{sid}]"
                    logo = ch.get("image") or ""

                    # Monta a entrada na Playlist M3U
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    # Link direto para o vídeo (conforme descoberto no seu código-fonte)
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")

                    total_geral += 1
            else:
                print(f"Erro {res.status_code} no servidor {sid}")
        except Exception as e:
            print(f"Falha de conexão no S{sid}: {e}")

    # 3. Salvar o arquivo final no repositório
    if total_geral > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"--- SUCESSO: {total_geral} canais salvos no arquivo playlist.m3u ---")
    else:
        print("ERRO: Nenhum canal capturado. Verifique se o portal está online.")

if __name__ == "__main__":
    get_channels()

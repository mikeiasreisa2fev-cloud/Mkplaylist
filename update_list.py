import requests
import uuid
import json
import time

def get_channels():
    # Início da lista M3U
    m3u = ["#EXTM3U"]
    
    # Domínio principal da API
    base_api = "https://app.pobreflix2.site/wp-json/xui-pflix/v1"
    
    # Identificação única para este "dispositivo" simulado
    device_id = str(uuid.uuid4()).replace('-', '')[:16]
    
    headers = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "Accept": "application/json"
    }

    print("--- Iniciando Processo de Captura ---")
    
    # 1. Realizar Login de Convidado para liberar o acesso
    print("Solicitando Token de acesso...")
    token = None
    try:
        login_url = f"{base_api}/auth/login"
        payload = {
            "username": f"guest_{device_id[:6]}", 
            "password": "guest", 
            "device_id": device_id
        }
        r = requests.post(login_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            token = data.get("data", {}).get("token") or data.get("token")
            print("Token obtido com sucesso!")
    except Exception as e:
        print(f"Erro no login: {e}")

    # Se conseguimos o token, adicionamos aos cabeçalhos
    if token:
        headers["Authorization"] = f"Bearer {token}"

    total_geral = 0

    # 2. Percorrer os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"Buscando canais do Servidor {sid}...")
        try:
            # Pedimos 500 canais por servidor (para pegar os 176, 192 e 127 de uma vez)
            url = f"{base_api}/channels"
            params = {"server_id": sid, "per_page": 500}
            
            res = requests.get(url, params=params, headers=headers, timeout=25)
            
            if res.status_code == 200:
                data = res.json()
                # A API pode retornar os itens em 'items' ou 'data.items'
                items = data.get("data", {}).get("items") or data.get("items") or []
                
                print(f"Sucesso! {len(items)} canais encontrados no Servidor {sid}")
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    
                    # Nome do canal e Grupo com identificação do servidor
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = (ch.get('category_name') or f'Servidor {sid}').upper()
                    group = f"{cat} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    # Monta a entrada do canal na lista M3U
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    # Link direto do servidor de vídeo oficial que funciona no TiviMate
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                    
                    total_geral += 1
            else:
                print(f"Erro {res.status_code} no servidor {sid}")
        except Exception as e:
            print(f"Falha ao conectar no servidor {sid}: {e}")

    # 3. Salvar o resultado final
    if total_geral > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"--- Fim! {total_geral} canais salvos no arquivo playlist.m3u ---")
    else:
        # Se falhou tudo, não sobrescreve o arquivo para não perder o que já tinha
        print("ERRO CRITICO: Nenhum canal capturado. Verifique o log acima.")

if __name__ == "__main__":
    get_channels()

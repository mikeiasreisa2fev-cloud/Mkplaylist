import requests
import re
import os

def get_channels():
    m3u = ["#EXTM3U"]
    
    # Headers para simular um navegador real e evitar bloqueio de leitura
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_geral = 0
    
    # Servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"--- ANALISANDO SERVIDOR {sid} ---")
        
        # Link da listagem completa de canais que você forneceu
        url = f"https://app.pobreflix2.site/canais/?thema=1&server=speed-{sid}"
        
        try:
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                html = res.text
                
                # BUSCA PELO PADRÃO QUE VOCÊ PASSOU:
                # Procura o ID (número) entre '/canais/' e o fechamento do link
                # E captura o nome que vem logo após a tag de fechamento ou em um title
                matches = re.findall(r'/canais/(\d+).*?>(.*?)<', html, re.DOTALL)
                
                if matches:
                    seen_ids = set()
                    for cid, name_raw in matches:
                        # Filtra apenas IDs válidos (geralmente acima de 5 dígitos)
                        if cid in seen_ids or not (5 <= len(cid) <= 9):
                            continue
                        
                        seen_ids.add(cid)
                        
                        # Limpeza do nome do canal
                        name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                        if len(name) < 2: name = f"Canal {cid}"
                        
                        # Monta a entrada M3U usando o modelo de link que você confirmou
                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                        # MODELO CONFIRMADO: https://speed.megafilmeshd9.com/midia/speed-X/ID.m3u8
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        total_geral += 1
                        
                    print(f"Sucesso: {len(seen_ids)} canais encontrados no S{sid}")
                else:
                    print(f"Aviso: HTML lido, mas nenhum ID de canal detectado no S{sid}")
            else:
                print(f"Erro {res.status_code} ao acessar servidor {sid}")
        except Exception as e:
            print(f"Falha técnica no servidor {sid}: {e}")

    # Salva o arquivo final no repositório
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    print(f"Finalizado! {total_geral} canais salvos no arquivo playlist.m3u")

if __name__ == "__main__":
    get_channels()

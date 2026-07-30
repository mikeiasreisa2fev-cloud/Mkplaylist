import requests
import re
import time

def get_channels():
    m3u = ["#EXTM3U"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_geral = 0
    # Servidores Speed 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"Iniciando busca no Servidor {sid}...")
        
        # WordPress costuma mostrar 20 canais por página. Vamos varrer até a página 10.
        for page in range(1, 11):
            # Formato da URL com paginação
            url = f"https://app.pobreflix2.site/canais/page/{page}/?thema=1&server=speed-{sid}"
            print(f"Lendo {url}...")
            
            try:
                res = requests.get(url, headers=headers, timeout=25)
                if res.status_code != 200:
                    print(f"Fim das páginas para S{sid} (Status {res.status_code})")
                    break
                
                html = res.text
                # Regex ultra-robusto para pegar ID e Nome baseado no seu HTML
                # Procura o ID dentro do link e o nome dentro da classe 'iptv-card-title'
                matches = re.findall(r'canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html, re.DOTALL)
                
                if not matches:
                    print(f"Nenhum canal encontrado na página {page}.")
                    break
                
                print(f"Sucesso! {len(matches)} canais encontrados na página {page}.")
                
                for cid, name_raw in matches:
                    # Limpeza do nome (remove tags HTML e texto 'Assistir')
                    name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                    uid = f"s{sid}_{cid}"
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="{uid}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                    # Link direto do vídeo descoberto no seu código-fonte
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                    total_geral += 1
                
                # Se a página veio com poucos canais, provavelmente é a última do servidor
                if len(matches) < 5:
                    break
                    
                time.sleep(1) # Pausa de segurança
            except Exception as e:
                print(f"Erro ao ler página {page}: {e}")
                break

    # Salva o arquivo final no repositório
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"PROCESSO FINALIZADO: {total_geral} canais salvos.")

if __name__ == "__main__":
    get_channels()

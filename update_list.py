import requests
import re
import time

def get_channels():
    m3u = ["#EXTM3U"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_geral = 0
    
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"--- Iniciando Varredura no Servidor {sid} ---")
        
        # O site costuma ter paginação. Vamos tentar ler até 10 páginas por servidor.
        for page in range(1, 11):
            url = f"https://app.pobreflix2.site/canais/page/{page}/?thema=1&server=speed-{sid}"
            print(f"Lendo Página {page}: {url}")
            
            try:
                res = requests.get(url, headers=headers, timeout=25)
                if res.status_code != 200:
                    print(f"Fim das páginas para o Servidor {sid} (Status {res.status_code})")
                    break
                
                html = res.text
                
                # Regex robusto para pegar ID e Nome baseado no seu HTML
                # Procura: /canais/ID/ e o texto dentro de iptv-card-title
                items = re.findall(r'/canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html, re.DOTALL)
                
                if not items:
                    # Tenta um padrão secundário se o site mudar
                    items = re.findall(r'href=".*?/canais/(\d+)/".*?alt="(.*?)"', html, re.DOTALL)

                if items:
                    count_page = 0
                    for cid, name_raw in items:
                        # Limpeza do nome
                        name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                        if not name: continue
                        
                        # Adiciona identificação [S1], [S2] ou [S3] no nome e no grupo
                        display_name = f"{name} [S{sid}]"
                        group_name = f"CANAIS [S{sid}]"
                        
                        # Tenta pegar a logo
                        logo_match = re.search(fr'canais/{cid}/.*?src="(.*?)"', html)
                        logo = logo_match.group(1) if logo_match else ""

                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group_name}",{display_name}')
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        count_page += 1
                        total_geral += 1
                    
                    print(f"Página {page}: {count_page} canais encontrados.")
                    if count_page < 10: # Se a página tem poucos canais, provavelmente é a última
                        break
                else:
                    print(f"Nenhum canal encontrado na página {page}.")
                    break
                    
                time.sleep(1) # Pausa para o servidor não nos bloquear
            except Exception as e:
                print(f"Erro na página {page}: {e}")
                break

    # Se a lista falhar, coloca o backup para não ficar vazia
    if total_geral == 0:
        m3u.append('#EXTINF:-1 tvg-id="s1_11892477",Globo AC FHD [S1]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-1/11892477.m3u8")

    # Salva o arquivo final
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"--- VARREDURA FINALIZADA: {total_geral} canais salvos ---")

if __name__ == "__main__":
    get_channels()

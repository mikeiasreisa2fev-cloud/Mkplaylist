import requests
import re
import time

def get_channels():
    m3u = ["#EXTM3U"]
    base_url = "https://app.pobreflix2.site"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": base_url
    }

    session = requests.Session()
    session.headers.update(headers)

    total_geral = 0
    # Focando no Servidor 2 como você pediu
    sid = "speed-2"
    print(f"--- Iniciando Varredura no Servidor {sid} ---")
    
    # Link das categorias que você forneceu
    cat_url = f"{base_url}/canais/categorias/?thema=1&server={sid}"
    
    try:
        res_cat = session.get(cat_url, timeout=20)
        if res_cat.status_code == 200:
            html_cat = res_cat.text
            
            # 1. 'CAÇA' os links de cada categoria (ex: Globo, Esportes)
            # Procura por: /canais/categorias/ID
            cat_ids = re.findall(r'/canais/categorias/(\d+)', html_cat)
            cat_ids = list(set(cat_ids)) # Remove duplicados
            
            print(f"Encontradas {len(cat_ids)} categorias. Lendo canais...")

            for cid_cat in cat_ids:
                # Monta o link da categoria específica
                url_final_cat = f"{base_url}/canais/categorias/{cid_cat}/?thema=1&server={sid}"
                
                try:
                    res_ch = session.get(url_final_cat, timeout=15)
                    if res_ch.status_code == 200:
                        html_ch = res_ch.text
                        
                        # 2. 'CAÇA' os canais dentro da categoria
                        # Procura por: /canais/ID e o Nome dentro do <h4>
                        chans = re.findall(r'/canais/(\d+)/.*?<h4>(.*?)</h4>', html_ch, re.DOTALL)
                        
                        if not chans:
                            # Tenta padrão alternativo (iptv-card-title)
                            chans = re.findall(r'/canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html_ch, re.DOTALL)

                        for ch_id, ch_name in chans:
                            # Limpeza de texto
                            clean_name = re.sub('<[^<]+?>', '', ch_name).replace("Assistir ", "").strip()
                            
                            m3u.append(f'#EXTINF:-1 tvg-id="s2_{ch_id}" group-title="CANAIS [S2]",{clean_name} [S2]')
                            # Link direto para o vídeo m3u8
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-2/{ch_id}.m3u8")
                            total_geral += 1
                        
                    time.sleep(0.3) # Pausa para não ser bloqueado
                except: continue
        else:
            print(f"Erro ao ler site: {res_cat.status_code}")
    except Exception as e:
        print(f"Falha de conexão: {e}")

    # Backup para não deixar a lista vazia
    if total_geral == 0:
        print("Aviso: Varredura falhou. Usando backup.")
        m3u.append('#EXTINF:-1 tvg-id="s2_4814058" group-title="CAZE TV",CAZÉ TV 01 [S2]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-2/4814058.m3u8")

    # Salva o arquivo final
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Fim! {total_geral} canais salvos.")

if __name__ == "__main__":
    get_channels()

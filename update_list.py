import requests
import re
from bs4 import BeautifulSoup
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

    total_canais = 0
    # Percorre os servidores 1, 2 e 3 conforme os links que você enviou
    for sid in [1, 2, 3]:
        print(f"--- Mapeando Categorias do Servidor {sid} ---")
        cat_url = f"{base_url}/canais/categorias/?thema=1&server=speed-{sid}"
        
        try:
            res_cat = session.get(cat_url, timeout=20)
            if res_cat.status_code != 200:
                print(f"Erro ao ler categorias S{sid}: {res_cat.status_code}")
                continue
                
            soup_cat = BeautifulSoup(res_cat.text, 'html.parser')
            # Busca os links de categorias (.iptv-categoria-card a)
            cat_links = soup_cat.select(".iptv-categoria-card a")
            
            for cl in cat_links:
                cat_name = cl.get_text(strip=True).upper()
                cat_href = cl['href']
                if cat_href.startswith('/'): cat_href = base_url + cat_href
                
                print(f"Capturando Canais de: {cat_name}")
                
                # Entra na página da categoria
                try:
                    res_ch = session.get(cat_href, timeout=20)
                    if res_ch.status_code == 200:
                        soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                        # Busca os canais (iptv-card ou iptv-cat-item)
                        chan_cards = soup_ch.select("a.iptv-card, a.iptv-cat-item")
                        
                        for card in chan_cards:
                            href = card.get('href', '')
                            cid_match = re.search(r'/canais/(\d+)', href)
                            if not cid_match: continue
                            cid = cid_match.group(1)
                            
                            # Pega o nome do canal (span ou h4)
                            name_tag = card.select_one(".iptv-card-title, h4")
                            name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"
                            
                            # Monta a entrada M3U (Link direto conforme seu teste)
                            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="{cat_name} [S{sid}]",{name} [S{sid}]')
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                            total_canais += 1
                        
                        # Pausa curta para não ser banido pelo servidor
                        time.sleep(0.5)
                except: continue
        except: continue

    # Se falhou tudo, coloca o backup para a lista não ficar vazia
    if total_canais == 0:
        m3u.append('#EXTINF:-1 tvg-id="s2_4814058" group-title="CAZE TV",CAZÉ TV 01 [S2]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-2/4814058.m3u8")

    # Salva o arquivo final
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Processo concluído! {total_canais} canais capturados.")

if __name__ == "__main__":
    get_channels()

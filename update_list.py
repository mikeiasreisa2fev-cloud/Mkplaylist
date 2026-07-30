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

    total_canais = 0
    # Percorre os servidores 1, 2 e 3 conforme o caminho informado
    for sid in [1, 2, 3]:
        print(f"--- Processando Servidor {sid} ---")
        # URL das categorias do servidor
        cat_page_url = f"{base_url}/canais/categorias/?thema=1&server=speed-{sid}"
        
        try:
            res = requests.get(cat_page_url, headers=headers, timeout=20)
            if res.status_code != 200: continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            cat_links = soup.select(".iptv-categoria-card a")
            
            for cl in cat_links:
                cat_name = cl.text.strip().upper()
                cat_href = cl['href']
                if cat_href.startswith('/'): cat_href = base_url + cat_href
                
                print(f"Lendo Categoria: {cat_name} [S{sid}]")
                
                try:
                    res_ch = requests.get(cat_href, headers=headers, timeout=20)
                    if res_ch.status_code == 200:
                        soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                        chan_cards = soup_ch.find_all('a', class_='iptv-card')
                        
                        for card in chan_cards:
                            c_href = card.get('href', '')
                            cid_match = re.search(r'/canais/(\d+)/', c_href)
                            if not cid_match: continue
                            cid = cid_match.group(1)
                            
                            name_tag = card.find('span', class_='iptv-card-title')
                            name = name_tag.text.strip() if name_tag else f"Canal {cid}"
                            
                            img_tag = card.find('img')
                            logo = img_tag.get('src') or ""

                            uid = f"s{sid}_{cid}"
                            m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{cat_name} [S{sid}]",{name} [S{sid}]')
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                            total_canais += 1
                        time.sleep(0.5)
                except: continue
        except: continue

    if total_canais > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"Sucesso: {total_canais} canais salvos.")

if __name__ == "__main__":
    get_channels()

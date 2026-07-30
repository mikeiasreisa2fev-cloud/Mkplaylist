import requests
import re
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time

def get_all_data():
    m3u = ["#EXTM3U"]
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Crawler")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_canais = 0
    # Servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"--- Mapeando categorias do Servidor {sid} ---")
        cat_url = f"https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-{sid}"
        
        try:
            res_cat = requests.get(cat_url, headers=headers, timeout=20)
            if res_cat.status_code == 200:
                soup_cat = BeautifulSoup(res_cat.text, 'html.parser')
                # Busca todos os links de categorias (ex: /canais/categorias/3321)
                cat_cards = soup_cat.find_all('div', class_='iptv-categoria-card')
                
                for card in cat_cards:
                    link_tag = card.find('a', href=True)
                    if not link_tag: continue
                    
                    cat_name = link_tag.text.strip().upper()
                    cat_href = link_tag['href']
                    
                    print(f"Lendo categoria: {cat_name}...")
                    
                    # Entra na categoria para pegar os canais
                    res_ch = requests.get(cat_href, headers=headers, timeout=20)
                    if res_ch.status_code == 200:
                        soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                        # Busca os canais (iptv-card)
                        chan_cards = soup_ch.find_all('a', class_='iptv-card')
                        
                        for chan in chan_cards:
                            c_href = chan['href']
                            # Extrai o ID (o número entre /canais/ e /)
                            cid_match = re.search(r'/canais/(\d+)/', c_href)
                            if not cid_match: continue
                            cid = cid_match.group(1)
                            
                            name_tag = chan.find('span', class_='iptv-card-title')
                            name = name_tag.text.strip() if name_tag else f"Canal {cid}"
                            
                            logo = ""
                            img_tag = chan.find('img')
                            if img_tag: logo = img_tag.get('src') or ""

                            uid = f"s{sid}_{cid}"
                            display_name = f"{name} [S{sid}]"
                            group_name = f"{cat_name} [S{sid}]"

                            # M3U
                            m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{group_name}",{display_name}')
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                            
                            # EPG entry
                            c_elem = ET.SubElement(tv, "channel", id=uid)
                            ET.SubElement(c_elem, "display-name").text = display_name
                            
                            total_canais += 1
                        
                        time.sleep(0.3) # Pequena pausa para evitar bloqueio
            else:
                print(f"Erro {res_cat.status_code} ao ler categorias do S{sid}")
        except Exception as e:
            print(f"Erro no Servidor {sid}: {e}")

    # Salva o arquivo M3U
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    # Salva o arquivo EPG (XML básico)
    tree = ET.ElementTree(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    
    print(f"Concluído! {total_canais} canais extraídos com sucesso.")

if __name__ == "__main__":
    get_all_data()

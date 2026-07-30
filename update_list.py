import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time

def get_all_data():
    m3u = ["#EXTM3U"]
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Master-v15")
    
    base_url = "https://app.pobreflix2.site"
    ajax_url = f"{base_url}/wp-admin/admin-ajax.php"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()
    session.headers.update(headers)

    print("Validando sessão (app_check_status)...")
    try:
        session.get(base_url, timeout=15)
        session.post(ajax_url, data={"action": "app_check_status"}, timeout=10)
    except: pass

    total_canais = 0
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        cat_page = f"{base_url}/canais/categorias/?thema=1&server=speed-{sid}"
        print(f"--- Mapeando Servidor {sid} ---")
        
        try:
            res_cat = session.get(cat_page, timeout=20)
            if res_cat.status_code != 200: continue
            
            soup_cat = BeautifulSoup(res_cat.text, 'html.parser')
            # Busca links de categorias (/canais/categorias/ID)
            cat_links = soup_cat.find_all('a', href=re.compile(r'/canais/categorias/'))
            
            for cl in cat_links:
                cat_name = cl.get_text(strip=True).upper()
                if not cat_name or len(cat_name) < 3: continue
                
                cat_href = cl['href']
                if cat_href.startswith('/'): cat_href = base_url + cat_href
                
                print(f"Lendo categoria: {cat_name}")
                
                res_ch = session.get(cat_href, timeout=20)
                if res_ch.status_code == 200:
                    soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                    chan_cards = soup_ch.find_all('a', class_='iptv-card')
                    
                    for card in chan_cards:
                        c_href = card.get('href', '')
                        cid_match = re.search(r'/canais/(\d+)/', c_href)
                        if not cid_match: continue
                        cid = cid_match.group(1)
                        
                        name_tag = card.find('span', class_='iptv-card-title')
                        name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"
                        
                        uid = f"s{sid}_{cid}"
                        display_name = f"{name} [S{sid}]"
                        group_name = f"{cat_name} [S{sid}]"

                        # Adiciona ao M3U
                        m3u.append(f'#EXTINF:-1 tvg-id="{uid}" group-title="{group_name}",{display_name}')
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        
                        # Adiciona ao EPG (Base)
                        chan_elem = ET.SubElement(tv, "channel", id=uid)
                        ET.SubElement(chan_elem, "display-name").text = display_name
                        
                        total_canais += 1
                time.sleep(0.3)
        except Exception as e:
            print(f"Erro no Servidor {sid}: {e}")

    # Salva os arquivos finais
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    tree = ET.ElementTree(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    
    print(f"Sucesso! {total_canais} canais salvos.")

if __name__ == "__main__":
    get_all_data()

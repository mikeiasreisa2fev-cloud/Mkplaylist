import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time

def get_all_data():
    m3u = ["#EXTM3U"]
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Extractor-AllPages")
    
    base_url = "https://app.pobreflix2.site"
    ajax_url = f"{base_url}/wp-admin/admin-ajax.php"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()
    session.headers.update(headers)

    print("Validando sessão (Handshake)...")
    try:
        session.get(base_url, timeout=15)
        session.post(ajax_url, data={"action": "app_check_status"}, timeout=10)
    except: pass

    total_canais = 0
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"--- Iniciando Varredura no Servidor {sid} ---")
        
        # Varre até 60 páginas por servidor conforme solicitado
        for page in range(1, 61):
            url = f"{base_url}/canais/page/{page}/?thema=1&server=speed-{sid}"
            print(f"Lendo S{sid} - Página {page}...")
            
            try:
                res = session.get(url, timeout=25)
                if res.status_code != 200: break
                
                soup = BeautifulSoup(res.text, 'html.parser')
                chan_cards = soup.find_all('a', class_='iptv-card')
                
                if not chan_cards:
                    print(f"Fim das páginas para S{sid} na página {page}.")
                    break
                
                count_page = 0
                for card in chan_cards:
                    c_href = card.get('href', '')
                    cid_match = re.search(r'/canais/(\d+)/', c_href)
                    if not cid_match: continue
                    cid = cid_match.group(1)
                    
                    name_tag = card.find('span', class_='iptv-card-title')
                    name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"
                    
                    logo = ""
                    img_tag = card.find('img')
                    if img_tag: logo = img_tag.get('src') or img_tag.get('data-src') or ""

                    uid = f"s{sid}_{cid}"
                    display_name = f"{name} [S{sid}]"
                    group_name = f"CANAIS [S{sid}]"

                    # M3U - Link direto SEM os cabeçalhos que travavam a reprodução
                    m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{group_name}",{display_name}')
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                    
                    # EPG Base
                    c_elem = ET.SubElement(tv, "channel", id=uid)
                    ET.SubElement(c_elem, "display-name").text = display_name
                    
                    count_page += 1
                    total_canais += 1
                
                if count_page == 0: break
                time.sleep(0.3) # Pausa para evitar bloqueio
                
            except: break

    # Salva os arquivos no repositório GitHub
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    tree = ET.ElementTree(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    print(f"--- SUCESSO TOTAL: {total_canais} canais extraídos ---")

if __name__ == "__main__":
    get_all_data()

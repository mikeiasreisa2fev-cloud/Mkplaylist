import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time
from datetime import datetime

def format_epg_date(timestamp):
    """Converte timestamp Unix para o formato XMLTV (YYYYMMDDHHMMSS +0000)."""
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime("%Y%m%d%H%M%S +0000")
    except:
        return ""

def get_all_data():
    m3u = ["#EXTM3U"]
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Real-EPG-Extractor")

    base_url = "https://app.pobreflix2.site"
    ajax_url = f"{base_url}/wp-admin/admin-ajax.php"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()
    session.headers.update(headers)

    print("Iniciando Handshake...")
    try:
        session.get(base_url, timeout=15)
        session.post(ajax_url, data={"action": "app_check_status"}, timeout=10)
    except: pass

    all_channels = []
    total_canais = 0

    for sid in [1, 2, 3]:
        print(f"\n--- Escaneando Servidor {sid} ---")
        for page in range(1, 61):
            url = f"{base_url}/canais/page/{page}/?thema=1&server=speed-{sid}"
            try:
                res = session.get(url, timeout=25)
                if res.status_code != 200: break
                
                soup = BeautifulSoup(res.text, 'html.parser')
                # Tenta pegar o título da categoria na página para o group-title
                page_title = soup.find(['h2', 'h1'])
                group_name = page_title.get_text(strip=True).upper() if page_title else f"CANAIS [S{sid}]"

                # Busca tanto cards gerais quanto itens de categoria
                items = soup.find_all('a', class_=re.compile(r'iptv-(card|cat-item)'))
                if not items: break

                count_page = 0
                for item in items:
                    c_href = item.get('href', '')
                    cid_match = re.search(r'/canais/(\d+)', c_href)
                    if not cid_match: continue
                    cid = cid_match.group(1)

                    # Busca o nome no span (card) ou h4 (cat-item)
                    name_tag = item.find(['span', 'h4'])
                    name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"
                    
                    logo = ""
                    img_tag = item.find('img')
                    if img_tag: logo = img_tag.get('src') or img_tag.get('data-src') or ""

                    uid = f"s{sid}_{cid}"
                    display_name = f"{name} [S{sid}]"

                    m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{group_name}",{display_name}')
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")

                    chan_elem = ET.SubElement(tv, "channel", id=uid)
                    ET.SubElement(chan_elem, "display-name").text = display_name
                    all_channels.append({"cid": cid, "uid": uid})
                    count_page += 1
                    total_canais += 1

                print(f"S{sid} P{page}: {count_page} canais.")
                if count_page == 0: break
                time.sleep(0.1)
            except: break

    print(f"\nExtraindo guia de programação (EPG)...")
    epg_count = 0
    # Processa os primeiros 150 canais para o Actions não dar erro de tempo
    for item in all_channels[:150]:
        try:
            epg_res = session.post(ajax_url, data={"action": "iptv_get_epg", "stream_id": item['cid']}, timeout=10)
            if epg_res.status_code == 200:
                data = epg_res.json()
                if data.get("success") and data.get("data", {}).get("html"):
                    epg_soup = BeautifulSoup(data["data"]["html"], 'html.parser')
                    for p in epg_soup.find_all(class_='iptv-epg-item'):
                        start = format_epg_date(p.get('data-start'))
                        end = format_epg_date(p.get('data-end'))
                        title = p.find(class_='epg-title').get_text(strip=True)
                        if start and end and title:
                            prog = ET.SubElement(tv, "programme", start=start, stop=end, channel=item['uid'])
                            ET.SubElement(prog, "title", lang="pt").text = title
                    epg_count += 1
            time.sleep(0.05)
        except: continue

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    def indent(elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip(): elem.text = i + "  "
            if not elem.tail or not elem.tail.strip(): elem.tail = i
            for elem in elem: indent(elem, level+1)
            if not elem.tail or not elem.tail.strip(): elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()): elem.tail = i

    indent(tv)
    ET.ElementTree(tv).write("epg.xml", encoding="utf-8", xml_declaration=True)
    print(f"FIM: {total_canais} canais e {epg_count} EPGs capturados.")

if __name__ == "__main__":
    get_all_data()

import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time
from datetime import datetime

def format_epg_date(timestamp):
    """Converte timestamp Unix para o formato XMLTV."""
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

    print("Validando sessão e Cookies...")
    try:
        session.get(base_url, timeout=15)
        session.post(ajax_url, data={"action": "app_check_status"}, timeout=10)
    except: pass

    all_channels = []
    total_canais = 0

    for sid in [1, 2, 3]:
        print(f"\n--- Servidor {sid} ---")
        for page in range(1, 61):
            url = f"{base_url}/canais/page/{page}/?thema=1&server=speed-{sid}"
            try:
                res = session.get(url, timeout=25)
                if res.status_code != 200: break
                soup = BeautifulSoup(res.text, 'html.parser')
                chan_items = soup.find_all('a', class_=re.compile(r'iptv-(card|cat-item)'))
                if not chan_items: break

                count_page = 0
                for item in chan_items:
                    c_href = item.get('href', '')
                    cid_match = re.search(r'/canais/(\d+)', c_href)
                    if not cid_match: continue
                    cid = cid_match.group(1)

                    name_tag = item.find(['span', 'h4'], class_=re.compile(r'iptv-card-title|'))
                    name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"
                    logo = item.find('img').get('src', '') if item.find('img') else ""

                    uid = f"s{sid}_{cid}"
                    display_name = f"{name} [S{sid}]"

                    m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="CANAIS [S{sid}]",{display_name}')
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")

                    chan_elem = ET.SubElement(tv, "channel", id=uid)
                    ET.SubElement(chan_elem, "display-name").text = display_name
                    all_channels.append({"cid": cid, "uid": uid})
                    count_page += 1
                    total_canais += 1

                print(f"Página {page}: {count_page} canais.")
                if count_page == 0: break
                time.sleep(0.1)
            except: break

    print(f"\nExtraindo EPG para {len(all_channels)} canais...")
    epg_count = 0
    for item in all_channels[:150]: # Limite de 150 canais para evitar timeout
        try:
            epg_res = session.post(ajax_url, data={"action": "iptv_get_epg", "stream_id": item['cid']}, timeout=10)
            if epg_res.status_code == 200:
                data = epg_res.json()
                if data.get("success") and data.get("data", {}).get("html"):
                    epg_soup = BeautifulSoup(data["data"]["html"], 'html.parser')
                    for p in epg_soup.find_all(class_='iptv-epg-item'):
                        prog_elem = ET.SubElement(tv, "programme", start=format_epg_date(p.get('data-start')), stop=format_epg_date(p.get('data-end')), channel=item['uid'])
                        ET.SubElement(prog_elem, "title", lang="pt").text = p.find(class_='epg-title').get_text(strip=True)
                    epg_count += 1
            time.sleep(0.1)
        except: continue

    with open("playlist.m3u", "w", encoding="utf-8") as f: f.write("\n".join(m3u))
    tree = ET.ElementTree(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    print(f"FIM: {total_canais} canais e {epg_count} EPGs salvos.")

if __name__ == "__main__":
    get_all_data()

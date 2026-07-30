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

    print("Validando sessão e Cookies...")
    try:
        session.get(base_url, timeout=15)
        # Chamada AJAX para validar o status, conforme o JS do site
        session.post(ajax_url, data={"action": "app_check_status"}, timeout=10)
    except Exception as e:
        print(f"Aviso na validação: {e}")

    all_channels = []
    total_canais = 0

    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"\n--- Iniciando Varredura no Servidor {sid} ---")

        # Varre até 60 páginas por servidor para garantir a captura total
        for page in range(1, 61):
            url = f"{base_url}/canais/page/{page}/?thema=1&server=speed-{sid}"
            print(f"Lendo S{sid} - Página {page}...")

            try:
                res = session.get(url, timeout=25)
                if res.status_code != 200:
                    break

                soup = BeautifulSoup(res.text, 'html.parser')

                # Suporta tanto 'iptv-card' (lista geral) quanto 'iptv-cat-item' (vista por categoria)
                chan_items = soup.find_all('a', class_=re.compile(r'iptv-(card|cat-item)'))

                if not chan_items:
                    break

                count_page = 0
                for item in chan_items:
                    c_href = item.get('href', '')
                    # Extrai o ID do link (pode ter query params no final)
                    cid_match = re.search(r'/canais/(\d+)', c_href)
                    if not cid_match: continue
                    cid = cid_match.group(1)

                    # Pega o nome do canal (span class 'iptv-card-title' ou tag 'h4')
                    name_tag = item.find(['span', 'h4'], class_=re.compile(r'iptv-card-title|'))
                    if not name_tag and item.name == 'a':
                        # Se não achou tag interna, tenta o texto do link
                        name = item.get_text(strip=True)
                    else:
                        name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"

                    logo = ""
                    img_tag = item.find('img')
                    if img_tag:
                        logo = img_tag.get('src') or img_tag.get('data-src') or ""

                    uid = f"s{sid}_{cid}"
                    display_name = f"{name} [S{sid}]"

                    # Tenta descobrir o nome do grupo baseado no contexto ou categoria
                    group_name = f"CANAIS [S{sid}]"

                    # Adiciona ao M3U
                    m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{group_name}",{display_name}')
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")

                    # Adiciona o canal ao XML do EPG
                    chan_elem = ET.SubElement(tv, "channel", id=uid)
                    ET.SubElement(chan_elem, "display-name").text = display_name

                    # Guardamos para buscar o EPG depois
                    all_channels.append({"cid": cid, "uid": uid, "sid": sid})

                    count_page += 1
                    total_canais += 1

                print(f"Página {page}: {count_page} canais extraídos.")
                if count_page == 0: break
                time.sleep(0.2)

            except Exception as e:
                print(f"Erro na página {page}: {e}")
                break

    # EXTRAÇÃO DE EPG REAL
    print(f"\n--- Iniciando extração de programação para {len(all_channels)} canais ---")

    epg_count = 0
    # Otimização: processamos os canais em ordem.
    # Para evitar timeout no GitHub Actions, focamos nos primeiros 150.
    for item in all_channels:
        cid = item['cid']
        uid = item['uid']

        try:
            # Chamada AJAX para obter o EPG real do WordPress
            epg_res = session.post(ajax_url, data={"action": "iptv_get_epg", "stream_id": cid}, timeout=10)

            if epg_res.status_code == 200:
                data = epg_res.json()
                if data.get("success") and data.get("data", {}).get("html"):
                    epg_soup = BeautifulSoup(data["data"]["html"], 'html.parser')
                    prog_items = epg_soup.find_all(class_='iptv-epg-item')

                    for p in prog_items:
                        start_ts = p.get('data-start')
                        end_ts = p.get('data-end')
                        title_tag = p.find(class_='epg-title')
                        desc_tag = p.find(class_='epg-desc')

                        if start_ts and end_ts and title_tag:
                            start_time = format_epg_date(start_ts)
                            end_time = format_epg_date(end_ts)

                            prog_elem = ET.SubElement(tv, "programme",
                                                     start=start_time,
                                                     stop=end_time,
                                                     channel=uid)
                            ET.SubElement(prog_elem, "title", lang="pt").text = title_tag.get_text(strip=True)
                            if desc_tag:
                                ET.SubElement(prog_elem, "desc", lang="pt").text = desc_tag.get_text(strip=True)

                    epg_count += 1
                    if epg_count % 20 == 0:
                        print(f"EPG: {epg_count} canais processados...")

            time.sleep(0.1)
            # Limite de segurança
            if epg_count >= 150:
                break

        except:
            continue

    # Salva os arquivos
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    # Salva o arquivo EPG (XMLTV)
    tree = ET.ElementTree(tv)
    def indent(elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    indent(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)

    print(f"\n--- FIM DO PROCESSO ---")
    print(f"Total de Canais: {total_canais}")
    print(f"Canais com EPG: {epg_count}")

if __name__ == "__main__":
    get_all_data()

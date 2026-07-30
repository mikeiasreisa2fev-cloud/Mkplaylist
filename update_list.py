import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time

def get_all_data():
    m3u = ["#EXTM3U"]
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Master")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_canais = 0
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"--- Explorando Servidor {sid} ---")
        # Página que lista as categorias (Imagem 3 que você mandou)
        cat_url = f"https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-{sid}"
        
        try:
            res_cat = requests.get(cat_url, headers=headers, timeout=20)
            if res_cat.status_code == 200:
                soup_cat = BeautifulSoup(res_cat.text, 'html.parser')
                # Busca todos os links de categorias
                cat_links = soup_cat.find_all('a', href=True)
                
                for cl in cat_links:
                    href = cl['href']
                    if '/canais/categorias/' in href and sid == sid: # Verifica se é link de cat
                        cat_name = cl.text.strip().upper()
                        if not cat_name: continue
                        
                        print(f"Lendo Categoria: {cat_name} [S{sid}]")
                        
                        # Entra na página da categoria para pegar os canais
                        res_ch = requests.get(href, headers=headers, timeout=20)
                        if res_ch.status_code == 200:
                            soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                            # Busca os cards de canais (Imagem 4 e 5)
                            chan_cards = soup_ch.find_all('a', class_='iptv-card')
                            
                            for card in chan_cards:
                                c_href = card['href']
                                cid = "".join(filter(str.isdigit, c_href.split('/')[-2]))
                                
                                name_elem = card.find('span', class_='iptv-card-title')
                                name = name_elem.text.strip() if name_elem else f"Canal {cid}"
                                
                                logo = ""
                                img = card.find('img')
                                if img: logo = img.get('src') or img.get('data-src') or ""

                                uid = f"s{sid}_{cid}"
                                display_name = f"{name} [S{sid}]"
                                group_title = f"{cat_name} [S{sid}]"

                                # Adiciona ao M3U
                                m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{group_title}",{display_name}')
                                # Link direto (sem headers conforme seu teste)
                                m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                                
                                # Adiciona ao EPG
                                c_elem = ET.SubElement(tv, "channel", id=uid)
                                ET.SubElement(c_elem, "display-name").text = display_name
                                
                                total_canais += 1
                        time.sleep(0.5) # Pausa para não ser bloqueado
            else:
                print(f"Erro ao acessar categorias do S{sid}")
        except Exception as e:
            print(f"Falha no servidor {sid}: {e}")

    # Salva os arquivos
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    # Salva o EPG.xml
    # Nota: Programação real exige centenas de chamadas, por isso geramos o guia base primeiro
    indent(tv)
    tree = ET.ElementTree(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    
    print(f"Sucesso! {total_canais} canais extraídos.")

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

if __name__ == "__main__":
    get_all_data()

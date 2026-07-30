import requests
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import time

def get_data():
    m3u = ["#EXTM3U"]
    # Criar a estrutura básica do EPG
    tv = ET.Element("tv", generator_info_name="SpeedFlix-Extractor")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_canais = 0
    # URLs dos servidores que você passou
    servers = {
        1: "https://app.pobreflix2.site/canais/?thema=1&server=speed-1",
        2: "https://app.pobreflix2.site/canais/?thema=1&server=speed-2",
        3: "https://app.pobreflix2.site/canais/?thema=1&server=speed-3"
    }

    for sid, url in servers.items():
        print(f"Lendo Servidor {sid}...")
        try:
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                html = res.text
                # Captura ID e Nome usando o padrão visual do site (iptv-card)
                items = re.findall(r'canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html, re.DOTALL)
                
                if items:
                    print(f"Sucesso! {len(items)} canais encontrados no S{sid}")
                    for cid, name_raw in items:
                        name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                        uid = f"s{sid}_{cid}"
                        
                        # Adiciona na Playlist M3U
                        m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-name="{name} [S{sid}]" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        
                        # Adiciona o canal no EPG
                        chan_elem = ET.SubElement(tv, "channel", id=uid)
                        ET.SubElement(chan_elem, "display-name").text = f"{name} [S{sid}]"
                        
                        total_canais += 1
            else:
                print(f"Erro {res.status_code} no servidor {sid}")
        except Exception as e:
            print(f"Falha no servidor {sid}: {e}")

    # Salva o M3U
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    # Salva o EPG (arquivo vazio por enquanto, pois a extração de horários é lenta)
    # Mas o TiviMate já vai reconhecer os IDs para o futuro
    tree = ET.ElementTree(tv)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    
    print(f"Finalizado! {total_canais} canais guardados.")

if __name__ == "__main__":
    get_data()

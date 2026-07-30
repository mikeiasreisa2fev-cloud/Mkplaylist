import requests
import re
import os

def get_channels():
    m3u = ["#EXTM3U"]

    # --- CANAIS FIXOS CAZE TV (SEMPRE PRESENTES) ---
    caze_tv = [
        ("4814058", "CAZÉ TV 01"), ("4814112", "CAZÉ TV 02"), ("4814113", "CAZÉ TV 03"),
        ("7324475", "CAZE TV 04"), ("7324489", "CAZE TV 05"), ("7324490", "CAZE TV 06"),
        ("7697067", "CAZE TV 07"), ("7697068", "CAZE TV 11"), ("7697077", "CAZE TV 10"),
        ("7697078", "CAZE TV 09"), ("7697079", "CAZE TV 08"), ("7697080", "CAZE TV 12")
    ]

    # Adiciona Caze TV no topo da lista
    for cid, name in caze_tv:
        m3u.append(f'#EXTINF:-1 tvg-id="s2_{cid}" group-title="CAZE TV",{name} [S2]')
        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-2/{cid}.m3u8")

    # --- VARREDURA AUTOMÁTICA ---
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_scraped = 0
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        url = f"https://app.pobreflix2.site/canais/?thema=1&server=speed-{sid}"
        print(f"Lendo Servidor {sid}...")

        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                html = res.text

                # REGEX POTENTE: Procura o ID dentro do link e o nome logo em seguida
                # Padrão: canais/ID e o texto que aparece antes da próxima tag
                matches = re.findall(r'canais/(\d+).*?>(.*?)<', html, re.DOTALL)

                # Evita duplicar canais manuais (CazeTV) se estivermos no servidor 2
                seen = set([c[0] for c in caze_tv if sid == 2])

                for cid, name_raw in matches:
                    if cid in seen or not cid.isdigit() or len(cid) < 5:
                        continue
                    seen.add(cid)

                    # Limpeza profunda do nome (remove tags e espaços)
                    name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                    if not name or len(name) < 2: continue

                    # Adiciona o canal descoberto
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                    m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                    total_scraped += 1

                print(f"Sucesso! Encontrados {len(seen)} canais no Servidor {sid}")
        except Exception as e:
            print(f"Erro ao ler Servidor {sid}: {e}")

    # Salva o arquivo final playlist.m3u para o Railway ler
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print(f"--- FIM: {total_scraped + len(caze_tv)} canais salvos no repositório ---")

if __name__ == "__main__":
    get_channels()

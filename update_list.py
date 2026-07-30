import requests
import re

def get_channels():
    m3u = ["#EXTM3U"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }
    
    total = 0
    # URLs das páginas que você forneceu
    server_urls = {
        1: "https://app.pobreflix2.site/canais/?thema=1&server=speed-1",
        2: "https://app.pobreflix2.site/canais/?thema=1&server=speed-2",
        3: "https://app.pobreflix2.site/canais/?thema=1&server=speed-3"
    }

    for sid, url in server_urls.items():
        print(f"Buscando canais do Servidor {sid}...")
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                # Procura o ID e o Nome no código do site
                # Baseado no HTML que você enviou: href=".../canais/ID/..." e title="NOME"
                items = re.findall(r'href="https://app.pobreflix2.site/canais/(\d+)/.*?title="(.*?)"', r.text)
                
                if items:
                    print(f"Encontrados {len(items)} canais no Servidor {sid}")
                    for cid, name in items:
                        clean_name = name.replace("Assistir ", "").strip()
                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{clean_name} [S{sid}]')
                        # Link direto para o vídeo que funciona no TiviMate
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        total += 1
                else:
                    print(f"Nenhum canal encontrado no Servidor {sid}")
            else:
                print(f"Erro {r.status_code} ao acessar {url}")
        except Exception as e:
            print(f"Erro no Servidor {sid}: {e}")

    # Canal de teste (Globo AC) se nada for encontrado
    if total == 0:
        m3u.append('#EXTINF:-1 tvg-id="s1_11892477",Globo AC FHD [S1]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-1/11892477.m3u8")

    # Salva o arquivo playlist.m3u na raiz do repositório
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Finalizado! {total} canais guardados.")

if __name__ == "__main__":
    get_channels()

import requests
import re
from bs4 import BeautifulSoup
import time

def get_channels():
    m3u = ["#EXTM3U"]
    base_url = "https://app.pobreflix2.site"
    # Link alvo solicitado: categorias do Servidor 2
    target_url = "https://app.pobreflix2.site/canais/categorias/?thema=1&server=speed-2"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": base_url
    }

    session = requests.Session()
    session.headers.update(headers)

    print(f"Iniciando captura das categorias: {target_url}")

    try:
        # 1. Acessa a página de categorias
        res = session.get(target_url, timeout=20)
        if res.status_code != 200:
            print(f"Erro ao acessar o site: {res.status_code}")
            return

        soup = BeautifulSoup(res.text, 'html.parser')
        # Localiza os links de categorias (div.iptv-categoria-card a)
        cat_links = soup.select(".iptv-categoria-card a")

        if not cat_links:
            print("Nenhuma categoria encontrada. Verifique se o link ainda é válido.")
            return

        total_canais = 0
        # 2. Percorre cada link de categoria encontrado
        for cl in cat_links:
            cat_name = cl.get_text(strip=True).upper()
            cat_href = cl['href']
            if cat_href.startswith('/'):
                cat_href = base_url + cat_href

            print(f"Lendo canais da categoria: {cat_name}")

            try:
                # 3. Entra na página da categoria para extrair os canais
                res_ch = session.get(cat_href, timeout=20)
                if res_ch.status_code == 200:
                    soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                    # Busca os cards de canais (a.iptv-card)
                    chan_cards = soup_ch.find_all('a', class_='iptv-card')

                    for card in chan_cards:
                        c_href = card.get('href', '')
                        # Extrai o ID do canal do link
                        cid_match = re.search(r'/canais/(\d+)/', c_href)
                        if not cid_match: continue
                        cid = cid_match.group(1)

                        # Extrai o nome do canal
                        name_tag = card.find('span', class_='iptv-card-title')
                        name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"

                        # Extrai a logo
                        logo = ""
                        img_tag = card.find('img')
                        if img_tag:
                            logo = img_tag.get('src') or img_tag.get('data-src') or ""

                        # Monta a entrada M3U
                        # Usando o padrão de servidor 2 e o link m3u8 direto confirmado
                        m3u.append(f'#EXTINF:-1 tvg-id="s2_{cid}" tvg-logo="{logo}" group-title="{cat_name}",{name} [S2]')
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-2/{cid}.m3u8")
                        total_canais += 1

                # Pequena pausa para não ser bloqueado por excesso de requisições
                time.sleep(0.3)

            except Exception as e:
                print(f"Erro ao processar categoria {cat_name}: {e}")

        # 4. Salva o resultado no arquivo M3U
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))

        print(f"\nConcluído! {total_canais} canais extraídos e salvos em 'playlist.m3u'.")

    except Exception as e:
        print(f"Ocorreu um erro geral: {e}")

if __name__ == "__main__":
    get_channels()

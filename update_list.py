import requests
import re
from bs4 import BeautifulSoup
import time

def get_channels():
    m3u = ["#EXTM3U"]
    base_url = "https://app.pobreflix2.site"
    ajax_url = f"{base_url}/wp-admin/admin-ajax.php"

    # Headers simulando um navegador que entende AJAX conforme o código JS fornecido
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": base_url,
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()
    session.headers.update(headers)

    print("Iniciando Handshake com o servidor (Simulando app_check_status)...")
    try:
        # 1. Visita a home para validar os Cookies iniciais
        session.get(base_url, timeout=15)

        # 2. Simula a chamada AJAX 'app_check_status' encontrada no JS do portal
        # Isso valida a sessão e evita o bloqueio por comportamento de robô
        session.post(ajax_url, data={"action": "app_check_status"}, timeout=10)
        print("Sessão validada com sucesso!")
    except Exception as e:
        print(f"Aviso: Falha na validação inicial ({e}), tentando prosseguir...")

    total_canais = 0
    # Servidores 1, 2 e 3 conforme solicitado
    for sid in [1, 2, 3]:
        print(f"--- Processando Servidor {sid} ---")
        # URL que lista as categorias do servidor
        cat_page = f"{base_url}/canais/categorias/?thema=1&server=speed-{sid}"

        try:
            res_cat = session.get(cat_page, timeout=20)
            if res_cat.status_code != 200:
                print(f"Erro ao acessar categorias do S{sid}: {res_cat.status_code}")
                continue

            soup_cat = BeautifulSoup(res_cat.text, 'html.parser')
            # Busca todos os links de categorias no grid (div.iptv-categoria-card a)
            cat_links = soup_cat.find_all('a', href=re.compile(r'/canais/categorias/'))

            for cl in cat_links:
                cat_name = cl.get_text(strip=True).upper()
                # Ignora links irrelevantes ou curtos demais
                if not cat_name or len(cat_name) < 3: continue

                cat_href = cl['href']
                if cat_href.startswith('/'): cat_href = base_url + cat_href

                print(f"Lendo Categoria: {cat_name} [S{sid}]")

                # Acessa a página da categoria para listar os canais individuais
                try:
                    res_ch = session.get(cat_href, timeout=20)
                    if res_ch.status_code == 200:
                        soup_ch = BeautifulSoup(res_ch.text, 'html.parser')
                        # Busca os cards de canais (a.iptv-card)
                        chan_cards = soup_ch.find_all('a', class_='iptv-card')

                        for card in chan_cards:
                            c_href = card.get('href', '')
                            # Extrai o ID numérico do canal
                            cid_match = re.search(r'/canais/(\d+)/', c_href)
                            if not cid_match: continue
                            cid = cid_match.group(1)

                            # Pega o nome do canal dentro da tag span
                            name_tag = card.find('span', class_='iptv-card-title')
                            name = name_tag.get_text(strip=True) if name_tag else f"Canal {cid}"

                            # Pega a logo (opcional)
                            logo = ""
                            img_tag = card.find('img')
                            if img_tag:
                                logo = img_tag.get('src') or img_tag.get('data-src') or ""

                            uid = f"s{sid}_{cid}"
                            display_name = f"{name} [S{sid}]"
                            group_title = f"{cat_name} [S{sid}]"

                            # Adiciona a entrada M3U com link direto para o m3u8
                            m3u.append(f'#EXTINF:-1 tvg-id="{uid}" tvg-logo="{logo}" group-title="{group_title}",{display_name}')
                            # Link de reprodução direta conforme o padrão do site
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")

                            total_canais += 1

                        # Pequena pausa para evitar sobrecarga no servidor de destino
                        time.sleep(0.5)
                except Exception as e:
                    print(f"Erro ao ler canais da categoria {cat_name}: {e}")

        except Exception as e:
            print(f"Falha ao processar categorias do servidor {sid}: {e}")

    # Salva o arquivo final playlist.m3u na raiz para ser servido pelo app.py
    if total_canais > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"--- SUCESSO: {total_canais} canais extraídos e salvos em playlist.m3u ---")
    else:
        print("ERRO: Nenhum canal encontrado. Verifique se o site mudou a estrutura das tags.")

if __name__ == "__main__":
    get_channels()

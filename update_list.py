import requests
import re

def get_channels():
    m3u = ["#EXTM3U"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_geral = 0
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        url = f"https://app.pobreflix2.site/canais/?thema=1&server=speed-{sid}"
        print(f"Lendo Servidor {sid}: {url}")
        
        try:
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                html = res.text
                
                # BUSCA PRECISA: Procura o padrão exato que você me enviou no HTML
                # Padrão: href=".../canais/ID/..." class="iptv-card" ... span class="iptv-card-title">NOME</span>
                items = re.findall(r'href="https://app.pobreflix2.site/canais/(\d+)/.*?class="iptv-card".*?iptv-card-title">(.*?)</span>', html, re.DOTALL)
                
                if not items:
                    # Segunda tentativa: padrão mais simples se o primeiro falhar
                    items = re.findall(r'/canais/(\d+)/.*?>(.*?)</a>', html, re.DOTALL)

                if items:
                    seen_ids = set()
                    for cid, name_raw in items:
                        if cid in seen_ids: continue
                        seen_ids.add(cid)
                        
                        # Limpa o nome removendo tags HTML e textos extras
                        name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                        
                        # Tenta capturar o link da imagem (Logo)
                        logo = ""
                        logo_match = re.search(fr'canais/{cid}/.*?src="(.*?)"', html)
                        if logo_match:
                            logo = logo_match.group(1)

                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                        # Link direto para o vídeo (conforme descoberto no seu código-fonte)
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8|User-Agent=okhttp/4.12.0&Referer=https://app.pobreflix2.site/")
                        total_geral += 1
                    print(f"Sucesso! {len(seen_ids)} canais encontrados no Servidor {sid}")
                else:
                    print(f"Aviso: HTML lido, mas nenhum canal identificado no Servidor {sid}")
            else:
                print(f"Erro {res.status_code} ao acessar Servidor {sid}")
        except Exception as e:
            print(f"Falha de conexão no Servidor {sid}: {e}")

    # Se a varredura falhar totalmente, mantém o backup para não quebrar a lista
    if total_geral == 0:
        m3u.append('#EXTINF:-1 tvg-id="s1_11892477",Globo AC FHD [S1]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-1/11892477.m3u8|User-Agent=okhttp/4.12.0&Referer=https://app.pobreflix2.site/")

    # Salva a lista no arquivo final
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Processo finalizado. Total de canais capturados: {total_geral}")

if __name__ == "__main__":
    get_channels()

import requests
import re

def get_channels():
    # Início da lista M3U
    m3u = ["#EXTM3U"]
    
    # Headers para o GitHub conseguir ler o site sem ser bloqueado
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_geral = 0
    
    # Percorre os servidores 1, 2 e 3 conforme solicitado
    for sid in [1, 2, 3]:
        url = f"https://app.pobreflix2.site/canais/?thema=1&server=speed-{sid}"
        print(f"Lendo Servidor {sid}...")
        
        try:
            # Faz a requisição para a página do servidor
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                html = res.text
                
                # Procura o ID do canal e o Nome usando o padrão do site (iptv-card-title)
                items = re.findall(r'/canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html, re.DOTALL)
                
                if items:
                    seen_ids = set()
                    for cid, name_raw in items:
                        if cid in seen_ids: continue
                        seen_ids.add(cid)
                        
                        # Limpa o nome do canal (remove tags HTML e o texto 'Assistir')
                        clean_name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                        
                        # Adiciona o nome com a identificação do servidor [S1], [S2] ou [S3]
                        display_name = f"{clean_name} [S{sid}]"
                        # Define o grupo com o número do servidor
                        group = f"CANAIS [S{sid}]"
                        
                        # Tenta capturar o link da imagem (Logo)
                        logo_match = re.search(fr'canais/{cid}/.*?src="(.*?)"', html)
                        logo = logo_match.group(1) if logo_match else ""

                        # Escreve a linha do canal no formato M3U
                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{display_name}')
                        
                        # Link direto para o vídeo (sem os headers extras que davam erro)
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        
                        total_geral += 1
                    print(f"Sucesso! {len(seen_ids)} canais capturados no Servidor {sid}")
                else:
                    print(f"Aviso: HTML lido, mas nenhum canal identificado no Servidor {sid}")
            else:
                print(f"Erro {res.status_code} ao acessar Servidor {sid}")
        except Exception as e:
            print(f"Falha de conexão no Servidor {sid}: {e}")

    # Lista de Backup caso a captura falhe totalmente
    if total_geral == 0:
        m3u.append('#EXTINF:-1 tvg-id="s1_11892477" group-title="CANAIS [S1]",Globo AC FHD [S1]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-1/11892477.m3u8")

    # Salva o arquivo playlist.m3u na raiz do repositório
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    print(f"Processo finalizado. Total de canais salvos: {total_geral}")

if __name__ == "__main__":
    get_channels()

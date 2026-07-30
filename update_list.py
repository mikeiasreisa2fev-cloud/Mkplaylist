import requests
import re
import json

def get_channels():
    m3u = ["#EXTM3U"]
    
    # Canais de backup (extraídos do seu código-fonte para segurança)
    backup_channels = [
        {"id": "11892477", "name": "Globo AC - Amazonica Rio Branco FHD"},
        {"id": "11892478", "name": "Globo AC - Amazonica Rio Branco HD"},
        {"id": "11892479", "name": "Globo AC - Amazonica Rio Branco SD"},
        {"id": "11892480", "name": "Globo AL - Gazeta de Alagoas FHD"},
        {"id": "11892481", "name": "Globo AL - Gazeta de Alagoas HD"},
        {"id": "11892482", "name": "Globo AL - Gazeta de Alagoas SD"},
    ]

    # Headers de navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_encontrado = 0

    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"Buscando canais do Servidor {sid}...")
        # URL da página de todos os canais que você enviou
        url = f"https://app.pobreflix2.site/canais/?thema=1&server=speed-{sid}"
        
        try:
            res = requests.get(url, headers=headers, timeout=25)
            if res.status_code == 200:
                html = res.text
                
                # Regex para encontrar o padrão do site: href e o título (span ou alt)
                # Procura links do tipo /canais/NUMERO/ e pega o nome no atributo 'alt' ou no span
                matches = re.findall(r'href="https://app.pobreflix2.site/canais/(\d+)/".*?alt="(.*?)"', html)
                
                if not matches:
                    # Tenta um padrão secundário (apenas o link e o nome no span)
                    matches = re.findall(r'canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html, re.DOTALL)

                if matches:
                    print(f"Sucesso! {len(matches)} canais capturados no S{sid}")
                    for cid, name in matches:
                        clean_name = name.replace("Assistir ", "").strip()
                        display_name = f"{clean_name} [S{sid}]"
                        group = f"CANAIS [S{sid}]"
                        
                        # Tenta achar a logo para este ID específico
                        logo_match = re.search(fr'canais/{cid}/.*?src="(.*?)"', html)
                        logo = logo_match.group(1) if logo_match else ""

                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{display_name}')
                        # Link direto do servidor de vídeo oficial (descoberto no seu HTML)
                        # O sufixo '|' é para o TiviMate enviar os headers necessários
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8|User-Agent=okhttp/4.12.0&Referer=https://app.pobreflix2.site/")
                        total_encontrado += 1
                else:
                    print(f"Aviso: HTML do S{sid} lido, mas nenhum canal identificado pelo código.")
            else:
                print(f"Erro {res.status_code} ao acessar o S{sid}")
        except Exception as e:
            print(f"Falha de conexão no S{sid}: {e}")

    # Se a varredura falhou totalmente, usa os canais de backup da Globo
    if total_encontrado == 0:
        print("Usando lista de backup...")
        for ch in backup_channels:
            m3u.append(f'#EXTINF:-1 tvg-id="s1_{ch["id"]}" group-title="CANAIS [S1]",{ch["name"]} [S1]')
            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-1/{ch['id']}.m3u8|User-Agent=okhttp/4.12.0&Referer=https://app.pobreflix2.site/")
            total_encontrado += 1

    # Salva o arquivo no repositório
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    print(f"Processo finalizado. Total de canais salvos: {total_encontrado}")

if __name__ == "__main__":
    get_channels()

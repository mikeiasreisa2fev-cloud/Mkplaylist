import requests
import re
import json
import time

def get_channels():
    m3u = ["#EXTM3U"]
    # Usamos o corsproxy.io que é um dos mais potentes para burlar bloqueios
    PROXY = "https://corsproxy.io/?"
    
    total_geral = 0
    # Percorrer os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        print(f"--- Lendo Servidor {sid} via Proxy ---")
        
        # Vamos tentar ler as primeiras 5 páginas de cada servidor para garantir volume
        for page in range(1, 6):
            target_url = f"https://app.pobreflix2.site/canais/page/{page}/?thema=1&server=speed-{sid}"
            
            try:
                # O corsproxy.io não exige parâmetros extras, apenas a URL no final
                res = requests.get(f"{PROXY}{target_url}", timeout=30)
                
                if res.status_code == 200:
                    html = res.text
                    
                    # Regex para capturar ID e Nome baseado no código que você me enviou
                    # Procura o link /canais/ID e o nome dentro do <h4> ou span
                    matches = re.findall(r'href=".*?/canais/(\d+).*?>.*?<h4>(.*?)</h4>', html, re.DOTALL)
                    
                    if not matches:
                        # Tenta padrão alternativo (span class iptv-card-title)
                        matches = re.findall(r'/canais/(\d+).*?iptv-card-title">(.*?)</span>', html, re.DOTALL)

                    if matches:
                        seen_ids = set()
                        count_page = 0
                        for cid, name_raw in matches:
                            if cid in seen_ids: continue
                            seen_ids.add(cid)
                            
                            # Limpa o nome
                            name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                            
                            m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                            # Link direto conforme seu teste de reprodução
                            m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                            total_geral += 1
                            count_page += 1
                        
                        print(f"Página {page}: {count_page} canais encontrados.")
                        if count_page < 5: break # Fim da lista
                    else:
                        print(f"Página {page}: Nenhum canal identificado.")
                        break
                else:
                    print(f"Erro {res.status_code} na página {page}")
                    break
                    
                time.sleep(1) # Pausa para não ser banido
            except Exception as e:
                print(f"Falha na conexão: {e}")
                break

    # 3. Salva a lista
    if total_geral > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"Sucesso! {total_geral} canais salvos em playlist.m3u")
    else:
        # Se falhou tudo, coloca o canal da Caze TV que sabemos que funciona
        print("Usando canais de emergência...")
        m3u.append('#EXTINF:-1 tvg-id="s2_4814058" group-title="CAZE TV",CAZÉ TV 01 [S2]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-2/4814058.m3u8")
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))

if __name__ == "__main__":
    get_channels()

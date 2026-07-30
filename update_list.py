import requests
import re
import uuid
import random
import time

def get_channels():
    m3u = ["#EXTM3U"]
    # Domínios para tentativa
    DOMAINS = ["https://app.pobreflix2.site", "https://ycineflix.tudo30.shop"]
    
    # Gerar um IP brasileiro falso para enganar o firewall (Simula rede residencial)
    fake_ip = f"{random.choice([177, 179, 186, 187, 189, 191, 200, 201])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    
    # Headers que o Aplicativo SpeedFlix original envia para o servidor
    headers = {
        "User-Agent": "okhttp/4.12.0",
        "X-Requested-With": "site.speedflix",
        "X-Forwarded-For": fake_ip,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9"
    }

    total_geral = 0
    
    for base_url in DOMAINS:
        print(f"Tentando capturar via: {base_url}")
        
        # Percorre os servidores 1, 2 e 3 conforme solicitado
        for sid in [1, 2, 3]:
            # Faz a varredura nas primeiras páginas de cada servidor
            for page in range(1, 4):
                url = f"{base_url}/canais/page/{page}/?thema=1&server=speed-{sid}"
                print(f"Lendo S{sid} Página {page}...")
                
                try:
                    res = requests.get(url, headers=headers, timeout=25)
                    if res.status_code == 200:
                        html = res.text
                        
                        # BUSCA AVANÇADA: Procura o link /canais/ID e o nome do canal por perto
                        # Suporta os formatos span class="iptv-card-title" e tag <h4>
                        matches = re.findall(r'/canais/(\d+)/.*?iptv-card-title">(.*?)</span>', html, re.DOTALL)
                        if not matches:
                            matches = re.findall(r'/canais/(\d+)/.*?<h4>(.*?)</h4>', html, re.DOTALL)
                        if not matches:
                            matches = re.findall(r'/canais/(\d+)/.*?>(.*?)</a>', html, re.DOTALL)

                        if matches:
                            seen_ids = set()
                            count = 0
                            for cid, name_raw in matches:
                                if cid in seen_ids or not cid.isdigit(): continue
                                seen_ids.add(cid)
                                
                                # Limpa o nome removendo tags HTML e textos inúteis
                                name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                                if len(name) < 2: name = f"Canal {cid}"
                                
                                # Monta a linha M3U
                                m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                                # Link direto que você confirmou que reproduz sem erro
                                m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                                total_geral += 1
                                count += 1
                            
                            print(f"Sucesso: {count} canais encontrados em S{sid} P{page}")
                            if count < 5: break # Se a página veio quase vazia, é a última
                        else:
                            print(f"Aviso: HTML lido mas nenhum padrão de canal encontrado.")
                            break
                    else:
                        print(f"Erro HTTP {res.status_code} em S{sid}")
                        break
                except Exception as e:
                    print(f"Falha de conexão: {e}")
                    break
        
        if total_geral > 10: break # Se já capturou volume suficiente, não precisa tentar o outro domínio

    # Plano de Emergência: Caso a varredura falhe totalmente, mantém os canais da Caze TV
    if total_geral == 0:
        print("ALERTA: Varredura falhou. Inserindo canais de backup.")
        m3u.append('#EXTINF:-1 tvg-id="s2_4814058" group-title="CAZE TV",CAZÉ TV 01 [S2]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-2/4814058.m3u8")
        m3u.append('#EXTINF:-1 tvg-id="s2_4814112" group-title="CAZE TV",CAZÉ TV 02 [S2]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-2/4814112.m3u8")

    # Salva o arquivo playlist.m3u para o Railway ler
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    print(f"Fim do processo. Total de {total_geral} canais guardados no repositório.")

if __name__ == "__main__":
    get_channels()

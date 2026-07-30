import requests
import re
import time

def get_channels():
    m3u = ["#EXTM3U"]
    # Headers para o GitHub conseguir ler o site
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://app.pobreflix2.site/"
    }

    total_geral = 0
    # Percorre os servidores 1, 2 e 3
    for sid in [1, 2, 3]:
        # Tentamos ler a página principal do servidor
        url = f"https://app.pobreflix2.site/canais/?thema=1&server=speed-{sid}"
        print(f"Lendo Servidor {sid}...")
        
        try:
            res = requests.get(url, headers=headers, timeout=25)
            if res.status_code == 200:
                html = res.text
                
                # BUSCA AGRESSIVA: Procura o ID (número) e o Nome
                # O Regex agora é flexível para pegar tanto em 'h4' quanto em 'span'
                # Ele busca o ID entre '/canais/' e '/' e o texto que aparece depois
                matches = re.findall(r'/canais/(\d+)/.*?>(.*?)<', html, re.DOTALL)
                
                if matches:
                    seen_ids = set()
                    for cid, name_raw in matches:
                        if cid in seen_ids or not cid.isdigit() or len(cid) < 5: 
                            continue
                        
                        seen_ids.add(cid)
                        
                        # Limpa o nome removendo tags HTML e textos inúteis
                        name = re.sub('<[^<]+?>', '', name_raw).replace("Assistir ", "").strip()
                        if len(name) < 2: name = f"Canal {cid}"
                        
                        m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" group-title="CANAIS [S{sid}]",{name} [S{sid}]')
                        # Link direto que você confirmou que reproduz sem erro
                        m3u.append(f"https://speed.megafilmeshd9.com/midia/speed-{sid}/{cid}.m3u8")
                        total_geral += 1
                        
                    print(f"Sucesso: {len(seen_ids)} canais encontrados no S{sid}")
            else:
                print(f"Erro {res.status_code} ao acessar servidor {sid}")
        except: continue

    # Se a varredura falhou, usa a Caze TV como backup (conforme você passou)
    if total_geral == 0:
        print("ALERTA: Varredura falhou. Usando backups manuais.")
        m3u.append('#EXTINF:-1 tvg-id="s2_4814058" group-title="CAZE TV",CAZÉ TV 01 [S2]')
        m3u.append("https://speed.megafilmeshd9.com/midia/speed-2/4814058.m3u8")

    # Salva o arquivo final
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"Finalizado! {total_geral} canais salvos.")

if __name__ == "__main__":
    get_channels()

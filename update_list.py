import requests
import json

def get_channels():
    m3u = ["#EXTM3U"]
    base_api = "https://app.pobreflix2.site/wp-json/xui-pflix/v1/channels"
    headers = {"User-Agent": "okhttp/4.12.0", "X-Requested-With": "site.speedflix"}

    for sid in [1, 2, 3]:
        try:
            # Pede 500 canais de uma vez
            r = requests.get(base_api, params={"server_id": sid, "per_page": 500}, headers=headers, timeout=20)
            if r.status_code == 200:
                items = r.json().get("data", {}).get("items") or r.json().get("items") or []
                for ch in items:
                    cid = ch.get("id")
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    group = f"{(ch.get('category_name') or 'Canais').upper()} [S{sid}]"
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{ch.get("image","")}" group-title="{group}",{name}')
                    # O link aponta para o seu app no Railway que faz o redirect
                    m3u.append(f"https://mkplaylist-production.up.railway.app/stream/{sid}/{cid}")
        except: continue
    
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

if __name__ == "__main__":
    get_channels()

import requests
import json
import uuid
import time

# Configurações baseadas no seu código
BASE_URL = "https://ycineflix.tudo30.shop/wp-json/xui-pflix/v1"
USER_AGENT = "okhttp/4.12.0"
APP_ID = "site.speedflix"
# URL DO SEU PROJETO NO RAILWAY (Ajuste se o link for diferente)
RAILWAY_URL = "https://mkplaylist-production.up.railway.app"

class SpeedFlixAPI:
    def __init__(self):
        self.token = None
        self.device_id = str(uuid.uuid4()).replace('-', '')[:16]

    def login(self):
        if self.token: return self.token
        try:
            payload = {
                "username": f"guest_{self.device_id[:8]}",
                "password": "guest",
                "device_id": self.device_id,
                "model": "Samsung SM-G998B",
                "version": "13"
            }
            headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Content-Type": "application/json"}
            r = requests.post(f"{BASE_URL}/auth/login", json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                self.token = data.get("data", {}).get("token") or data.get("token")
                return self.token
        except: pass
        return None

    def get_headers(self):
        headers = {"User-Agent": USER_AGENT, "X-Requested-With": APP_ID, "Accept": "application/json"}
        token = self.login()
        if token: headers["Authorization"] = f"Bearer {token}"
        return headers

api = SpeedFlixAPI()

def get_channels():
    m3u = ["#EXTM3U"]
    total_canais = 0
    
    for sid in [1, 2, 3]:
        page = 1
        while page <= 15:
            try:
                r = requests.get(f"{BASE_URL}/channels", 
                                params={"server_id": sid, "per_page": 100, "page": page},
                                headers=api.get_headers(), timeout=20)
                if r.status_code != 200: break
                
                data = r.json()
                items = data.get("data", {}).get("items") or data.get("items") or []
                if not items: break
                
                print(f"Servidor {sid} - Pagina {page}: {len(items)} canais.")
                
                for ch in items:
                    cid = ch.get("id")
                    if not cid: continue
                    name = f"{ch.get('name') or ch.get('title')} [S{sid}]"
                    cat = ch.get('category_name') or 'Canais'
                    group = f"{cat.upper()} [S{sid}]"
                    logo = ch.get("image") or ""
                    
                    m3u.append(f'#EXTINF:-1 tvg-id="s{sid}_{cid}" tvg-logo="{logo}" group-title="{group}",{name}')
                    m3u.append(f"{RAILWAY_URL}/stream/{sid}/{cid}")
                    total_canais += 1
                
                meta = data.get("data", {}).get("meta") or data.get("meta") or {}
                if page >= int(meta.get("total_pages", 1)): break
                page += 1
            except: break

    if total_canais > 0:
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u))
        print(f"Sucesso! {total_canais} canais salvos no arquivo.")
    else:
        print("Erro: Nenhum canal capturado.")

if __name__ == "__main__":
    get_channels()

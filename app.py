import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, Response
import os

app = Flask(__name__)

BASE_URL = "https://speedflix02.com/wp-json/xui-pflix/v1"
SERVERS = [1, 2, 3]

def get_channels(server_id):
    channels = []
    page = 1
    while True:
        try:
            print(f"Fetching channels for server {server_id}, page {page}...")
            response = requests.get(f"{BASE_URL}/channels", params={
                "server_id": server_id,
                "page": page,
                "per_page": 100
            }, timeout=15)
            if response.status_code != 200:
                print(f"Error {response.status_code} for server {server_id}")
                break

            data = response.json()
            # The API returns Lbs<Lca5<Lib4>> so it might be wrapped in "data" or "items"
            items = data.get("items") or data.get("data", {}).get("items")
            if not items:
                break

            channels.extend(items)

            total_pages = data.get("total_pages") or data.get("data", {}).get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching channels for server {server_id}: {e}")
            break
    return channels

def get_epg(channel_id, server_id):
    try:
        response = requests.get(f"{BASE_URL}/channels/{channel_id}/epg", params={
            "server_id": server_id,
            "limit": 20
        }, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Response is Lbs<Lgw0> where Lgw0 has "epg" (Lk52) which has "epg_listings"
            epg_data = data.get("epg") or data.get("data", {}).get("epg")
            if epg_data:
                return epg_data.get("epg_listings", [])
    except Exception as e:
        print(f"Error fetching EPG for channel {channel_id}: {e}")
    return []

def generate_xmltv():
    tv = ET.Element("tv", generator_info_name="SpeedFlix EPG Generator")

    processed_channel_ids = set()

    for server_id in SERVERS:
        channels = get_channels(server_id)
        print(f"Found {len(channels)} channels on server {server_id}")
        for ch in channels:
            channel_id = ch.get("id")
            if not channel_id or channel_id in processed_channel_ids:
                continue

            processed_channel_ids.add(channel_id)

            name = ch.get("name") or ch.get("title") or f"Channel {channel_id}"
            icon = ch.get("image")

            # Create channel element
            channel_elem = ET.SubElement(tv, "channel", id=str(channel_id))
            ET.SubElement(channel_elem, "display-name").text = name
            if icon:
                ET.SubElement(channel_elem, "icon", src=icon)

            # Fetch and add EPG programs
            listings = get_epg(channel_id, server_id)
            for prog in listings:
                start_ts = prog.get("start_timestamp")
                stop_ts = prog.get("stop_timestamp")
                title = prog.get("title")
                desc = prog.get("description")

                if start_ts and stop_ts and title:
                    try:
                        # XMLTV format: YYYYMMDDHHMMSS +HHMM
                        start_time = datetime.fromtimestamp(int(start_ts)).strftime("%Y%m%d%H%M%S +0000")
                        stop_time = datetime.fromtimestamp(int(stop_ts)).strftime("%Y%m%d%H%M%S +0000")

                        programme_elem = ET.SubElement(tv, "programme",
                                                     start=start_time,
                                                     stop=stop_time,
                                                     channel=str(channel_id))
                        ET.SubElement(programme_elem, "title", lang="pt").text = title
                        if desc:
                            ET.SubElement(programme_elem, "desc", lang="pt").text = desc
                    except:
                        continue

    return ET.tostring(tv, encoding="utf-8", xml_declaration=True)

@app.route("/")
def index():
    return "SpeedFlix EPG Generator is active.<br>Access <a href='/epg.xml'>/epg.xml</a> to download EPG."

@app.route("/epg.xml")
def epg():
    xml_data = generate_xmltv()
    return Response(xml_data, mimetype="application/xml")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

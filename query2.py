#!/usr/bin/env python3
"""
Step 2: Query for elements with explicit indigenous language name tags.
"""

import json
import time
import urllib.error
import urllib.request
import urllib.parse
from collections import defaultdict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "overpass-native-placenames/1.0 (github research; halmueller@gmail.com)"

# ISO 639-3 codes for Pacific Northwest / Washington state indigenous languages
# See: https://iso639-3.sil.org/
INDIGENOUS_CODES = [
    "clm",   # Klallam (Lower Elwha, Jamestown, Port Gamble S'Klallam)
    "lut",   # Lushootseed (Puget Sound Salish — Puyallup, Snohomish, Muckleshoot, etc.)
    "nez",   # Nez Perce
    "oka",   # Okanagan-Colville
    "myh",   # Makah
    "twa",   # Twana (Skokomish)
    "chn",   # Chinook Jargon
    "str",   # Straits Salish (Saanich / Northern Straits)
    "spo",   # Spokane
    "fla",   # Kalispel-Pend d'Oreilles (Flathead)
    "yak",   # Yakama (no standard ISO code; sometimes used informally)
    "wac",   # Wishram-Wasco (Upper Chinookan)
    "cjh",   # Upper Chehalis
    "qun",   # Quinault
    "twf",   # Takelma (unlikely but include)
    "psc",   # Colville (sometimes psc)
]

code_list = "|".join(INDIGENOUS_CODES)

QUERY = f"""
[out:json][timeout:300];
area["name"="Washington"]["admin_level"="4"]["boundary"="administrative"]->.wa;
(
  node(area.wa)[~"^name:({code_list})$"~"."];
  way(area.wa)[~"^name:({code_list})$"~"."];
  relation(area.wa)[~"^name:({code_list})$"~"."];
);
out tags;
"""


def run_query(query: str) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(3):
        req = urllib.request.Request(OVERPASS_URL, data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("User-Agent", USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=360) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = 60 * (attempt + 1)
                print(f"Rate limited (429); waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise


def main():
    print(f"Querying for language codes: {code_list}\n", flush=True)
    result = run_query(QUERY)
    elements = result.get("elements", [])
    print(f"Got {len(elements)} elements\n")

    # Group by which language codes appear
    by_lang = defaultdict(list)
    for el in elements:
        tags = el.get("tags", {})
        for code in INDIGENOUS_CODES:
            if f"name:{code}" in tags:
                by_lang[code].append(el)

    for code, items in sorted(by_lang.items()):
        print(f"=== name:{code} ({len(items)} elements) ===")
        for el in items[:5]:
            tags = el.get("tags", {})
            name = tags.get("name", "")
            name_en = tags.get("name:en", tags.get("name", ""))
            native = tags.get(f"name:{code}", "")
            ftype = el["type"]
            # Get the OSM feature type
            for key in ["place", "natural", "waterway", "highway", "amenity", "leisure"]:
                if key in tags:
                    ftype = f"{ftype}/{key}={tags[key]}"
                    break
            print(f"  [{ftype}]  name={name!r}")
            print(f"           name:{code}={native!r}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
        print()

    with open("raw_results2.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("Full results saved to raw_results2.json")


if __name__ == "__main__":
    main()

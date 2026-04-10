#!/usr/bin/env python3
"""
Step 1: Run the name != name:en query against Overpass and dump raw results.
"""

import json
import time
import urllib.error
import urllib.request
import urllib.parse

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "overpass-native-placenames/1.0 (github research; halmueller@gmail.com)"

QUERY = """
[out:json][timeout:300];
area["name"="Washington"]["admin_level"="4"]["boundary"="administrative"]->.wa;
(
  node["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  way["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  relation["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
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
    print("Running query...", flush=True)
    result = run_query(QUERY)
    elements = result.get("elements", [])
    print(f"Got {len(elements)} elements\n")

    for el in elements[:20]:  # preview first 20
        tags = el.get("tags", {})
        name = tags.get("name", "")
        name_en = tags.get("name:en", "")
        etype = el.get("type", "")
        eid = el.get("id", "")
        print(f"[{etype}/{eid}]  name={name!r}  name:en={name_en!r}")

    if len(elements) > 20:
        print(f"\n... and {len(elements) - 20} more")

    # Save full results for inspection
    with open("raw_results.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\nFull results saved to raw_results.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Extract Washington state places with indigenous / non-English names from OSM.

Two complementary queries:
  Q1 — geographic features where name != name:en (native name embedded in primary tag)
  Q2 — any element with an explicit indigenous language name tag (name:lut, name:clm, etc.)

Results are merged, deduplicated, and written to stdout as a TSV table and to
placenames.tsv as a file.
"""

import json
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from collections import defaultdict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "overpass-native-placenames/1.0 (github research; halmueller@gmail.com)"

# ISO 639-3 codes for PNW / WA indigenous languages, with display names
INDIGENOUS_LANGS = {
    "clm": "Klallam",
    "lut": "Lushootseed",
    "nez": "Nez Perce",
    "oka": "Okanagan-Colville",
    "myh": "Makah",
    "twa": "Twana / Skokomish",
    "chn": "Chinook Jargon",
    "str": "Straits Salish",
    "spo": "Spokane",
    "fla": "Kalispel-Pend d'Oreilles",
    "yak": "Yakama",
    "wac": "Wishram-Wasco",
    "cjh": "Upper Chehalis",
    "qun": "Quinault",
    "psc": "Colville",
}

CODE_LIST = "|".join(INDIGENOUS_LANGS)

# OSM tag keys that indicate a real geographic/cultural feature
FEATURE_KEYS = ["place", "natural", "waterway", "boundary", "highway", "leisure",
                "landuse", "historic", "amenity", "tourism"]

# Feature types we want to keep (others are filtered out as noise)
KEEP_FEATURE_TYPES = {
    # places
    "place=city", "place=town", "place=village", "place=hamlet",
    "place=locality", "place=suburb", "place=neighbourhood",
    "place=isolated_dwelling", "place=farm",
    # terrain / nature
    "natural=peak", "natural=volcano", "natural=water", "natural=bay",
    "natural=cape", "natural=spring", "natural=wetland", "natural=beach",
    "natural=cliff", "natural=valley", "natural=glacier", "natural=strait",
    "natural=peninsula", "natural=island", "natural=stone",
    # water
    "waterway=river", "waterway=stream", "waterway=lake",
    # administrative
    "boundary=administrative",
    # roads on tribal land with bilingual names
    "highway=residential", "highway=secondary", "highway=tertiary",
    "highway=unclassified", "highway=service",
    # cultural / parks
    "leisure=park", "leisure=nature_reserve",
    "historic=site", "historic=ruins",
    "amenity=college",
    "tourism=attraction",
}

# ── Queries ──────────────────────────────────────────────────────────────────

QUERY_GEOGRAPHIC = """
[out:json][timeout:300];
area["name"="Washington"]["admin_level"="4"]["boundary"="administrative"]->.wa;
(
  node["place"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  node["natural"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  node["waterway"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  way["natural"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  way["waterway"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  relation["place"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  relation["natural"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  relation["waterway"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
  relation["boundary"="administrative"]["name"]["name:en"](if: t["name"] != t["name:en"])(area.wa);
);
out tags;
"""

QUERY_NATIVE_TAGS = f"""
[out:json][timeout:300];
area["name"="Washington"]["admin_level"="4"]["boundary"="administrative"]->.wa;
(
  node(area.wa)[~"^name:({CODE_LIST})$"~"."];
  way(area.wa)[~"^name:({CODE_LIST})$"~"."];
  relation(area.wa)[~"^name:({CODE_LIST})$"~"."];
);
out tags;
"""


# ── HTTP ──────────────────────────────────────────────────────────────────────

def run_query(label: str, query: str) -> list[dict]:
    print(f"  Running {label}...", end=" ", flush=True)
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(3):
        req = urllib.request.Request(OVERPASS_URL, data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("User-Agent", USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=360) as resp:
                result = json.loads(resp.read().decode())
            elements = result.get("elements", [])
            print(f"{len(elements)} elements")
            return elements
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = 60 * (attempt + 1)
                print(f"\n  Rate limited (429); waiting {wait}s before retry...", end=" ", flush=True)
                time.sleep(wait)
            else:
                raise


# ── Processing ────────────────────────────────────────────────────────────────

def element_key(el: dict) -> str:
    return f"{el['type']}/{el['id']}"


def feature_type(tags: dict) -> str:
    for key in FEATURE_KEYS:
        if key in tags:
            return f"{key}={tags[key]}"
    return "unknown"


def native_names(tags: dict) -> dict[str, str]:
    """Return {lang_code: native_name} for all known indigenous language tags."""
    result = {}
    for code in INDIGENOUS_LANGS:
        val = tags.get(f"name:{code}")
        if val:
            result[code] = val
    return result


def merge_elements(lists: list[list[dict]]) -> dict[str, dict]:
    """Merge multiple element lists by OSM key, combining tags."""
    merged: dict[str, dict] = {}
    for elements in lists:
        for el in elements:
            key = element_key(el)
            if key not in merged:
                merged[key] = el
            else:
                # Merge tags (second occurrence may have extra language tags)
                merged[key]["tags"].update(el.get("tags", {}))
    return merged


def osm_type_rank(el: dict) -> int:
    """Lower rank = preferred representative for deduplication."""
    t = el["type"]
    # Prefer: relation > node > way
    # (relations represent the whole feature; nodes are authoritative for points)
    return {"relation": 0, "node": 1, "way": 2}.get(t, 3)


def build_rows(merged: dict[str, dict]) -> list[dict]:
    # Build candidate rows first, then deduplicate by (name_en, native_names_key)
    candidates: dict[tuple, dict] = {}  # dedup_key -> best row

    for key, el in merged.items():
        tags = el.get("tags", {})
        ftype = feature_type(tags)

        # Filter: keep only meaningful feature types
        if ftype not in KEEP_FEATURE_TYPES:
            continue

        name_en = tags.get("name:en", tags.get("name", ""))
        name_primary = tags.get("name", "")

        # Collect all native name evidence
        natives = native_names(tags)

        # Also treat primary name as a native name if it differs from name:en
        # and no explicit native tag accounts for it
        primary_is_native = (
            name_primary
            and name_en
            and name_primary != name_en
            and not any(name_primary == v for v in natives.values())
            # contains non-ASCII — rough proxy for non-English script
            and any(ord(c) > 127 for c in name_primary)
        )

        if not natives and not primary_is_native:
            continue

        # Format native names column
        native_parts = []
        for code, val in natives.items():
            lang = INDIGENOUS_LANGS[code]
            native_parts.append(f"{val} [{lang}]")
        if primary_is_native and not natives:
            native_parts.append(f"{name_primary} [embedded in name]")

        native_names_str = " | ".join(native_parts)
        langs_str = ", ".join(INDIGENOUS_LANGS[c] for c in natives)

        # Dedup key: same English name = same real-world feature
        # (native name sets may differ between node and relation for the same place)
        dedup_key = name_en.strip().lower()

        row = {
            "osm_id": key,
            "feature_type": ftype,
            "name_en": name_en,
            "_natives": dict(natives),   # {code: value} — merged across duplicates
            "_primary_native": name_primary if (primary_is_native and not natives) else None,
            "_el": el,
        }

        if dedup_key not in candidates:
            candidates[dedup_key] = row
        else:
            existing = candidates[dedup_key]
            # Merge native name tags (union)
            existing["_natives"].update(natives)
            if row["_primary_native"] and not existing["_primary_native"]:
                existing["_primary_native"] = row["_primary_native"]
            # Prefer the better OSM element type
            if osm_type_rank(el) < osm_type_rank(existing["_el"]):
                existing["_el"] = el
                existing["osm_id"] = key
                existing["feature_type"] = ftype
                existing["name_en"] = name_en

    # Finalise: render native_names and languages from merged data
    rows = []
    for row in candidates.values():
        merged_natives = row["_natives"]
        native_parts = [f"{v} [{INDIGENOUS_LANGS[c]}]" for c, v in merged_natives.items()]
        if row["_primary_native"] and not merged_natives:
            native_parts.append(f"{row['_primary_native']} [embedded in name]")
        if not native_parts:
            continue
        rows.append({
            "osm_id": row["osm_id"],
            "feature_type": row["feature_type"],
            "name_en": row["name_en"],
            "native_names": " | ".join(native_parts),
            "languages": ", ".join(INDIGENOUS_LANGS[c] for c in merged_natives),
            "osm_url": osm_url(row["osm_id"]),
        })

    # Sort: feature type category, then English name
    rows.sort(key=lambda r: (r["feature_type"], r["name_en"].lower()))
    return rows


# ── Output ────────────────────────────────────────────────────────────────────

OSM_BASE = "https://www.openstreetmap.org"

def osm_url(osm_id: str) -> str:
    etype, eid = osm_id.split("/")
    return f"{OSM_BASE}/{etype}/{eid}"


COLUMNS = ["osm_id", "feature_type", "name_en", "native_names", "languages", "osm_url"]
SEP = "\t"


def write_table(rows: list[dict], file=sys.stdout):
    # Header
    print(SEP.join(COLUMNS), file=file)
    for row in rows:
        print(SEP.join(str(row[c]) for c in COLUMNS), file=file)


def print_summary(rows: list[dict]):
    by_lang: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    for row in rows:
        for lang in row["languages"].split(", "):
            if lang:
                by_lang[lang] += 1
        by_type[row["feature_type"]] += 1

    print(f"\n{'─'*60}")
    print(f"Total features: {len(rows)}")
    print(f"\nBy language:")
    for lang, count in sorted(by_lang.items(), key=lambda x: -x[1]):
        print(f"  {count:4d}  {lang}")
    print(f"\nBy feature type (top 15):")
    for ftype, count in sorted(by_type.items(), key=lambda x: -x[1])[:15]:
        print(f"  {count:4d}  {ftype}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Querying Overpass API...")
    geo_elements = run_query("Q1 geographic name≠name:en", QUERY_GEOGRAPHIC)
    native_elements = run_query("Q2 indigenous language tags", QUERY_NATIVE_TAGS)

    print("\nMerging and filtering...")
    merged = merge_elements([geo_elements, native_elements])
    rows = build_rows(merged)

    print_summary(rows)

    out_path = "placenames.tsv"
    with open(out_path, "w", encoding="utf-8") as f:
        write_table(rows, file=f)
    print(f"\nWrote {len(rows)} rows to {out_path}")

    # Also print to stdout
    print()
    write_table(rows)


if __name__ == "__main__":
    main()

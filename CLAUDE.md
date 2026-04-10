# overpass-native-placenames

> For general audience documentation see `README.md`. For development history and rationale see `transcript.md`.

Python scripts that query OpenStreetMap via the Overpass API to extract Washington state place names that have indigenous / non-English language names.

## Scripts

| Script | Run with | Purpose |
|--------|----------|---------|
| `placenames.py` | `python3 placenames.py` | Main script: queries Overpass, writes `placenames.tsv` |
| `languages.py` | `python3 languages.py` | Frequency table of languages from TSV |
| `query.py` | `python3 query.py` | Exploratory: Q1 (name≠name:en), writes `raw_results.json` |
| `query2.py` | `python3 query2.py` | Exploratory: Q2 (indigenous language tags), writes `raw_results2.json` |

No dependencies beyond the Python standard library.

## Output columns

`placenames.tsv`: `osm_id`, `feature_type`, `name_en`, `native_names`, `languages`, `osm_url`

## Query strategy

Two complementary Overpass queries are merged:

1. **Q1** — geographic features (`place`, `natural`, `waterway`, `boundary`) where `name != name:en`
2. **Q2** — any element with an explicit indigenous language tag (`name:lut`, `name:clm`, `name:nez`, etc.)

Q1 catches names embedded in the primary `name` tag (e.g. `Mount Si / q̓əlbc̓`).
Q2 catches features whose primary name is English but a native variant is tagged separately (e.g. `Mount Rainier` + `name:lut=Tahoma`).

## Deduplication

OSM represents rivers and roads as many way segments, and cities as both a node and a relation. Dedup groups by `name_en` (case-insensitive), merges all `name:xx` tags across duplicates, and prefers `relation > node > way` as the representative element.

## Indigenous language codes (ISO 639-3)

`clm` Klallam · `lut` Lushootseed · `nez` Nez Perce · `oka` Okanagan-Colville · `myh` Makah · `twa` Twana/Skokomish · `chn` Chinook Jargon · `str` Straits Salish · `spo` Spokane · `fla` Kalispel-Pend d'Oreilles · `yak` Yakama · `wac` Wishram-Wasco · `cjh` Upper Chehalis · `qun` Quinault · `psc` Colville

## API notes

- All scripts send `User-Agent: overpass-native-placenames/1.0 (github research; halmueller@gmail.com)`
- HTTP 429 is retried up to twice with 60s / 120s backoff
- No artificial inter-query delay needed for normal single runs (2 queries total)
- Each Overpass query carries `[timeout:300]`

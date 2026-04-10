# Session Transcript: OSM Native Place Names for Washington State

## Goal

Build a Python script that queries OpenStreetMap via the Overpass API and produces a table of all places in Washington state that have a non-English (specifically indigenous) name.

---

## Step 1: Planning the query strategy

Two complementary signals in OSM for non-English names:

- **`name` ≠ `name:en`** — when both tags exist and differ, the primary name is likely non-English
- **`name:xx` language tags** — explicit per-language name variants (e.g., `name:lut`, `name:clm`)

Identified relevant ISO 639-3 codes for Pacific Northwest indigenous languages:

| Code | Language |
|------|----------|
| `clm` | Klallam |
| `lut` | Lushootseed |
| `nez` | Nez Perce |
| `oka` | Okanagan-Colville |
| `myh` | Makah |
| `twa` | Twana / Skokomish |
| `chn` | Chinook Jargon |
| `str` | Straits Salish |
| `spo` | Spokane |
| `fla` | Kalispel-Pend d'Oreilles |
| `yak` | Yakama |
| `wac` | Wishram-Wasco |
| `cjh` | Upper Chehalis |
| `qun` | Quinault |
| `psc` | Colville |

---

## Step 2: `query.py` — exploratory Q1

Ran `name != name:en` against all element types in Washington state. Returned 193 elements — mostly **business noise** (QFC vs. "Quality Food Center", Vietnamese restaurants, etc.). A few genuine geographic hits:

- `Mount Si / q̓əlbc̓` — Lushootseed name embedded in the primary `name` tag
- `Quil Ceda Village / qʷəl'sidəʔ ʔalʔaltəd`

Key finding: the `name != name:en` query needs to be scoped to geographic feature types to be useful.

---

## Step 3: `query2.py` — exploratory Q2

Queried for any element with a `name:xx` tag matching the indigenous language code list. Returned 178 elements across 9 languages:

- `name:lut` — 68 elements (Lushootseed, dominated by Puyallup tribal streets)
- `name:nez` — 62 elements (Nez Perce, eastern WA towns and rivers)
- `name:clm` — 32 elements (Klallam, Lower Elwha tribal streets near Port Angeles)
- `name:myh` — 6 (Makah, Neah Bay area)
- `name:chn` — 5 (Chinook Jargon: Vancouver, Walla Walla, Lake Washington)
- `name:str` — 3 (Straits Salish: Mount Baker, Cherry Point, NW Indian College)
- `name:yak` — 2 (Yakama: Mount Adams = Pahto, Mount Saint Helens = Loowit)
- `name:oka` — 1 (Colville Indian Reservation)
- `name:spo` — 1 (Tribal Gathering Place, Spokane)

Notable finds: Mount Rainier (`name:lut=Tahoma`), Seattle (`name:lut=dᶻidᶻəlal̕ič`), Walla Walla has both Nez Perce (`páasx̂a`) and Chinook Jargon (`walawala`) names.

---

## Step 4: `placenames.py` — combined production script

Merged both queries, with these design decisions:

**Filtering**: Keep only meaningful geographic/cultural feature types (`place=*`, `natural=*`, `waterway=*`, `highway=*`, `leisure=park`, etc.). Drop businesses and generic amenities.

**Deduplication**: OSM represents the same feature as multiple elements:
- A river is split into dozens of way segments, each tagged identically
- A city exists as both a node (point) and a relation (boundary)

Dedup strategy: group by `name_en` (case-insensitive), merge all `name:xx` tags across duplicates, prefer `relation > node > way` as the representative OSM element.

**Output**: TSV with columns `osm_id`, `feature_type`, `name_en`, `native_names`, `languages`, `osm_url`.

Final result: **66 unique features** across 8 languages.

---

## Step 5: API hygiene

Added to all three scripts:
- `User-Agent: overpass-native-placenames/1.0 (github research; halmueller@gmail.com)`
- HTTP 429 retry with 60s / 120s backoff (up to 3 attempts)

No deliberate inter-query delay needed — only 2 queries per run, and the Overpass slot system self-regulates.

---

## Step 6: Auxiliary scripts

**`languages.py`** — reads `placenames.tsv` and prints a frequency table by language. Accepts an optional filename argument.

```
Language                       Features
----------------------------------------
Klallam                              27
Lushootseed                          17
Nez Perce                             9
Makah                                 6
Straits Salish                        3
Chinook Jargon                        3
Yakama                                2
Spokane                               1
```

---

## Step 7: Documentation

After the scripts were working, the question was what to save for an audience that doesn't use Claude Code. Decisions made:

**Write `README.md`** (standard entry point for any repo) covering:
- How to run the scripts
- Output column schema
- Caveats — OSM coverage reflects what volunteers have tagged, not a complete inventory; languages with active tagging projects are over-represented; deduplication by English name has edge cases
- Data freshness — `placenames.tsv` is a snapshot; re-run `placenames.py` for current data
- How to contribute — add missing names to OSM directly using `name:xx` tags, with links to OSM wiki

**Keep `transcript.md`** (this file) — a development log showing what was tried, what failed, and why decisions were made. Useful for anyone who wants to understand or extend the approach.

**`CLAUDE.md`** is the operational reference for Claude Code specifically — commands, architecture, dedup logic. Not the right place for general audience documentation.

Items considered but not created:
- Renaming `transcript.md` to `METHODOLOGY.md` — decided against; keeping the name honest about its origin
- A separate data dictionary — absorbed into the README output table

---

## Files

| File | Purpose |
|------|---------|
| `query.py` | Exploratory: Q1 name≠name:en, dumps raw JSON |
| `query2.py` | Exploratory: Q2 indigenous language tags, grouped output |
| `placenames.py` | Production: runs both queries, merges, deduplicates, writes TSV |
| `languages.py` | Post-processing: language frequency table from TSV |
| `placenames.tsv` | Output: 66 features, 6 columns including OSM URLs |
| `raw_results.json` | Cached Q1 results |
| `raw_results2.json` | Cached Q2 results |
| `README.md` | General audience documentation |
| `CLAUDE.md` | Claude Code operational reference |
| `transcript.md` | This file — development log |

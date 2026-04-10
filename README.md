# OSM Native Place Names — Washington State

Python scripts that query [OpenStreetMap](https://www.openstreetmap.org) via the [Overpass API](https://overpass-api.de) to extract Washington state place names that have documented indigenous language names.

No external dependencies — standard library only.

## Quick start

```sh
python3 placenames.py          # query Overpass, write placenames.tsv
python3 languages.py           # frequency table by language
```

## Output

`placenames.tsv` — tab-separated, UTF-8, one row per unique feature:

| Column | Description |
|--------|-------------|
| `osm_id` | OSM element type and ID, e.g. `relation/237385` |
| `feature_type` | OSM tag describing the feature, e.g. `place=city` |
| `name_en` | English name |
| `native_names` | One or more native names with language label, e.g. `Tahoma [Lushootseed]` |
| `languages` | Comma-separated list of languages present |
| `osm_url` | Direct link to the OSM element |

## Caveats

**These results reflect what OSM volunteers have tagged, not a complete inventory.**

- Languages with active tagging projects (Lushootseed, Klallam, Nez Perce) are well-represented. Many other Washington languages have little or no OSM coverage.
- Some indigenous names appear in OSM only as the primary `name` tag with no English translation; others exist only as a `name:xx` sidecar. Both patterns are captured here.
- OSM data quality varies. A few entries show signs of informal or inconsistent tagging (e.g. `Sto-Lit-Qua-Mish River` as a Lushootseed name for the Stillaguamish, which is itself a transliteration of the indigenous name).
- The script targets 15 ISO 639-3 language codes. Languages tagged under different or non-standard codes will be missed.
- The deduplication strategy groups by English name. Two genuinely distinct features with identical English names would be incorrectly merged.

## Data freshness

`placenames.tsv` is a snapshot generated at a point in time. OSM is a live database — names are added and corrected continuously. Re-run `placenames.py` to get current data.

## How to contribute

If you know of a missing indigenous name for a Washington place, the right place to add it is OpenStreetMap itself, under the appropriate `name:xx` tag. This makes the data available to everyone, not just this project.

- [OSM Beginner's Guide](https://wiki.openstreetmap.org/wiki/Beginners%27_guide)
- [OSM wiki: Multilingual names](https://wiki.openstreetmap.org/wiki/Multilingual_names)
- [OSM wiki: Key:name](https://wiki.openstreetmap.org/wiki/Key:name)

## Background and methodology

See `transcript.md` for a full account of how these scripts were developed, including what queries were tried, what noise was encountered, and the reasoning behind the filtering and deduplication approach.

## Files

| File | Purpose |
|------|---------|
| `placenames.py` | Main script: queries Overpass, merges results, writes TSV |
| `languages.py` | Post-processing: language frequency table from TSV |
| `query.py` | Exploratory: Q1 (name≠name:en), dumps raw JSON |
| `query2.py` | Exploratory: Q2 (indigenous language tags), grouped output |
| `placenames.tsv` | Output snapshot |
| `raw_results.json` | Cached Q1 results |
| `raw_results2.json` | Cached Q2 results |
| `transcript.md` | Development log |

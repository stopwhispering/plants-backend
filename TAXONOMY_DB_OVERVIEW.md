# Taxonomy & Biodiversity Database Overview

> Generated: 2026-07-04  
> Purpose: Identify deprecated libraries, overlapping data sources, and guide restructuring of database access.

---

## Summary Table

> **Legend:** ⚠️ = deprecated library &nbsp;|&nbsp; 💀 = dead / unreachable code &nbsp;|&nbsp; ✅ = active

| # | Database | Status | Access Method | Library / Protocol | Primary Data Retrieved | Used Where |
|---|---|---|---|---|---|---|
| 1 | IPNI | ✅ active | External API | `pykew` (custom fork) ⚠️ | Taxon names, LSID, ranks, hybrid status | `taxonomy_search.py` |
| 2 | POWO | ✅ active | Direct HTTP | `requests` | Taxonomic status, authors, basionym, synonyms, distribution (concat string) | `taxonomy_search.py` |
| 2b | POWO | 💀 dead code | pykew library | `pykew.powo` ⚠️ | Distribution (native/introduced areas, TDWG codes) | `taxon/services.py` lines 104–127 |
| 3 | GBIF | ✅ active | External API | `pygbif` + `aiohttp` | GBIF taxon ID (nubKey), occurrence images + metadata | `lookup_gbif_id.py`, `taxonomy_occurence_images.py` |
| 4 | Wikidata | ✅ active | Web scrape + API | `aiohttp` + `beautifulsoup4` + `wikidata` ⚠️ | GBIF ID (fallback via LSID cross-reference) | `lookup_gbif_id.py` |
| 5 | WCVP | ✅ active | Local SQLite | `sqlite3` | Distribution (native/introduced, TDWG L3 codes) | `taxon/services.py` |

### Deprecated Libraries
| Library | Version | Status | Notes |
|---|---|---|---|
| `pykew` | git fork | ⚠️ Deprecated upstream | Custom fork of an ~8-year-old unmaintained library. IPNI module still in active use (§1). POWO module is dead code (§2b). |
| `wikidata` | ^0.7.0 | ⚠️ Reportedly broken | Python client was reportedly defective at implementation time; HTML scraping used as workaround. Current status unknown. |

### Dead Code
| Location | Dead Code | Reason |
|---|---|---|
| `taxon/services.py` lines 104–127 | `powo.lookup(lsid, include=["distribution"])` and downstream parsing | Unreachable: sits after an unconditional `return` in `_retrieve_locations()`. Was the original POWO-based distribution fetch, replaced by WCVP (§5) but never deleted. |
| `taxon/services.py` line 7 | `from pykew import powo` | Import only used by the dead code block above. |

---

## 1. IPNI — International Plant Names Index

**Website:** https://www.ipni.org  
**Library:** `pykew` — custom fork at https://github.com/stopwhispering/pykew.git  
**pyproject.toml:** `pykew = { git = "https://github.com/stopwhispering/pykew.git" }`  
**Note:** pykew is lightly maintained (~8 years without upstream updates).

### Example Call
```python
from pykew import ipni
from pykew.ipni_terms import Filters

ipni_search = ipni.search("Aloe vera", filters=[Filters.specific, Filters.infraspecific])
for result in ipni_search:
    print(result["fqId"], result["name"], result["rank"])
```

### Retrieved Information
| Field | Description |
|---|---|
| `fqId` | IPNI Life Sciences Identifier (LSID), e.g. `urn:lsid:ipni.org:names:77095488-1` |
| `name` | Full taxon name |
| `rank` | Taxonomic rank (e.g. `Species`, `Genus`, `Subspecies`, `Variety`, `Forma`) |
| `family` | Family name |
| `genus` | Genus name |
| `species` | Species epithet |
| `infraspecies` | Infraspecific epithet (if applicable) |
| `hybrid` | Boolean: is a hybrid |
| `hybridGenus` | Boolean: hybrid genus |
| `publicationYear` | Year of name publication |
| `inPowo` | Boolean: whether the name is present in POWO |

### Used Where
- **File:** `plants/modules/biodiversity/taxonomy_search.py`
- **Class/Method:** `ApiSearcher._search_taxa_in_ipni_api()`
- **Trigger:** Called during taxon search when `include_external_apis=True`
- **Flow:** `TaxonomySearch.search()` → `ApiSearcher.search_taxa_in_external_apis()` → `_search_taxa_in_ipni_api()`

---

## 2. POWO — Plants of the World Online

**Website:** https://powo.science.kew.org  
**Access:** Direct HTTP REST API (undocumented)  
**Library:** `requests`  
**Note:** Previously accessed via `pykew.powo` — replaced by direct HTTP requests after POWO returned 403 errors. pykew's POWO module is no longer used in active code paths (see §2b below).

### Example Call (active)
```python
import requests

resp = requests.get(
    f"https://powo.science.kew.org/api/2/taxon/{lsid}",
    params={"fields": "distribution"},
    headers={"User-Agent": "your-app-name/1.0 (contact@example.com)"},
    timeout=10,
)
powo_lookup = resp.json()
```

### Retrieved Information
| Field | Description |
|---|---|
| `taxonomicStatus` | e.g. `Accepted`, `Synonym` |
| `authors` | Author citation string |
| `synonym` | Boolean |
| `basionym.name` | Basionym name (if applicable) |
| `distribution.natives[]` | List of native distribution areas |
| `distribution.introduced[]` | List of introduced distribution areas |

Distribution is parsed into a concatenated string (`synonyms_concat`, `distribution_concat`) stored on the `Taxon` model.

### Used Where
- **File:** `plants/modules/biodiversity/taxonomy_search.py`
- **Class/Method:** `ApiSearcher._update_taxon_from_powo_api()`
- **Trigger:** Called for every IPNI result during external API search, to enrich with POWO data
- **Flow:** `ApiSearcher.search_taxa_in_external_apis()` → `_update_taxon_from_powo_api()`
- **Helper:** `plants/modules/biodiversity/taxonomy_shared_functions.py` — `get_accepted_synonym_label()`, `get_concatenated_distribution()`

---

## 2b. POWO via pykew ⚠️ DEAD CODE

**Library:** `pykew.powo`  
**pyproject.toml:** included via the `pykew` git dependency

### Example Call (legacy)
```python
from pykew import powo

powo_lookup = powo.lookup(lsid, include=["distribution"])
```

### Status
This code path is **unreachable dead code** in `plants/modules/taxon/services.py`:

```python
async def _retrieve_locations(lsid: str) -> list[Distribution]:
    return await run_in_threadpool(_lookup_locations_sync, lsid)  # <-- returns here

    # Lines 104–127 below are NEVER reached:
    powo_lookup = await run_in_threadpool(powo.lookup, lsid, include=["distribution"])
    ...
```

The `powo.lookup`-based distribution retrieval was replaced by the WCVP SQLite lookup (see §4) but the old code was not removed. The `from pykew import powo` import in `services.py` is only used by this dead code.

---

## 3. GBIF — Global Biodiversity Information Facility

**Website:** https://www.gbif.org  
**Library:** `pygbif` (^0.6.2) for API queries; `aiohttp` (3.13.3) for async image downloads  
**REST API base:** https://api.gbif.org/v1/

GBIF is used for two distinct purposes: (a) resolving the GBIF taxon ID (nubKey) from an IPNI LSID, and (b) fetching occurrence records with associated images.

### 3a. GBIF ID Lookup

#### Example Calls
```python
from pygbif import species

IPNI_DATASET_KEY = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"

# Primary: PyGBIF name lookup in IPNI dataset
lookup = species.name_lookup(q=taxon_name, datasetKey=IPNI_DATASET_KEY)
gbif_id = lookup["results"][0]["nubKey"]

# Fallback: direct REST API call to verify via taxonID (LSID)
import aiohttp
# example: https://api.gbif.org/v1/species/9527904/related?datasetKey=046bbc50-cae2-47ff-aa43-729fbf53f7c5 (Aloiampelos ciliaris)
url = f"https://api.gbif.org/v1/species/{nub_key}/related?datasetKey={IPNI_DATASET_KEY}"
async with aiohttp.ClientSession() as session, session.get(url) as response:
    data = await response.json()
```

#### Retrieved Information
- `nubKey` — GBIF's internal taxon identifier (used for all subsequent GBIF queries)

#### Used Where
- **File:** `plants/modules/biodiversity/lookup_gbif_id.py`
- **Class/Method:** `GBIFIdentifierLookup.lookup()` → `_gbif_id_from_gbif_api()` + `_gbif_id_from_rest_api()`
- **Trigger:** Called during `save_new_taxon()` in `taxon/services.py` for non-custom taxa

### 3b. GBIF Occurrence Images

#### Example Call
```python
from pygbif import occurrences as occ_api

occ_search = occ_api.search(taxonKey=gbif_id, mediaType="StillImage")
for occ in occ_search["results"]:
    for media in occ["media"]:
        image_url = media.get("identifier") or media.get("references")
        # then download via aiohttp
```

#### Retrieved Information
| Field | Description |
|---|---|
| `key` | Occurrence ID |
| `scientificName` | Scientific name from occurrence record |
| `basisOfRecord` | e.g. `HUMAN_OBSERVATION` (PRESERVED_SPECIMEN filtered out) |
| `verbatimLocality` / `locality` | Observation location description |
| `countryCode`, `stateProvince` | Geographic context |
| `eventDate` | Date of observation |
| `media[].identifier` / `media[].references` | Image URL |
| `media[].creator` / `recordedBy` | Photographer |
| `media[].created` | Photo date |
| `publisher` / `institutionCode` / `datasetName` | Publishing institution |
| `references` | Link back to source record |

Images are downloaded via `aiohttp`, then thumbnailed with `Pillow` and stored locally. Metadata is persisted in `TaxonOccurrenceImage` and `TaxonToOccurrenceAssociation` database tables.

#### Used Where
- **File:** `plants/modules/biodiversity/taxonomy_occurence_images.py`
- **Class/Method:** `TaxonOccurencesLoader.scrape_occurrences_for_taxon()`
- **Trigger:** Launched as a FastAPI background task after saving a new taxon (`taxon/services.py` → `save_new_taxon()`)

---

## 4. Wikidata

**Website:** https://www.wikidata.org  
**Access:** HTML scraping via `aiohttp` + `beautifulsoup4`; structured data via `wikidata` Python client  
**Libraries:** `wikidata` (^0.7.0), `beautifulsoup4` (^4.11.2), `aiohttp` (3.13.3)  
**Note:** Used as fallback when GBIF cannot be found directly via `pygbif`. The Wikidata API was reportedly defective at the time of implementation, hence the HTML scraping approach.

### Example Call
```python
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup
from wikidata.client import Client

# 1. Scrape search results page
lsid_number = "77095488-1"
search_url = f"https://www.wikidata.org/w/index.php?search={urllib.parse.quote(lsid_number)}"
async with aiohttp.ClientSession() as session, session.get(search_url) as response:
    soup = BeautifulSoup(await response.text(), "html.parser")

# 2. Extract Wikidata entity ID (e.g. Q15482666) from HTML
# 3. Fetch entity claims via wikidata client
entity = Client().get("Q15482666", load=True)
claims = entity.data["claims"]
gbif_id = claims["P846"][0]["mainsnak"]["datavalue"]["value"]
```

### Wikidata Properties Used
| Property ID | Meaning |
|---|---|
| `P961` | IPNI identifier |
| `P846` | GBIF taxon ID |
| `P5037` | POWO identifier |

### Retrieved Information
- GBIF taxon ID (`P846`) — cross-referenced against IPNI LSID (`P961`) or POWO ID (`P5037`) to verify correctness

### Used Where
- **File:** `plants/modules/biodiversity/lookup_gbif_id.py`
- **Class/Method:** `WikidataGbifLookup.lookup()`
- **Trigger:** Fallback in `lookup_gbif_id()` function when `GBIFIdentifierLookup` returns `None`
- **Flow:** `taxon/services.py` → `lookup_gbif_id(taxon_name, lsid)` → tries `GBIFIdentifierLookup` first, then `WikidataGbifLookup`

---

## 5. WCVP — World Checklist of Vascular Plants

**Website:** https://wcvp.science.kew.org  
**Access:** Local SQLite database (`wcvp.sqlite` in project root)  
**Download Script:** `scripts/download_bulk_wcvp.py`  
**Download URL:** `https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip`  
**Library:** Python built-in `sqlite3`

The WCVP bulk data (CSV files: `wcvp_names.csv`, `wcvp_distribution.csv`) is downloaded and imported into a local SQLite database. The DB has two tables:

```sql
CREATE TABLE names (
    plant_name_id INTEGER PRIMARY KEY,
    ipni_id TEXT,
    accepted_plant_name_id INTEGER
);
CREATE TABLE distribution (
    plant_name_id INTEGER, area TEXT, area_code_l3 TEXT,
    introduced INTEGER, extinct INTEGER, location_doubtful INTEGER
);
```

### Example Call
```python
import sqlite3

con = sqlite3.connect("wcvp.sqlite")
cur = con.cursor()

# Resolve LSID to plant_name_id (following synonym chain)
name_row = cur.execute(
    "SELECT plant_name_id, accepted_plant_name_id FROM names WHERE ipni_id = ?",
    ("77095488-1",)
).fetchone()

target_id = name_row["accepted_plant_name_id"] or name_row["plant_name_id"]

dist_rows = cur.execute(
    "SELECT area, area_code_l3, introduced FROM distribution WHERE plant_name_id = ?",
    (target_id,)
).fetchall()
```

### Retrieved Information
| Field | Description |
|---|---|
| `area` | Human-readable area name (e.g. `South Africa`) |
| `area_code_l3` | WGSRPD Level-3 code (e.g. `CPP`) |
| `introduced` | `1` = introduced, `0` = native |
| `extinct` | `1` = extinct |
| `location_doubtful` | `1` = uncertain record |

Results are mapped to `Distribution` ORM model objects and stored in the local database when a new taxon is saved.

### Used Where
- **File:** `plants/modules/taxon/services.py`
- **Functions:** `_lookup_locations_sync()` (sync SQLite query), `_retrieve_locations()` (async wrapper)
- **Trigger:** Called during `save_new_taxon()` for non-custom taxa to populate the `Distribution` table
- **Flow:** `save_new_taxon()` → `_retrieve_locations(lsid)` → `_lookup_locations_sync(lsid)`

---

## Call Flow Summary (New Taxon Save)

```
POST /taxon (frontend search result selected)
  └── save_new_taxon()  [taxon/services.py]
        ├── _retrieve_locations(lsid)
        │     └── _lookup_locations_sync(lsid)  ──► WCVP SQLite (§5)
        │
        ├── lookup_gbif_id(taxon_name, lsid)  [lookup_gbif_id.py]
        │     ├── GBIFIdentifierLookup.lookup()  ──► GBIF API via pygbif (§3a)
        │     │     └── fallback: GBIF REST API via aiohttp (§3a)
        │     └── WikidataGbifLookup.lookup()  ──► Wikidata scrape (§4)  [if GBIF failed]
        │
        └── (background task) TaxonOccurencesLoader.scrape_occurrences_for_taxon(gbif_id)
              └── occ_api.search()  ──► GBIF Occurrences via pygbif (§3b)
                    └── aiohttp download + Pillow thumbnail for each image

GET /taxon/search?taxon_name=...&include_external_apis=true
  └── TaxonomySearch.search()  [taxonomy_search.py]
        ├── _query_taxa_in_local_database()  ──► local PostgreSQL DB
        └── ApiSearcher.search_taxa_in_external_apis()
              ├── _search_taxa_in_ipni_api()  ──► IPNI via pykew (§1)
              └── _update_taxon_from_powo_api()  ──► POWO direct HTTP (§2)
```

---

## Observations / Potential Issues

| # | Issue | Details |
|---|---|---|
| 1 | **Dead code** | `pykew.powo` import and powo-based distribution code in `taxon/services.py` lines 104–127 is unreachable after early `return`. The import `from pykew import powo` at line 7 is also unused. |
| 2 | **Deprecated library** | `pykew` is a custom fork of a library that has not been maintained for ~8 years. The IPNI module is still in active use; the POWO module is dead code. |
| 3 | **POWO API undocumented** | The direct POWO HTTP API (`powo.science.kew.org/api/2/taxon/...`) is undocumented and can change without notice (noted in code comments). The `requests` call uses a generic User-Agent. |
| 4 | **Wikidata scraping** | HTML scraping of Wikidata is fragile. The `wikidata` Python library was reportedly broken at time of implementation — current status unknown. |
| 5 | **Distribution overlap** | Distribution data is sourced from **two places**: POWO API (as `distribution_concat` text string on `Taxon`) and WCVP SQLite (as structured `Distribution` rows). These serve different purposes but the data comes from the same upstream source (Kew). |
| 6 | **WCVP manual refresh** | The WCVP SQLite database must be manually refreshed by re-running `scripts/download_bulk_wcvp.py`. There is no automated update mechanism. |
| 7 | **Blocking calls in async context** | `pygbif` is a blocking library; `pykew` is also synchronous. Both are wrapped with `run_in_threadpool` to avoid blocking the async event loop. |


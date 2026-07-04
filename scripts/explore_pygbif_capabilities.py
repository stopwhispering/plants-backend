"""
explore_pygbif_capabilities.py
==============================
Investigates what data pygbif can provide for a sample taxon (Haworthia truncata,
GBIF nubKey 8097702), with the goal of assessing whether pygbif can replace one or
more of the current external data sources:

  Current stack                    Potentially replaced by pygbif?
  ─────────────────────────────    ───────────────────────────────
  IPNI   (pykew)                   § Search / name lookup
  POWO   (direct HTTP)             § Taxonomic status, authors, basionym, synonyms, distribution
  WCVP   (local SQLite)            § Distribution (structured, TDWG codes)
  Wikidata (scraping + wikidata)   § LSID → GBIF ID cross-reference
  GBIF   (already used)            ── (keep)

Run from project root:
    python scripts/explore_pygbif_capabilities.py
"""
from __future__ import annotations

import pprint
import sys
import textwrap
from typing import Any

# Ensure UTF-8 output even on Windows terminals (box-drawing chars in summary)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from pygbif import occurrences as occ_api
from pygbif import species as sp_api

# ── Constants ──────────────────────────────────────────────────────────────────
HAWORTHIA_TRUNCATA_GBIF_NUB_KEY = 8097702
HAWORTHIA_TRUNCATA_LSID = "urn:lsid:ipni.org:names:77095488-1"
HAWORTHIA_TRUNCATA_LSID_SHORT = "77095488-1"   # the part after the last ':'

IPNI_DATASET_KEY = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"

GBIF_REST_BASE = "https://api.gbif.org/v1"

SEP = "─" * 78


def header(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def dump(label: str, data: Any, indent: int = 2) -> None:
    print(f"\n▶ {label}:")
    if isinstance(data, (dict, list)):
        print(textwrap.indent(pprint.pformat(data, width=100), " " * indent))
    else:
        print(f"  {data!r}")


def rest_get(path: str, **params: Any) -> Any:
    url = f"{GBIF_REST_BASE}/{path}"
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
# § 1  NAME SEARCH — can pygbif replace IPNI (pykew) for taxon name discovery?
# ══════════════════════════════════════════════════════════════════════════════
header("§ 1  NAME SEARCH  —  can pygbif replace IPNI (pykew)?")

# 1a  name_backbone: fuzzy match against GBIF backbone taxonomy
# NOTE: pygbif 0.6.x uses scientificName/taxonRank (not name/rank)
print("\n[1a] species.name_backbone(scientificName='Haworthia truncata', taxonRank='species')")
backbone = sp_api.name_backbone(scientificName="Haworthia truncata", taxonRank="species")
BACKBONE_FIELDS = [
    "usageKey", "scientificName", "canonicalName", "rank", "status",
    "confidence", "matchType", "synonym", "family", "genus", "species",
    "authorship",
]
dump("Backbone result (selected fields)", {k: backbone.get(k) for k in BACKBONE_FIELDS})

# 1b  name_lookup: full-text search (same call used by current GBIF ID lookup code)
print("\n[1b] species.name_lookup('Haworthia truncata', rank='SPECIES')")
lookup = sp_api.name_lookup(q="Haworthia truncata", rank="SPECIES", limit=5)
dump("name_lookup — first 3 results (selected fields)", [
    {k: r.get(k) for k in ["key", "nubKey", "scientificName", "rank", "taxonomicStatus",
                            "taxonID", "datasetKey", "family", "authorship"]}
    for r in lookup.get("results", [])[:3]
])

# 1c  name_lookup restricted to IPNI dataset (same approach as current code)
print(f"\n[1c] species.name_lookup('Haworthia truncata', datasetKey=IPNI_DATASET_KEY)")
lookup_ipni = sp_api.name_lookup(
    q="Haworthia truncata", datasetKey=IPNI_DATASET_KEY, limit=5
)
dump("IPNI-dataset lookup — first 3 results", [
    {k: r.get(k) for k in ["key", "nubKey", "scientificName", "rank", "taxonomicStatus",
                            "taxonID", "family", "authorship"]}
    for r in lookup_ipni.get("results", [])[:3]
])

# 1d  name_suggest: auto-complete style endpoint
print("\n[1d] species.name_suggest('Haworthia trun')")
suggest = sp_api.name_suggest(q="Haworthia trun", limit=5)
dump("name_suggest results", [
    {k: r.get(k) for k in ["key", "scientificName", "rank", "status"]}
    for r in suggest[:5]
])


# ══════════════════════════════════════════════════════════════════════════════
# § 2  TAXON DETAILS — can pygbif replace POWO (authors, basionym, synonyms)?
# ══════════════════════════════════════════════════════════════════════════════
header("§ 2  TAXON DETAILS  —  can pygbif replace POWO?")

# 2a  Full name_usage for the nubKey
print(f"\n[2a] species.name_usage(key={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY})")
usage = sp_api.name_usage(key=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY)
USAGE_FIELDS = [
    "key", "nubKey", "taxonID",  # taxonID = IPNI LSID!
    "scientificName", "canonicalName", "rank", "taxonomicStatus",
    "authorship", "publishedIn", "namePublishedInYear",
    "basionymKey", "basionym",
    "family", "genus", "species", "infraspecificEpithet",
    "synonym", "accordingTo",
    "numDescendants", "numOccurrences",
]
dump("name_usage — selected fields", {k: usage.get(k) for k in USAGE_FIELDS if k in usage})
dump("name_usage — ALL keys present", sorted(usage.keys()))

# 2b  taxonID field — is it the IPNI LSID we rely on?
taxon_id = usage.get("taxonID")
print(f"\n[2b] usage['taxonID'] = {taxon_id!r}")
print(f"     Expected LSID    = {HAWORTHIA_TRUNCATA_LSID!r}")
print(f"     Match            = {taxon_id == HAWORTHIA_TRUNCATA_LSID}")

# 2c  Synonyms
print(f"\n[2c] species.name_usage(key={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}, data='synonyms')")
synonyms = sp_api.name_usage(key=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY, data="synonyms")
syn_list = synonyms.get("results", [])
dump(f"Synonyms ({len(syn_list)} found)", [
    {k: s.get(k) for k in ["key", "scientificName", "rank", "taxonomicStatus", "authorship"]}
    for s in syn_list[:10]
])

# 2d  Related name usages (across datasets)
print(f"\n[2d] REST: /species/{HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}/related?datasetKey=IPNI")
related = rest_get(f"species/{HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}/related",
                   datasetKey=IPNI_DATASET_KEY)
dump("Related in IPNI dataset", [
    {k: r.get(k) for k in ["key", "taxonID", "scientificName", "rank",
                            "taxonomicStatus", "authorship"]}
    for r in related.get("results", [])[:5]
])

# 2e  Parsed name (verbose name decomposition)
print(f"\n[2e] REST: /species/{HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}/name")
parsed_name = rest_get(f"species/{HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}/name")
dump("Parsed name object", parsed_name)


# ══════════════════════════════════════════════════════════════════════════════
# § 3  DISTRIBUTION — can pygbif replace POWO/WCVP for distribution data?
# ══════════════════════════════════════════════════════════════════════════════
header("§ 3  DISTRIBUTION  —  can pygbif replace POWO / WCVP?")

# 3a  Distribution endpoint on the species API
print(f"\n[3a] species.name_usage(key={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}, data='distributions')")
distributions = sp_api.name_usage(key=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY, data="distributions")
dist_list = distributions.get("results", [])
dump(f"Distributions ({len(dist_list)} records)", dist_list[:20])
if dist_list:
    dump("Distribution record keys", sorted(dist_list[0].keys()))

# 3b  REST distributions
print(f"\n[3b] REST: /species/{HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}/distributions")
dist_rest = rest_get(f"species/{HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}/distributions")
dist_rest_list = dist_rest.get("results", [])
dump(f"REST distributions ({len(dist_rest_list)} records, first 10)", dist_rest_list[:10])


# ══════════════════════════════════════════════════════════════════════════════
# § 4  LSID → GBIF ID LOOKUP — can pygbif replace the Wikidata fallback?
# ══════════════════════════════════════════════════════════════════════════════
header("§ 4  LSID → GBIF ID LOOKUP  —  can pygbif replace Wikidata?")

# 4a  name_lookup in IPNI dataset by exact LSID (taxonID)
# Current code: lookup by q=name, then match taxonID manually.
# Question: can we search by taxonID directly?
print(f"\n[4a] REST: /species?datasetKey=IPNI&taxonID={HAWORTHIA_TRUNCATA_LSID}")
try:
    by_taxon_id = rest_get("species", datasetKey=IPNI_DATASET_KEY,
                           taxonID=HAWORTHIA_TRUNCATA_LSID, limit=5)
    dump("Search by taxonID in IPNI dataset", by_taxon_id.get("results", []))
except Exception as e:
    print(f"  Error: {e}")

# 4b  backbone lookup — returns nubKey directly from name
print(f"\n[4b] species.name_backbone returns usageKey directly from name string")
backbone2 = sp_api.name_backbone(scientificName="Haworthia truncata", taxonRank="species", strict=True)
dump("Backbone usageKey (= nubKey / GBIF ID)", {
    "usageKey": backbone2.get("usageKey"),
    "matchType": backbone2.get("matchType"),
    "confidence": backbone2.get("confidence"),
    "status": backbone2.get("status"),
})

# 4c  Can we search GBIF by the LSID number alone?
print(f"\n[4c] name_lookup with q=LSID short number '{HAWORTHIA_TRUNCATA_LSID_SHORT}'")
lsid_lookup = sp_api.name_lookup(q=HAWORTHIA_TRUNCATA_LSID_SHORT, limit=5)
dump("Results", [
    {k: r.get(k) for k in ["key", "nubKey", "scientificName", "taxonID", "datasetKey"]}
    for r in lsid_lookup.get("results", [])[:5]
])


# ══════════════════════════════════════════════════════════════════════════════
# § 5  VERNACULAR NAMES & ADDITIONAL METADATA
# ══════════════════════════════════════════════════════════════════════════════
header("§ 5  VERNACULAR NAMES & ADDITIONAL METADATA")

print(f"\n[5a] species.name_usage(key={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}, data='vernacularNames')")
vernacular = sp_api.name_usage(key=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY, data="vernacularNames")
dump("Vernacular names", vernacular.get("results", [])[:10])

print(f"\n[5b] species.name_usage(key={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}, data='references')")
refs = sp_api.name_usage(key=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY, data="references")
dump("References", refs.get("results", [])[:5])

print(f"\n[5c] species.name_usage(key={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}, data='media')")
media = sp_api.name_usage(key=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY, data="media")
dump("Media (first 3)", media.get("results", [])[:3])


# ══════════════════════════════════════════════════════════════════════════════
# § 6  OCCURRENCE SEARCH (current usage – for reference)
# ══════════════════════════════════════════════════════════════════════════════
header("§ 6  OCCURRENCE SEARCH (current usage – for reference)")

print(f"\n[6a] occurrences.search(taxonKey={HAWORTHIA_TRUNCATA_GBIF_NUB_KEY}, mediaType='StillImage', limit=3)")
occ_search = occ_api.search(
    taxonKey=HAWORTHIA_TRUNCATA_GBIF_NUB_KEY,
    mediaType="StillImage",
    limit=3,
)
results = occ_search.get("results", [])
dump(f"Occurrence count (total): {occ_search.get('count')}", None)
if results:
    first = results[0]
    dump("First occurrence (selected fields)", {
        k: first.get(k) for k in [
            "key", "scientificName", "basisOfRecord", "countryCode",
            "stateProvince", "verbatimLocality", "eventDate",
            "recordedBy", "publisher", "references",
        ]
    })
    first_media = first.get("media", [{}])[0]
    dump("First occurrence — first media object", first_media)


# ══════════════════════════════════════════════════════════════════════════════
# § 7  SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
header("§ 7  SUMMARY — Findings from actual API output")

summary = """
pygbif version tested: 0.6.6
Sample taxon: Haworthia truncata, GBIF nubKey 8097702, LSID urn:lsid:ipni.org:names:77095488-1

────────────────────────────────────────────────────────────────────────────────
FINDING  §1a / §4b  name_backbone — BROKEN in 0.6.6
  All returned fields are None regardless of input. The pygbif 0.6.6 API changed
  its parameter names (scientificName / taxonRank instead of name / rank) but the
  function silently returns an empty result. Cannot be relied on.

FINDING  §1b  name_lookup (general) — WORKS for nubKey resolution
  Returns nubKey=8097702 correctly. taxonID field contains dataset-specific IDs
  (not IPNI LSIDs) for the backbone dataset. Useful for resolving GBIF ID by name.

FINDING  §1c  name_lookup (IPNI dataset) — WORKS for IPNI LSIDs
  Returns IPNI LSIDs (urn:lsid:ipni.org:names:...) in taxonID field.
  BUT: results may miss the exact species hit in top results (returned varieties
  first). Current code already uses this approach (name match + taxonID compare).

FINDING  §2a  name_usage backbone — PARTIAL
  Returns: authorship, canonicalName, rank, taxonomicStatus, publishedIn.
  MISSING from backbone response: basionym, infraspecificEpithet, numOccurrences,
  synonym boolean. 'vernacularName' is present as a single string (truncated).

FINDING  §2b  taxonID in backbone — NOT the IPNI LSID
  usage['taxonID'] = 'gbif:8097702'  ← internal GBIF ID, NOT the IPNI LSID.
  To get the IPNI LSID, must query the IPNI dataset entry via /related (§2d).
  § 2d /related returns taxonID = 'urn:lsid:ipni.org:names:536237-1' — note this
  is a DIFFERENT LSID than the one stored in our DB (77095488-1), suggesting
  multiple IPNI records for the same taxon. Cross-referencing remains necessary.

FINDING  §2c  Synonyms endpoint — EMPTY for this taxon
  data='synonyms' returns 0 results for Haworthia truncata via backbone key.
  GBIF backbone synonyms are unreliable here — POWO remains the better source.

FINDING  §3  Distribution — INCOMPLETE, cannot replace WCVP
  7 records returned from multiple aggregated sources. Problems:
  • Only 2 of 7 records have a TDWG locationId (inconsistent casing: 'tdwg:CPP'
    vs 'TDWG:CPP'). The rest use country ISO codes (e.g. 'ZA', 'BR').
  • native/introduced establishment status is ABSENT on most records
    (one Brazil record has establishmentMeans='MANAGED').
  • The single WCVP-sourced record does provide locality='Cape Provinces' + TDWG
    code, but without native/introduced flag.
  → WCVP SQLite remains necessary for reliable TDWG L3 + establishment data.

FINDING  §4a  taxonID filter on /species endpoint — BROKEN
  REST /species?taxonID=<LSID>&datasetKey=IPNI returns completely unrelated taxa.
  The taxonID parameter is not filtering as expected.

FINDING  §4c  Searching by LSID number — USELESS
  name_lookup(q='77095488-1') returns random unrelated taxa. Not usable.

FINDING  §5a  Vernacular names — BONUS DATA (not currently used)
  Returns common names in multiple languages (eng, afr, por) with sources.
  Could be stored as additional taxon metadata.

FINDING  §5b  References — BONUS DATA (not currently used)
  Returns full citation string with DOI for the original publication.
  Could augment the publishedIn field already stored.

FINDING  §6  Occurrences — WORKS (already in use)
  34 still images found. Good quality metadata. Sources include iNaturalist.

────────────────────────────────────────────────────────────────────────────────
REPLACEMENT ASSESSMENT:
┌─────────────────────────────┬─────────────────────────────────────────────────┐
│ Current source              │ Replace with pygbif?                            │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ IPNI via pykew              │ ✗ NO — name_lookup (IPNI dataset) is the same  │
│ (name search)               │   underlying call already used in the codebase. │
│                             │   pykew wraps the same IPNI-at-GBIF endpoint.   │
│                             │   Could drop pykew if using pygbif directly,    │
│                             │   but the data source is identical.             │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ POWO direct HTTP            │ ✗ NO — synonyms endpoint returned 0 results.   │
│ (status, authors, basionym, │   basionym not available in backbone response.  │
│  synonyms, distribution)    │   POWO API remains the only clean source for   │
│                             │   full taxonomic enrichment per taxon.          │
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ WCVP SQLite                 │ ✗ NO — GBIF distributions lack consistent TDWG │
│ (TDWG L3 + native/intro)    │   L3 codes and establishment status.           │
│                             │   Keep WCVP for authoritative distribution data.│
├─────────────────────────────┼─────────────────────────────────────────────────┤
│ Wikidata scraping           │ ~ MAYBE — name_backbone is broken in 0.6.6.    │
│ (LSID → GBIF ID fallback)   │   name_lookup (general) does return nubKey,    │
│                             │   but taxonID ≠ IPNI LSID in backbone entries. │
│                             │   Current code's name_lookup + manual taxonID  │
│                             │   compare already avoids Wikidata for primary  │
│                             │   lookup; Wikidata is only the last fallback.  │
│                             │   Fix name_backbone usage or use name_lookup   │
│                             │   more aggressively before falling back.        │
└─────────────────────────────┴─────────────────────────────────────────────────┘

BONUS opportunities identified:
  • Vernacular names (§5a) — not currently stored, available for free
  • Publication reference with DOI (§5b) — supplements publishedIn field
"""
print(summary)


import csv
import glob
import sqlite3
import zipfile
from pathlib import Path

import requests

WCVP_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip"
DATA_DIR = Path("wcvp_data")
DB_PATH = "../wcvp.sqlite"


def download_and_extract_wcvp(url: str = WCVP_URL, out_dir: Path = DATA_DIR) -> tuple[str, str]:
    """Download the WCVP zip and extract it. Returns (names_csv, distribution_csv) paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "wcvp.zip"

    print(f"Downloading {url} ...")
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)

    print("Extracting ...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out_dir)

    # The zip may put the CSVs directly in out_dir or inside a subfolder, so search recursively.
    names = glob.glob(str(out_dir / "**" / "wcvp_names.csv"), recursive=True)
    dist = glob.glob(str(out_dir / "**" / "wcvp_distribution.csv"), recursive=True)
    if not names or not dist:
        raise FileNotFoundError(
            f"Could not find wcvp_names.csv / wcvp_distribution.csv under {out_dir}. "
            f"Extracted files: {[p.name for p in out_dir.rglob('*.csv')]}"
        )
    return names[0], dist[0]


def build_wcvp_sqlite(names_csv: str, dist_csv: str, db_path: str = DB_PATH) -> None:
    # Fail fast if someone passes a non-CSV (e.g. the sqlite file itself).
    for p in (names_csv, dist_csv):
        if not p.lower().endswith(".csv"):
            raise ValueError(f"Expected a WCVP .csv file, got: {p}")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS names;
        DROP TABLE IF EXISTS distribution;
        CREATE TABLE names (
            plant_name_id INTEGER PRIMARY KEY,
            ipni_id TEXT,
            accepted_plant_name_id INTEGER
        );
        CREATE TABLE distribution (
            plant_name_id INTEGER, area TEXT, area_code_l3 TEXT,
            introduced INTEGER, extinct INTEGER, location_doubtful INTEGER
        );
    """)
    with open(names_csv, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="|")
        cur.executemany(
            "INSERT INTO names VALUES (?,?,?)",
            ((row["plant_name_id"] or None, row["ipni_id"] or None,
              row["accepted_plant_name_id"] or None) for row in r),
        )
    with open(dist_csv, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="|")
        cur.executemany(
            "INSERT INTO distribution VALUES (?,?,?,?,?,?)",
            ((row["plant_name_id"] or None, row["area"], row["area_code_l3"],
              row["introduced"], row["extinct"], row["location_doubtful"]) for row in r),
        )
    cur.executescript("""
        CREATE INDEX idx_names_ipni ON names(ipni_id);
        CREATE INDEX idx_dist_pnid ON distribution(plant_name_id);
    """)
    con.commit()
    con.close()
    print(f"Built {db_path}")


if __name__ == "__main__":
    names_csv, dist_csv = download_and_extract_wcvp()
    build_wcvp_sqlite(names_csv, dist_csv, db_path=DB_PATH)
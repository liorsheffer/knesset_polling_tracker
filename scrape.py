#!/usr/bin/env python3
"""
Scrapes the poll table from https://themadad.com/allpolls/ and writes it to
data/polls.json in the same shape the dashboard (index.html) expects.

Run manually:   python3 scrape.py
Run on a schedule: see .github/workflows/update-polls.yml
"""
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://themadad.com/allpolls/"
OUT_PATH = Path(__file__).parent / "data" / "polls.json"

# English keys, in the same left-to-right order the party columns appear on
# the site (after "poll number / date / respondents / outlet / pollster").
PARTY_KEYS = [
    "Likud", "UTJ", "Shas", "BlueWhite", "YeshAtid", "HadashTaal",
    "YisraelBeiteinu", "Democrats", "ReligiousZionism", "Raam", "Balad",
    "OtzmaYehudit", "Together", "Yisr", "TrooperHendel", "UnitedArabList",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PollTrackerBot/1.0; "
                  "+https://github.com/) personal, non-commercial poll aggregator"
}


def parse_int(cell: str):
    cell = cell.strip()
    if not cell:
        return None
    cell = cell.replace(",", "")
    try:
        return int(cell)
    except ValueError:
        m = re.search(r"-?\d+", cell)
        return int(m.group()) if m else None


def find_polls_table(soup: BeautifulSoup):
    """The polls table is identified by a header cell containing
    'מספר הסקר' (poll number). Search all tables for that marker so this
    keeps working even if the page's surrounding markup changes."""
    for table in soup.find_all("table"):
        header_text = table.get_text(" ", strip=True)
        if "מספר" in header_text and "תאריך" in header_text:
            return table
    return None


def scrape():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = find_polls_table(soup)
    if table is None:
        print("Could not locate the polls table on the page.", file=sys.stderr)
        sys.exit(1)

    rows_out = []
    body_rows = table.find_all("tr")
    for tr in body_rows:
        cells = tr.find_all(["td"])
        if not cells or len(cells) < 6:
            continue  # header row or malformed row
        texts = [c.get_text(strip=True) for c in cells]

        poll_id = parse_int(texts[0])
        date_raw = texts[1].strip()
        if poll_id is None or not re.match(r"\d{2}/\d{2}/\d{4}", date_raw):
            continue  # not a data row

        n = parse_int(texts[2])
        media = texts[3].strip()
        pollster = texts[4].strip()
        party_cells = texts[5:5 + len(PARTY_KEYS)]

        d, m, y = date_raw.split("/")
        iso_date = f"{y}-{m}-{d}"

        record = {
            "id": poll_id,
            "date": iso_date,
            "date_disp": date_raw,
            "n": n,
            "media": media,
            "pollster": pollster,
        }
        for key, cell in zip(PARTY_KEYS, party_cells):
            record[key] = parse_int(cell)
        # fill any missing trailing party columns with None
        for key in PARTY_KEYS[len(party_cells):]:
            record[key] = None

        rows_out.append(record)

    if not rows_out:
        print("Parsed 0 rows — the site's table structure may have changed.",
              file=sys.stderr)
        sys.exit(1)

    # de-duplicate by poll id, keep newest scrape's version, sort newest first
    by_id = {r["id"]: r for r in rows_out}
    rows_out = sorted(by_id.values(), key=lambda r: (r["date"], r["id"]), reverse=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows_out, f, ensure_ascii=False, indent=None)

    print(f"Wrote {len(rows_out)} polls to {OUT_PATH}")


if __name__ == "__main__":
    scrape()

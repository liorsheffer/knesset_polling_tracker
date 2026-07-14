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


def fetch_rendered_html(url: str) -> str:
    """themadad.com's poll table is built by JavaScript after the initial
    page load — a plain HTTP GET (even one that gets past the site's
    firewall) only ever returns an empty shell page, no table. A real
    headless browser sidesteps both that and any bot-detection based on
    request fingerprints, since it behaves like an actual browser."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="he-IL",
        )
        page.goto(url, wait_until="networkidle", timeout=60000)
        # The table is populated after load; wait for it explicitly, then
        # give any slower AJAX call a little extra time.
        try:
            page.wait_for_selector("table", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html


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
    try:
        html = fetch_rendered_html(URL)
    except Exception as e:  # noqa: BLE001
        print(
            f"Could not load {URL} in the headless browser — got: {e}\n"
            "If this is the first run, make sure the Playwright browser was "
            "installed (the workflow's 'Install Playwright browser' step) — "
            "run `.venv/bin/python3 -m playwright install chromium` manually "
            "on this machine if needed.",
            file=sys.stderr,
        )
        sys.exit(1)

    soup = BeautifulSoup(html, "html.parser")

    table = find_polls_table(soup)
    if table is None:
        print("Could not locate the polls table on the rendered page — "
              "the site's markup or JS loading behavior may have changed.",
              file=sys.stderr)
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

# HaMadad Poll Tracker — Knesset 26

A self-updating dashboard tracking every mandate poll for Israel's 2026 general
election, sourced from [themadad.com/allpolls](https://themadad.com/allpolls/).

- **`index.html`** — the dashboard itself (party trend lines, coalition vs.
  opposition chart, a live seat bar, and a searchable table of every poll).
  It reads `data/polls.json`.
- **`data/polls.json`** — the poll data, currently a snapshot of 334 polls
  (Feb 2025 – Jul 2026) that this project shipped with.
- **`scrape.py`** — re-scrapes themadad.com and rewrites `data/polls.json`.
- **`.github/workflows/update-polls.yml`** — runs `scrape.py` on a schedule
  (every 6 hours by default), commits the result if anything changed, and
  redeploys the site to GitHub Pages. This is what makes the page "auto
  update whenever you refresh it" — the data file itself gets refreshed
  in the background, so you're always looking at the latest scrape.

## Set this up on your own GitHub (5 minutes)

1. Create a new **public** repository (Pages requires public on the free
   tier, or any tier on GitHub Enterprise).
2. Upload everything in this folder to the repo (drag-and-drop on
   github.com works fine, or `git push` from your machine).
3. In the repo, go to **Settings → Pages** and set **Source** to
   **"GitHub Actions."**
4. Go to the **Actions** tab → select **"Update poll data"** → **"Run
   workflow"** to trigger the first run manually (don't want to wait 6
   hours for the first deploy).
5. Your dashboard will be live at
   `https://<your-username>.github.io/<repo-name>/`.

After that, the schedule in `update-polls.yml` keeps it current — no
manual steps needed. Every time you (or anyone) opens the page, it loads
whatever `data/polls.json` currently holds.

## Adjusting the refresh schedule

Edit the `cron` line in `.github/workflows/update-polls.yml`. The default,
`15 */6 * * *`, runs at :15 past every 6th hour UTC. For example, use
`*/30 * * * *` to check every 30 minutes, or `0 6,18 * * *` for twice a
day. themadad.com typically only publishes a handful of new polls per
week, so anything more frequent than hourly is mostly unnecessary.

## If the scrape ever breaks

Poll-tracking sites occasionally change their HTML. `scrape.py` finds the
table by looking for a header cell containing "מספר" (poll number) and
"תאריך" (date), and reads party columns positionally in the order they
appear on the page as of July 2026. If themadad.com reorders or renames
columns, or adds/removes a party, you'll need to update the `PARTY_KEYS`
list at the top of `scrape.py` to match the new column order. The GitHub
Action will show a failed run (with an error, not silently) if the table
can't be found at all, and will simply do nothing if it parses 0 rows.

## Running the scraper locally

```bash
pip install -r requirements.txt
python3 scrape.py
# then just open index.html in a browser
```

## Notes

- All data is public poll results already published by Israeli media
  outlets and aggregated by HaMadad; this project only re-presents it.
- The dashboard's "Coalition" / "Opposition" grouping reflects the
  composition of Israel's current governing coalition as of July 2026
  (Likud, Shas, UTJ, Religious Zionism, Otzma Yehudit) versus all other
  parties — it's a factual grouping used for the governability chart, not
  an editorial judgment.
- Both trend charts plot a trailing 5-calendar-day running mean (same-day
  polls are first averaged together, then averaged with the prior 4 days)
  rather than raw poll-by-poll points, and each series can be split by
  "government pollsters" (Shlomo Filbar / Channel 14 and Zuriel Sharon /
  i24 news) versus all other, "regular" pollsters — toggle either group,
  or overlay a LOESS (locally-weighted regression) trend line, from the
  chip controls above each chart.

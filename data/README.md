# Data Directory

Place the raw 5-minute Chinese Government Bond Futures Excel files in `data/raw/`:

- `10年国债期货_5min_3年.xlsx`
- `30年国债期货_5min_2年.xlsx`

The pipeline first searches `data/raw/` and then falls back to the repository root for local convenience. Raw Excel files are intentionally ignored by Git.

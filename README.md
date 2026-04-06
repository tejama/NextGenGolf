# NextGenGolf Masters Pool Optimizer

Production-style Python application for optimizing **Masters pool** entries with the exact format:

- 13 buckets (choose 1 golfer per bucket)
- Best 8 golfers count toward lineup score
- Missed cuts are heavily penalized
- Output top 10 lineups in EV and diversified modes

## Quickstart (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## 2026 Masters pool CSV is now included

I added `data/masters_players_real.csv` from your screenshots (all 13 buckets, including the large Bonus bucket).

### Run it directly

```bash
masters-optimize run --config config/real_data_example.json --output output
```

This will print the top 10 EV and top 10 diversified lineups using the real golfer names from that CSV.

## If you want a faster smoke run first

```bash
# uses the same real-name CSV but smaller sim settings
masters-optimize run --config config/real_data_smoke.json --output output/real_smoke --mode ev
```

## Why you previously saw `Player 1-2`

`config/default.json` uses synthetic data on purpose, so names are placeholders. For real names always use `config/real_data_example.json`.

## Files added for real-data workflow

- `data/masters_players_real.csv` → built from your screenshots.
- `config/real_data_example.json` → full 10,000 simulation run against that CSV.
- `config/real_data_smoke.json` → quick smoke config for fast local validation.
- `data/masters_players_template.csv` → template if you want to edit/refresh buckets later.

## Other commands

### Backtest

```bash
masters-optimize backtest --config config/default.json
```

### Regression checks (prints progress every 500 by default)

```bash
masters-optimize regression --config config/default.json
```

## Notes

- In `zsh`, quote extras install: `python -m pip install -e '.[dev]'`.
- CLI prints names and IDs together (example: `Scottie Scheffler (B01_P1)`).

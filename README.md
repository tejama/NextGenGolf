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

## IMPORTANT: Why you see `Player 1-2` instead of real golfers

`config/default.json` uses the **synthetic** connector, so you will get placeholder names by design.

If you want real names like **Scottie Scheffler**, **Justin Thomas**, etc., do this exactly:

### 1) Create your real-player CSV from the template

```bash
cp data/masters_players_template.csv data/masters_players_real.csv
```

Then edit `data/masters_players_real.csv` and replace rows with your real pool players.

- Keep the same column headers.
- You must have all 13 buckets represented (`bucket` = 1..13).
- Put real player names in the `name` column.

### 2) Run with the real-data config

```bash
masters-optimize run --config config/real_data_example.json --output output
```

That config points to `data/masters_players_real.csv`, so output lineups will print real names from your file.

## Commands

### Fast smoke run (synthetic placeholders)

```bash
masters-optimize run --config config/smoke.json --output output/smoke --mode all
```

### Full run (synthetic placeholders)

```bash
masters-optimize run --config config/default.json --output output --mode all
```

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

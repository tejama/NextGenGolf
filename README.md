# NextGenGolf Masters Pool Optimizer

Production-style Python application for optimizing **Masters pool** entries with the exact format:

- 13 buckets (choose 1 golfer per bucket)
- Best 8 golfers count toward lineup score
- Missed cuts are heavily penalized
- Output top 10 lineups in EV and diversified modes

## Highlights

- Modular architecture: data, features, model, simulation, optimization, backtest, regression checks
- Config-driven weights and simulation settings
- Monte Carlo tournament simulation (10,000+ runs)
- Portfolio generation with overlap control
- Automated tests for stability/drift/consistency/benchmarking

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Generate lineups from sample data
masters-optimize run --config config/default.json --output output

# Backtest on historical sample snapshots
masters-optimize backtest --config config/default.json

# Regression checks
masters-optimize regression --config config/default.json

# Run tests
pytest -q
```

## Data expectations

The system supports pluggable connectors. Included connectors:
- `CSVConnector` for curated local files
- `SyntheticConnector` for deterministic synthetic generation (for CI/tests)

Expected player dataset fields include:
- identity: `player_id`, `name`, `bucket`
- strokes gained: `sg_off_tee`, `sg_approach`, `sg_arg`, `sg_putting`
- skill/consistency: `driving_distance`, `driving_accuracy`, `gir`, `scrambling`, `par5_scoring`, `bogey_avoidance`, `double_bogey_rate`
- priors: `cut_rate`, `masters_history`, `augusta_correlated`, `majors_perf`, `field_adjusted_finish`
- market odds: `odds_win`, `odds_top5`, `odds_top10`
- rolling form: `recent_finishes` (semicolon-delimited finishes, newest first)

## CLI output

Running `masters-optimize run` emits:
- player model table
- top 10 EV lineups
- top 10 diversified lineups
- JSON artifacts in output directory


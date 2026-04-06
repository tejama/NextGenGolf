from __future__ import annotations

import argparse
import json

from .backtest import run_backtest
from .config import load_config
from .pipeline import run_pipeline
from .regression_checks import run_regression_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Masters pool optimizer")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run optimization pipeline")
    run_cmd.add_argument("--config", required=True)
    run_cmd.add_argument("--output", default="output")
    run_cmd.add_argument("--lock", default="", help="Comma separated player_ids to lock")
    run_cmd.add_argument("--exclude", default="", help="Comma separated player_ids to exclude")
    run_cmd.add_argument("--mode", choices=["all", "ev", "diversified"], default="all")

    bt_cmd = sub.add_parser("backtest", help="Run backtesting")
    bt_cmd.add_argument("--config", required=True)

    reg_cmd = sub.add_parser("regression", help="Run regression integrity checks")
    reg_cmd.add_argument("--config", required=True)

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.command == "run":
        locks = [x.strip() for x in args.lock.split(",") if x.strip()]
        excludes = [x.strip() for x in args.exclude.split(",") if x.strip()]
        results = run_pipeline(cfg, args.output, locked_players=locks, excluded_players=excludes)
        if args.mode in {"all", "ev"}:
            print("Top 10 EV lineups")
            _print_lineups(results["ev"])
        if args.mode in {"all", "diversified"}:
            print("\nTop 10 diversified lineups")
            _print_lineups(results["diversified"])
    elif args.command == "backtest":
        print(json.dumps(run_backtest(cfg), indent=2))
    elif args.command == "regression":
        print(json.dumps(run_regression_checks(cfg), indent=2))


def _print_lineups(lineups) -> None:
    for i, l in enumerate(lineups, start=1):
        print(
            f"{i:02d}. exp={l.expected_score:.2f} floor={l.floor:.2f} "
            f"ceiling={l.ceiling:.2f} vol={l.volatility:.2f} overlap={l.overlap_pct:.1f}%"
        )
        print("    players:", ", ".join(l.players))
        print(
            "    profile:",
            f"best8={l.best8_expected:.2f} cut={l.cut_survival_avg:.2f} win_eq={l.win_equity_sum:.3f}",
        )
        print("    rationale:", l.rationale)


if __name__ == "__main__":
    main()

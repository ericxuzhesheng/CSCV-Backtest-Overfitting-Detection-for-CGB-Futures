from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cscv import run_cscv
from src.data_loader import load_contract_data
from src.report_generator import generate_all_reports
from src.strategy_matrix import StrategyConfig, build_strategy_return_matrix, default_param_grid
from src.utils import DEFAULT_START_DATE, FIGURES_DIR, TABLES_DIR, ensure_output_dirs, selected_contracts
from src.visualization import generate_all_figures


def _save_large_matrix(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, float_format="%.8g", index_label="datetime")


def run_contract(
    contract: str,
    n_splits: int,
    start_date: str,
    performance_metric: str,
    grid_size: int,
    save_strategy_returns: bool,
) -> dict:
    print(f"\n[{contract}] Loading data")
    data = load_contract_data(contract)
    print(f"[{contract}] Raw data: {data.index.min()} -> {data.index.max()}, rows={len(data):,}")

    param_grid = default_param_grid(grid_size)
    param_path = TABLES_DIR / f"parameter_grid_{contract}.csv"
    param_grid.to_csv(param_path, index=False, encoding="utf-8-sig")
    print(f"[{contract}] Parameter grid: {len(param_grid):,} strategies")

    print(f"[{contract}] Building strategy return matrix from {start_date}")
    returns = build_strategy_return_matrix(
        data=data,
        param_grid=param_grid,
        start_date=start_date,
        config=StrategyConfig(),
    )
    print(f"[{contract}] Return matrix: rows={len(returns):,}, columns={returns.shape[1]:,}")

    matrix_path = TABLES_DIR / f"strategy_returns_{contract}.csv"
    if save_strategy_returns:
        print(f"[{contract}] Saving full strategy return matrix to {matrix_path}")
        _save_large_matrix(returns, matrix_path)
    else:
        print(f"[{contract}] Skipping full strategy return matrix CSV by request")

    print(f"[{contract}] Running CSCV: n_splits={n_splits}, metric={performance_metric}")
    cscv_result = run_cscv(
        returns_matrix=returns,
        n_splits=n_splits,
        performance_metric=performance_metric,
    )
    splits = cscv_result["splits"]
    summary = dict(cscv_result["summary"])
    summary.update(
        {
            "contract": contract,
            "sample_start": str(returns.index.min()),
            "sample_end": str(returns.index.max()),
            "rows": int(len(returns)),
            "performance_metric": performance_metric,
        }
    )

    splits_path = TABLES_DIR / f"cscv_splits_{contract}.csv"
    summary_path = TABLES_DIR / f"cscv_summary_{contract}.csv"
    splits.to_csv(splits_path, index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"[{contract}] PBO={summary['PBO']:.4f}, median_oos_rank={summary['median_oos_rank']:.4f}")

    print(f"[{contract}] Generating figures")
    generate_all_figures(splits, contract, FIGURES_DIR)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CSCV overfitting validation for CGB futures.")
    parser.add_argument("--contract", choices=["T", "TL", "ALL"], default="ALL")
    parser.add_argument("--n-splits", type=int, default=8)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--performance-metric", default="sharpe", choices=["sharpe", "mean_return"])
    parser.add_argument("--grid-size", type=int, default=100)
    parser.add_argument(
        "--skip-strategy-returns",
        action="store_true",
        help="Compute the matrix but skip writing the full wide CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_output_dirs()
    summaries = []
    for contract in selected_contracts(args.contract):
        summaries.append(
            run_contract(
                contract=contract,
                n_splits=args.n_splits,
                start_date=args.start_date,
                performance_metric=args.performance_metric,
                grid_size=args.grid_size,
                save_strategy_returns=not args.skip_strategy_returns,
            )
        )

    all_summary = pd.DataFrame(summaries)
    all_summary.to_csv(TABLES_DIR / "cscv_summary_all.csv", index=False, encoding="utf-8-sig")
    generate_all_reports(start_date=args.start_date)
    print("\nDone. Outputs are under results/.")


if __name__ == "__main__":
    main()

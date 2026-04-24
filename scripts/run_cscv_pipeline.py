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
from src.dynamic_selection_audit import run_dynamic_selection_audit
from src.report_generator import generate_all_reports
from src.strategy_matrix import StrategyConfig, build_strategy_return_matrix, default_param_grid
from src.utils import DEFAULT_START_DATE, FIGURES_DIR, PERIODS_PER_YEAR, TABLES_DIR, ensure_output_dirs, selected_contracts
from src.visualization import generate_all_figures, generate_dynamic_audit_figures


def _save_large_matrix(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, float_format="%.8g", index_label="datetime")


def _load_large_matrix(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col="datetime", parse_dates=["datetime"])


def _bars_from_days(days: int) -> int:
    return int(days) * 54


def _prepare_returns_matrix(
    contract: str,
    start_date: str,
    grid_size: int,
    save_strategy_returns: bool,
    force_rebuild: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix_path = TABLES_DIR / f"strategy_returns_{contract}.csv"
    param_path = TABLES_DIR / f"parameter_grid_{contract}.csv"

    if matrix_path.exists() and param_path.exists() and not force_rebuild:
        print(f"[{contract}] Loading existing strategy return matrix from {matrix_path}")
        returns = _load_large_matrix(matrix_path)
        param_grid = pd.read_csv(param_path)
        return returns, param_grid

    print(f"\n[{contract}] Loading data")
    data = load_contract_data(contract)
    print(f"[{contract}] Raw data: {data.index.min()} -> {data.index.max()}, rows={len(data):,}")

    param_grid = default_param_grid(grid_size)
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

    if save_strategy_returns:
        print(f"[{contract}] Saving strategy return matrix to {matrix_path}")
        _save_large_matrix(returns, matrix_path)
    else:
        print(f"[{contract}] Skipping strategy return matrix CSV by request")

    return returns, param_grid


def _run_cscv_mode(
    contract: str,
    returns: pd.DataFrame,
    n_splits: int,
    performance_metric: str,
) -> dict:
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
    splits.to_csv(TABLES_DIR / f"cscv_splits_{contract}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(TABLES_DIR / f"cscv_summary_{contract}.csv", index=False, encoding="utf-8-sig")
    generate_all_figures(splits, contract, FIGURES_DIR)
    print(f"[{contract}] PBO={summary['PBO']:.4f}, median_oos_rank={summary['median_oos_rank']:.4f}")
    return summary


def _run_dynamic_mode(
    contract: str,
    returns: pd.DataFrame,
    train_window_days: int,
    test_window_days: int,
    rebalance_days: int,
    selection_metric: str,
) -> dict:
    train_window_bars = _bars_from_days(train_window_days)
    test_window_bars = _bars_from_days(test_window_days)
    rebalance_every_bars = _bars_from_days(rebalance_days)

    print(
        f"[{contract}] Running dynamic audit: train={train_window_bars}, "
        f"test={test_window_bars}, rebalance={rebalance_every_bars}, metric={selection_metric}"
    )
    audit_result = run_dynamic_selection_audit(
        returns_matrix=returns,
        train_window_bars=train_window_bars,
        test_window_bars=test_window_bars,
        rebalance_every_bars=rebalance_every_bars,
        selection_metric=selection_metric,
        periods_per_year=PERIODS_PER_YEAR,
    )
    splits = audit_result["splits"]
    summary = dict(audit_result["summary"])
    summary.update(
        {
            "contract": contract,
            "sample_start": str(returns.index.min()),
            "sample_end": str(returns.index.max()),
            "rows": int(len(returns)),
            "train_window_days": int(train_window_days),
            "test_window_days": int(test_window_days),
            "rebalance_days": int(rebalance_days),
        }
    )
    stability = audit_result["parameter_stability"].copy()
    stability.insert(0, "contract", contract)

    splits.to_csv(TABLES_DIR / f"dynamic_audit_splits_{contract}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(
        TABLES_DIR / f"dynamic_audit_summary_{contract}.csv",
        index=False,
        encoding="utf-8-sig",
    )
    stability.to_csv(TABLES_DIR / f"parameter_stability_{contract}.csv", index=False, encoding="utf-8-sig")
    generate_dynamic_audit_figures(splits, contract, FIGURES_DIR)
    print(
        f"[{contract}] Dynamic failure rate={summary['dynamic_selection_failure_rate']:.4f}, "
        f"score_oos_corr={summary['score_oos_corr']:.4f}"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CSCV and dynamic parameter selection audit for CGB futures.")
    parser.add_argument("--mode", choices=["strategy_matrix", "cscv", "dynamic_audit", "full"], default="full")
    parser.add_argument("--contract", choices=["T", "TL", "ALL"], default="ALL")
    parser.add_argument("--n-splits", type=int, default=8)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--performance-metric", default="sharpe", choices=["sharpe", "mean_return"])
    parser.add_argument(
        "--selection-metric",
        default="sharpe",
        choices=["sharpe", "annualized_return", "calmar", "cumulative_return", "win_rate"],
    )
    parser.add_argument("--train-window-days", type=int, default=60)
    parser.add_argument("--test-window-days", type=int, default=10)
    parser.add_argument("--rebalance-days", type=int, default=1)
    parser.add_argument("--grid-size", type=int, default=100)
    parser.add_argument("--skip-strategy-returns", action="store_true")
    parser.add_argument("--force-rebuild", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_output_dirs()

    cscv_summaries: list[dict] = []
    dynamic_summaries: list[dict] = []

    for contract in selected_contracts(args.contract):
        returns, _ = _prepare_returns_matrix(
            contract=contract,
            start_date=args.start_date,
            grid_size=args.grid_size,
            save_strategy_returns=not args.skip_strategy_returns,
            force_rebuild=args.force_rebuild or args.mode in {"strategy_matrix", "full"},
        )

        if args.mode in {"cscv", "full"}:
            cscv_summaries.append(
                _run_cscv_mode(
                    contract=contract,
                    returns=returns,
                    n_splits=args.n_splits,
                    performance_metric=args.performance_metric,
                )
            )

        if args.mode in {"dynamic_audit", "full"}:
            dynamic_summaries.append(
                _run_dynamic_mode(
                    contract=contract,
                    returns=returns,
                    train_window_days=args.train_window_days,
                    test_window_days=args.test_window_days,
                    rebalance_days=args.rebalance_days,
                    selection_metric=args.selection_metric,
                )
            )

    if cscv_summaries:
        pd.DataFrame(cscv_summaries).to_csv(TABLES_DIR / "cscv_summary_all.csv", index=False, encoding="utf-8-sig")
    if dynamic_summaries:
        pd.DataFrame(dynamic_summaries).to_csv(
            TABLES_DIR / "dynamic_audit_summary_all.csv",
            index=False,
            encoding="utf-8-sig",
        )

    if args.mode in {"cscv", "dynamic_audit", "full"}:
        generate_all_reports(start_date=args.start_date)

    print("\nDone. Outputs are under results/.")


if __name__ == "__main__":
    main()

from __future__ import annotations

from itertools import combinations
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .metrics import metric_from_stats
from .utils import PERIODS_PER_YEAR, parse_strategy_id


def _block_stats(values: np.ndarray, n_splits: int) -> tuple[List[np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    indices = np.array_split(np.arange(values.shape[0]), n_splits)
    counts = np.array([len(idx) for idx in indices], dtype=int)
    sums = np.vstack([values[idx].sum(axis=0, dtype=np.float64) for idx in indices])
    sumsq = np.vstack([(values[idx].astype(np.float64) ** 2).sum(axis=0) for idx in indices])
    return indices, counts, sums, sumsq


def _aggregate_metric(
    block_ids: tuple[int, ...],
    counts: np.ndarray,
    sums: np.ndarray,
    sumsq: np.ndarray,
    metric: str,
) -> np.ndarray:
    total_count = int(counts[list(block_ids)].sum())
    total_sum = sums[list(block_ids)].sum(axis=0)
    total_sumsq = sumsq[list(block_ids)].sum(axis=0)
    return metric_from_stats(total_sum, total_sumsq, total_count, metric)


def run_cscv(
    returns_matrix: pd.DataFrame,
    n_splits: int = 8,
    performance_metric: str = "sharpe",
) -> Dict[str, object]:
    if n_splits <= 1 or n_splits % 2 != 0:
        raise ValueError("n_splits must be an even integer greater than 1.")
    if len(returns_matrix) < n_splits:
        raise ValueError("returns_matrix has fewer rows than n_splits.")

    clean = returns_matrix.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    values = clean.to_numpy(dtype=np.float32, copy=False)
    strategies = clean.columns.to_numpy()
    n_strategies = len(strategies)

    block_indices, counts, sums, sumsq = _block_stats(values, n_splits)
    half = n_splits // 2
    all_blocks = tuple(range(n_splits))
    split_rows = []
    oos_perf_accum = np.zeros(n_strategies, dtype=float)
    oos_perf_count = 0

    for split_id, is_blocks in enumerate(combinations(all_blocks, half), start=1):
        oos_blocks = tuple(block for block in all_blocks if block not in is_blocks)
        is_perf = _aggregate_metric(is_blocks, counts, sums, sumsq, performance_metric)
        oos_perf = _aggregate_metric(oos_blocks, counts, sums, sumsq, performance_metric)

        best_idx = int(np.nanargmax(is_perf))
        selected_oos_perf = float(oos_perf[best_idx])
        oos_ranks = rankdata(np.nan_to_num(oos_perf, nan=-np.inf), method="average")
        if n_strategies > 1:
            selected_rank_pct = float((oos_ranks[best_idx] - 1.0) / (n_strategies - 1.0))
        else:
            selected_rank_pct = 1.0
        clipped = min(max(selected_rank_pct, 1e-6), 1.0 - 1e-6)
        rank_logit = float(np.log(clipped / (1.0 - clipped)))
        best_strategy = str(strategies[best_idx])
        params = parse_strategy_id(best_strategy)

        split_rows.append(
            {
                "split_id": split_id,
                "is_blocks": "|".join(map(str, is_blocks)),
                "oos_blocks": "|".join(map(str, oos_blocks)),
                "best_strategy": best_strategy,
                "N_fast": params["N_fast"],
                "N_slow": params["N_slow"],
                "is_performance": float(is_perf[best_idx]),
                "oos_performance": selected_oos_perf,
                "oos_rank": float(oos_ranks[best_idx]),
                "oos_rank_pct": selected_rank_pct,
                "rank_logit": rank_logit,
                "overfit_event": bool(selected_rank_pct < 0.5),
            }
        )
        oos_perf_accum += np.nan_to_num(oos_perf, nan=-np.inf)
        oos_perf_count += 1

    splits = pd.DataFrame(split_rows)
    full_perf = metric_from_stats(
        values.sum(axis=0, dtype=np.float64),
        (values.astype(np.float64) ** 2).sum(axis=0),
        len(clean),
        performance_metric,
    )
    best_overall_idx = int(np.nanargmax(full_perf))
    avg_oos_perf = oos_perf_accum / max(oos_perf_count, 1)
    best_oos_idx = int(np.nanargmax(avg_oos_perf))

    summary = {
        "n_strategies": int(n_strategies),
        "n_splits": int(n_splits),
        "n_combinations": int(len(splits)),
        "PBO": float(splits["overfit_event"].mean()),
        "median_oos_rank": float(splits["oos_rank_pct"].median()),
        "mean_is_performance": float(splits["is_performance"].mean()),
        "mean_oos_performance": float(splits["oos_performance"].mean()),
        "degradation_ratio": float(
            splits["oos_performance"].mean() / splits["is_performance"].mean()
            if splits["is_performance"].mean() != 0
            else np.nan
        ),
        "best_overall_strategy": str(strategies[best_overall_idx]),
        "best_oos_strategy": str(strategies[best_oos_idx]),
        "periods_per_year": PERIODS_PER_YEAR,
    }
    return {
        "splits": splits,
        "summary": summary,
        "block_ranges": [
            {
                "block": i,
                "start": str(clean.index[idx[0]]),
                "end": str(clean.index[idx[-1]]),
                "rows": int(len(idx)),
            }
            for i, idx in enumerate(block_indices)
        ],
    }

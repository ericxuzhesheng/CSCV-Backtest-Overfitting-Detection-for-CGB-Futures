from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, rankdata, spearmanr

from .metrics import cumulative_return, evaluate_metric, sharpe_ratio
from .utils import PERIODS_PER_YEAR


SUPPORTED_SELECTION_METRICS = {
    "sharpe",
    "annualized_return",
    "calmar",
    "cumulative_return",
    "win_rate",
}


@dataclass(frozen=True)
class WindowSlice:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


def _validate_inputs(
    returns_matrix: pd.DataFrame,
    train_window_bars: int,
    test_window_bars: int,
    rebalance_every_bars: int,
    selection_metric: str,
) -> None:
    if returns_matrix.empty:
        raise ValueError("returns_matrix is empty.")
    if train_window_bars <= 1 or test_window_bars <= 0 or rebalance_every_bars <= 0:
        raise ValueError("train_window_bars, test_window_bars, and rebalance_every_bars must be positive.")
    if train_window_bars + test_window_bars > len(returns_matrix):
        raise ValueError("Not enough rows for one train/test window.")
    if selection_metric not in SUPPORTED_SELECTION_METRICS:
        raise ValueError(
            f"Unsupported selection_metric: {selection_metric}. "
            f"Use one of {sorted(SUPPORTED_SELECTION_METRICS)}."
        )


def _iter_windows(
    n_rows: int,
    train_window_bars: int,
    test_window_bars: int,
    rebalance_every_bars: int,
) -> Iterable[WindowSlice]:
    train_start = 0
    while True:
        train_end = train_start + train_window_bars
        test_start = train_end
        test_end = test_start + test_window_bars
        if test_end > n_rows:
            break
        yield WindowSlice(
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )
        train_start += rebalance_every_bars


def _prefix_sum(values: np.ndarray) -> np.ndarray:
    out = np.zeros((values.shape[0] + 1, values.shape[1]), dtype=np.float64)
    out[1:] = np.cumsum(values, axis=0, dtype=np.float64)
    return out


def _window_from_prefix(prefix: np.ndarray, start: int, end: int) -> np.ndarray:
    return prefix[end] - prefix[start]


def _safe_percentile(rank_value: float, n_items: int) -> float:
    if n_items <= 1:
        return 1.0
    return float((rank_value - 1.0) / (n_items - 1.0))


def _corr_or_nan(x: np.ndarray, y: np.ndarray, method: str) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return np.nan
    x_valid = x[mask]
    y_valid = y[mask]
    if np.allclose(x_valid, x_valid[0]) or np.allclose(y_valid, y_valid[0]):
        return np.nan
    if method == "pearson":
        return float(pearsonr(x_valid, y_valid).statistic)
    if method == "spearman":
        return float(spearmanr(x_valid, y_valid).statistic)
    raise ValueError(f"Unsupported correlation method: {method}")


def _format_top_frequency(strategy_counts: pd.Series, top_n: int = 5) -> str:
    if strategy_counts.empty:
        return ""
    total = float(strategy_counts.sum())
    parts = []
    for strategy, count in strategy_counts.head(top_n).items():
        ratio = count / total if total else np.nan
        parts.append(f"{strategy}:{int(count)} ({ratio:.2%})")
    return "; ".join(parts)


def _parameter_stability(selected: pd.Series, contract: str | None = None) -> tuple[dict, pd.DataFrame]:
    if selected.empty:
        summary = {
            "parameter_switch_count": 0,
            "most_frequent_strategy": "",
            "most_frequent_strategy_ratio": np.nan,
            "top_5_strategy_frequency": "",
            "parameter_entropy": np.nan,
            "average_holding_windows": np.nan,
        }
        row = dict(summary)
        if contract is not None:
            row["contract"] = contract
        return summary, pd.DataFrame([row])

    counts = selected.value_counts()
    most_frequent_strategy = str(counts.index[0])
    most_frequent_ratio = float(counts.iloc[0] / len(selected))
    probs = (counts / counts.sum()).to_numpy(dtype=float)
    entropy = float(-(probs * np.log(probs)).sum())

    switches = int((selected != selected.shift(1)).iloc[1:].sum())
    run_lengths = []
    current = 1
    values = selected.tolist()
    for idx in range(1, len(values)):
        if values[idx] == values[idx - 1]:
            current += 1
        else:
            run_lengths.append(current)
            current = 1
    run_lengths.append(current)
    avg_hold = float(np.mean(run_lengths)) if run_lengths else np.nan

    summary = {
        "parameter_switch_count": switches,
        "most_frequent_strategy": most_frequent_strategy,
        "most_frequent_strategy_ratio": most_frequent_ratio,
        "top_5_strategy_frequency": _format_top_frequency(counts, top_n=5),
        "parameter_entropy": entropy,
        "average_holding_windows": avg_hold,
    }
    row = dict(summary)
    if contract is not None:
        row["contract"] = contract
    return summary, pd.DataFrame([row])


def _metric_scores_vectorized(
    values: np.ndarray,
    metric: str,
    periods_per_year: int,
) -> np.ndarray:
    count = values.shape[0]
    if count == 0:
        return np.full(values.shape[1], np.nan, dtype=float)

    if metric == "sharpe":
        mean = np.mean(values, axis=0, dtype=np.float64)
        vol = np.std(values, axis=0, ddof=1) if count > 1 else np.full(values.shape[1], np.nan)
        out = np.divide(mean, vol, out=np.full(values.shape[1], np.nan), where=np.isfinite(vol) & (vol > 0))
        return out * np.sqrt(periods_per_year)

    if metric == "annualized_return":
        gross = np.prod(1.0 + values, axis=0, dtype=np.float64)
        out = np.full(values.shape[1], np.nan, dtype=float)
        valid = gross > 0
        out[valid] = gross[valid] ** (periods_per_year / count) - 1.0
        return out

    if metric == "cumulative_return":
        return np.prod(1.0 + values, axis=0, dtype=np.float64) - 1.0

    if metric == "win_rate":
        return np.mean(values > 0, axis=0, dtype=np.float64)

    if metric == "calmar":
        nav = np.cumprod(1.0 + values, axis=0, dtype=np.float64)
        peaks = np.maximum.accumulate(nav, axis=0)
        drawdowns = nav / peaks - 1.0
        max_drawdowns = np.min(drawdowns, axis=0)
        gross = nav[-1]
        ann = np.full(values.shape[1], np.nan, dtype=float)
        valid = gross > 0
        ann[valid] = gross[valid] ** (periods_per_year / count) - 1.0
        return np.divide(
            ann,
            np.abs(max_drawdowns),
            out=np.full(values.shape[1], np.nan, dtype=float),
            where=np.isfinite(max_drawdowns) & (max_drawdowns < 0),
        )

    raise ValueError(f"Unsupported metric: {metric}")


def _build_metric_engine(values: np.ndarray, metric: str, periods_per_year: int):
    if metric == "sharpe":
        prefix_sum = _prefix_sum(values)
        prefix_sumsq = _prefix_sum(values.astype(np.float64) ** 2)

        def scorer(start: int, end: int) -> np.ndarray:
            count = end - start
            if count <= 1:
                return np.full(values.shape[1], np.nan, dtype=float)
            total = _window_from_prefix(prefix_sum, start, end)
            total_sq = _window_from_prefix(prefix_sumsq, start, end)
            mean = total / count
            var = (total_sq - count * mean * mean) / (count - 1)
            var = np.maximum(var, 0.0)
            vol = np.sqrt(var)
            return np.divide(
                mean,
                vol,
                out=np.full(values.shape[1], np.nan, dtype=float),
                where=vol > 0,
            ) * np.sqrt(periods_per_year)

        return scorer

    if metric == "win_rate":
        wins = _prefix_sum((values > 0).astype(np.float64))

        def scorer(start: int, end: int) -> np.ndarray:
            count = end - start
            if count <= 0:
                return np.full(values.shape[1], np.nan, dtype=float)
            return _window_from_prefix(wins, start, end) / count

        return scorer

    if metric in {"cumulative_return", "annualized_return"}:
        invalid = (values <= -1.0) | ~np.isfinite(values)
        bad_counts = _prefix_sum(invalid.astype(np.float64))
        log_growth = np.where(~invalid, np.log1p(values), 0.0)
        prefix_log = _prefix_sum(log_growth)

        def scorer(start: int, end: int) -> np.ndarray:
            count = end - start
            if count <= 0:
                return np.full(values.shape[1], np.nan, dtype=float)
            bad = _window_from_prefix(bad_counts, start, end) > 0
            gross = np.exp(_window_from_prefix(prefix_log, start, end))
            out = gross - 1.0
            out = out.astype(float, copy=False)
            out[bad] = np.nan
            if metric == "annualized_return":
                annualized = np.full(values.shape[1], np.nan, dtype=float)
                valid = (~bad) & (gross > 0)
                annualized[valid] = gross[valid] ** (periods_per_year / count) - 1.0
                return annualized
            return out

        return scorer

    def scorer(start: int, end: int) -> np.ndarray:
        return _metric_scores_vectorized(values[start:end], metric, periods_per_year)

    return scorer


def run_dynamic_selection_audit(
    returns_matrix: pd.DataFrame,
    train_window_bars: int,
    test_window_bars: int,
    rebalance_every_bars: int,
    selection_metric: str = "sharpe",
    periods_per_year: int = PERIODS_PER_YEAR,
) -> Dict[str, object]:
    selection_metric = selection_metric.lower()
    _validate_inputs(
        returns_matrix=returns_matrix,
        train_window_bars=train_window_bars,
        test_window_bars=test_window_bars,
        rebalance_every_bars=rebalance_every_bars,
        selection_metric=selection_metric,
    )

    clean = returns_matrix.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    values = clean.to_numpy(dtype=np.float64, copy=False)
    strategies = clean.columns.to_numpy()
    scorer = _build_metric_engine(values, selection_metric, periods_per_year)

    split_rows = []
    score_pairs = []
    oos_pairs = []
    oos_rank_pairs = []

    for window_id, window in enumerate(
        _iter_windows(
            n_rows=len(clean),
            train_window_bars=train_window_bars,
            test_window_bars=test_window_bars,
            rebalance_every_bars=rebalance_every_bars,
        ),
        start=1,
    ):
        train_scores = scorer(window.train_start, window.train_end)
        oos_scores = scorer(window.test_start, window.test_end)
        oos_rank_values = rankdata(np.nan_to_num(oos_scores, nan=-np.inf), method="average")
        oos_percentiles = np.array(
            [_safe_percentile(rank, len(strategies)) for rank in oos_rank_values],
            dtype=float,
        )

        score_pairs.append(train_scores)
        oos_pairs.append(oos_scores)
        oos_rank_pairs.append(oos_percentiles)

        best_train_idx = int(np.nanargmax(np.nan_to_num(train_scores, nan=-np.inf)))
        best_oos_idx = int(np.nanargmax(np.nan_to_num(oos_scores, nan=-np.inf)))
        selected_strategy = str(strategies[best_train_idx])
        selected_oos_slice = clean.iloc[window.test_start : window.test_end, best_train_idx].to_numpy(dtype=float)

        split_rows.append(
            {
                "window_id": window_id,
                "train_start": str(clean.index[window.train_start]),
                "train_end": str(clean.index[window.train_end - 1]),
                "test_start": str(clean.index[window.test_start]),
                "test_end": str(clean.index[window.test_end - 1]),
                "selected_strategy": selected_strategy,
                "selection_metric": selection_metric,
                "selection_score": float(train_scores[best_train_idx]),
                "selected_oos_score": float(oos_scores[best_train_idx]),
                "selected_oos_return": float(cumulative_return(selected_oos_slice)),
                "selected_oos_sharpe": float(sharpe_ratio(selected_oos_slice, periods_per_year)),
                "selected_oos_rank": float(oos_rank_values[best_train_idx]),
                "selected_oos_percentile": float(oos_percentiles[best_train_idx]),
                "failure_flag": int(oos_percentiles[best_train_idx] < 0.5),
                "best_oos_strategy": str(strategies[best_oos_idx]),
                "best_oos_score": float(oos_scores[best_oos_idx]),
                "n_candidates": int(len(strategies)),
            }
        )

    splits = pd.DataFrame(split_rows)
    if splits.empty:
        raise ValueError("No valid walk-forward windows were generated.")

    all_scores = np.concatenate(score_pairs) if score_pairs else np.array([], dtype=float)
    all_oos = np.concatenate(oos_pairs) if oos_pairs else np.array([], dtype=float)
    all_oos_ranks = np.concatenate(oos_rank_pairs) if oos_rank_pairs else np.array([], dtype=float)

    stability_summary, stability_table = _parameter_stability(splits["selected_strategy"])

    summary = {
        "n_windows": int(len(splits)),
        "n_strategies": int(clean.shape[1]),
        "train_window_bars": int(train_window_bars),
        "test_window_bars": int(test_window_bars),
        "rebalance_every_bars": int(rebalance_every_bars),
        "selection_metric": selection_metric,
        "mean_selected_oos_return": float(splits["selected_oos_return"].mean()),
        "mean_selected_oos_sharpe": float(splits["selected_oos_sharpe"].mean()),
        "median_selected_oos_rank": float(splits["selected_oos_rank"].median()),
        "mean_selected_oos_percentile": float(splits["selected_oos_percentile"].mean()),
        "median_selected_oos_percentile": float(splits["selected_oos_percentile"].median()),
        "dynamic_selection_failure_rate": float(splits["failure_flag"].mean()),
        "score_oos_corr": _corr_or_nan(all_scores, all_oos, method="pearson"),
        "score_oos_rank_corr": _corr_or_nan(all_scores, all_oos_ranks, method="spearman"),
        **stability_summary,
        "periods_per_year": int(periods_per_year),
    }

    return {
        "splits": splits,
        "summary": summary,
        "parameter_stability": stability_table,
    }

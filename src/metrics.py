from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import PERIODS_PER_YEAR


def cumulative_return(returns: pd.Series | np.ndarray) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.nan
    return float(np.prod(1.0 + arr) - 1.0)


def annualized_return(returns: pd.Series | np.ndarray, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.nan
    total = np.prod(1.0 + arr)
    if total <= 0:
        return np.nan
    return float(total ** (periods_per_year / arr.size) - 1.0)


def annualized_volatility(returns: pd.Series | np.ndarray, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return np.nan
    return float(np.std(arr, ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(returns: pd.Series | np.ndarray, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return np.nan
    vol = np.std(arr, ddof=1)
    if vol <= 0 or not np.isfinite(vol):
        return np.nan
    return float(np.mean(arr) / vol * np.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series | np.ndarray) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    if arr.size == 0:
        return np.nan
    nav = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(nav)
    dd = nav / peak - 1.0
    return float(np.min(dd))


def calmar_ratio(returns: pd.Series | np.ndarray, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    ann = annualized_return(returns, periods_per_year)
    mdd = max_drawdown(returns)
    if not np.isfinite(ann) or not np.isfinite(mdd) or mdd >= 0:
        return np.nan
    return float(ann / abs(mdd))


def win_rate(returns: pd.Series | np.ndarray) -> float:
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.nan
    return float(np.mean(arr > 0))


def performance_summary(returns: pd.Series | np.ndarray, periods_per_year: int = PERIODS_PER_YEAR) -> dict:
    return {
        "cumulative_return": cumulative_return(returns),
        "annualized_return": annualized_return(returns, periods_per_year),
        "annualized_volatility": annualized_volatility(returns, periods_per_year),
        "sharpe": sharpe_ratio(returns, periods_per_year),
        "max_drawdown": max_drawdown(returns),
        "calmar": calmar_ratio(returns, periods_per_year),
        "win_rate": win_rate(returns),
    }


def evaluate_metric(
    returns: pd.Series | np.ndarray,
    metric: str,
    periods_per_year: int = PERIODS_PER_YEAR,
) -> float:
    metric_key = metric.lower()
    if metric_key == "sharpe":
        return sharpe_ratio(returns, periods_per_year)
    if metric_key == "annualized_return":
        return annualized_return(returns, periods_per_year)
    if metric_key == "calmar":
        return calmar_ratio(returns, periods_per_year)
    if metric_key == "cumulative_return":
        return cumulative_return(returns)
    if metric_key == "win_rate":
        return win_rate(returns)
    raise ValueError(f"Unsupported metric: {metric}")


def metric_from_stats(sum_returns: np.ndarray, sum_squares: np.ndarray, count: int, metric: str) -> np.ndarray:
    if count <= 1:
        return np.full_like(sum_returns, np.nan, dtype=float)
    mean = sum_returns / count
    var = (sum_squares - count * mean * mean) / (count - 1)
    var = np.maximum(var, 0.0)
    vol = np.sqrt(var)
    if metric == "sharpe":
        out = np.divide(
            mean,
            vol,
            out=np.full_like(mean, np.nan, dtype=float),
            where=vol > 0,
        ) * np.sqrt(PERIODS_PER_YEAR)
    elif metric == "mean_return":
        out = mean * PERIODS_PER_YEAR
    else:
        raise ValueError(f"Unsupported CSCV performance metric: {metric}")
    return out

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from numba import njit

from .utils import DEFAULT_START_DATE, PERIODS_PER_YEAR, make_strategy_id


@dataclass(frozen=True)
class StrategyConfig:
    allow_short: bool = True
    max_consecutive_losses: int = 3
    loss_cooldown_bars: int = 108
    periods_per_year: int = PERIODS_PER_YEAR


def default_param_grid(grid_size: int = 100) -> pd.DataFrame:
    n_fast = np.unique(np.linspace(10, 540, grid_size).astype(int))
    n_slow = np.unique(np.linspace(54, 2700, grid_size).astype(int))
    rows = []
    for fast in n_fast:
        for slow in n_slow:
            if int(fast) < int(slow):
                rows.append(
                    {
                        "strategy_id": make_strategy_id(int(fast), int(slow)),
                        "N_fast": int(fast),
                        "N_slow": int(slow),
                    }
                )
    return pd.DataFrame(rows)


def calc_bullbear_indicator(data: pd.DataFrame, period: int) -> pd.Series:
    ret_std = data["close"].pct_change().rolling(period).std(ddof=1)
    if "open_interest" in data.columns:
        oi = data["open_interest"].replace(0, np.nan).ffill()
        turnover = data["volume"] / oi
    else:
        turnover = data["volume"]
    mean_turnover = turnover.rolling(period).mean()
    return mean_turnover / ret_std.replace(0, np.nan)


@njit(cache=True)
def _build_position_numba(
    fast_values: np.ndarray,
    slow_values: np.ndarray,
    close_values: np.ndarray,
    allow_short: bool,
    max_consecutive_losses: int,
    loss_cooldown_bars: int,
) -> np.ndarray:
    n = len(fast_values)
    pos = np.zeros(n, dtype=np.float64)
    prev_pos = 0.0
    consecutive_losses = 0
    loss_cooldown_counter = 0
    entry_price = 0.0

    for i in range(n):
        cur_fast = fast_values[i]
        cur_slow = slow_values[i]
        cur_close = close_values[i]

        if loss_cooldown_counter > 0:
            loss_cooldown_counter -= 1
            pos[i] = 0.0
            prev_pos = 0.0
            continue

        desired_pos = prev_pos
        if not np.isnan(cur_fast) and not np.isnan(cur_slow):
            if cur_fast > cur_slow:
                desired_pos = 1.0
            elif cur_fast < cur_slow:
                desired_pos = -1.0 if allow_short else 0.0

        if prev_pos != 0.0 and desired_pos != prev_pos:
            pnl = 0.0
            if prev_pos == 1.0:
                pnl = cur_close - entry_price
            elif prev_pos == -1.0:
                pnl = entry_price - cur_close

            if pnl < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0

            if consecutive_losses >= max_consecutive_losses:
                loss_cooldown_counter = loss_cooldown_bars
                consecutive_losses = 0
                desired_pos = 0.0

        if desired_pos != prev_pos:
            if desired_pos != 0.0:
                entry_price = cur_close
            else:
                entry_price = 0.0

        pos[i] = desired_pos
        prev_pos = desired_pos

    return pos


def build_strategy_return_matrix(
    data: pd.DataFrame,
    param_grid: pd.DataFrame,
    start_date: str = DEFAULT_START_DATE,
    config: Optional[StrategyConfig] = None,
) -> pd.DataFrame:
    """Build per-bar strategy returns for each parameter combination.

    The signal and position are determined using information through bar t.
    Returns are earned with ``position.shift(1)`` on bar t+1.
    """

    cfg = config or StrategyConfig()
    data = data.sort_index().copy()
    start_ts = pd.Timestamp(start_date)
    if data.index.max() < start_ts:
        raise ValueError(f"No data available on or after {start_date}")

    unique_periods = sorted(
        set(param_grid["N_fast"].astype(int).tolist() + param_grid["N_slow"].astype(int).tolist())
    )
    indicators = {
        period: calc_bullbear_indicator(data, int(period)).to_numpy(dtype=np.float64)
        for period in unique_periods
    }

    close = data["close"].to_numpy(dtype=np.float64)
    ret_bh = np.zeros(len(data), dtype=np.float64)
    ret_bh[1:] = np.diff(close) / close[:-1]
    start_mask = np.asarray(data.index >= start_ts)
    start_idx = int(np.argmax(start_mask))
    out_index = data.index[start_idx:]

    # Warm up numba outside the main loop.
    _build_position_numba(
        np.array([1.0, 2.0], dtype=np.float64),
        np.array([0.5, 1.5], dtype=np.float64),
        np.array([100.0, 101.0], dtype=np.float64),
        cfg.allow_short,
        cfg.max_consecutive_losses,
        cfg.loss_cooldown_bars,
    )

    strategy_ids = param_grid["strategy_id"].tolist()
    matrix = np.empty((len(out_index), len(strategy_ids)), dtype=np.float32)
    for col_idx, row in enumerate(param_grid.itertuples(index=False)):
        pos = _build_position_numba(
            indicators[int(row.N_fast)],
            indicators[int(row.N_slow)],
            close,
            cfg.allow_short,
            cfg.max_consecutive_losses,
            cfg.loss_cooldown_bars,
        )
        shifted_pos = np.empty_like(pos)
        shifted_pos[0] = 0.0
        shifted_pos[1:] = pos[:-1]
        matrix[:, col_idx] = (shifted_pos[start_idx:] * ret_bh[start_idx:]).astype(np.float32)

    return pd.DataFrame(matrix, index=out_index, columns=strategy_ids)

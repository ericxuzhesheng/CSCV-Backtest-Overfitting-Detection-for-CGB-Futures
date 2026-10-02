"""Build a declared candidate grid from read-only QRS/VPIN checkouts."""
import argparse
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path, package=False):
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def revision(path):
    return subprocess.check_output(["git", "-c", f"safe.directory={path.as_posix()}", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qrs-repo", type=Path, required=True)
    parser.add_argument("--vpin-repo", type=Path, required=True)
    parser.add_argument("--cost-bps", type=float, default=1.0)
    args = parser.parse_args()
    if not np.isfinite(args.cost_bps) or args.cost_bps < 0:
        raise ValueError("cost-bps must be finite and non-negative")
    qrs_root, vpin_root = args.qrs_repo.resolve(), args.vpin_repo.resolve()
    load_module("qrs_source", qrs_root / "src" / "__init__.py", package=True)
    calc = importlib.import_module("qrs_source.qrs_calculator")
    signal = importlib.import_module("qrs_source.signal_generator")
    bt = importlib.import_module("qrs_source.backtest")
    vpin = load_module("vpin_source", vpin_root / "vpin_timing.py")
    out = ROOT / "data" / "external"
    out.mkdir(parents=True, exist_ok=True)
    metadata = {"cost_bps_per_unit_turnover": args.cost_bps, "periods_per_year": 252,
                "qrs_commit": revision(qrs_root), "vpin_commit": revision(vpin_root),
                "notes": ["Declared small sensitivity grid, not the complete historical search universe.",
                          "QRS uses only ma_compare: the upstream price_compare/ma_cross branches map same-day daily closes to intraday bars.",
                          "VPIN roll returns are unavailable; these dates are dropped for every candidate, never treated as measured zero returns.",
                          "Costs are scenario assumptions, not verified brokerage fees. Strategy-switching costs are not included in dynamic diagnostics."],
                "datasets": {}}
    for contract in ("T", "TL"):
        path = qrs_root / "data" / "cache" / f"{contract.lower()}_5min.parquet"
        raw = pd.read_parquet(path)
        if "date" not in raw:
            raw = raw.reset_index()
        raw["date"] = pd.to_datetime(raw["date"])
        matrices, grid = {}, []
        for n, m in ((16, 600), (20, 800)):
            features = calc.calculate_qrs_intraday(raw, N=n, M=m, n=2.0)
            for threshold in (.3, .5, .7):
                label = f"qrs_N{n}_M{m}_S{threshold:g}"
                signals = signal.generate_qrs_intraday_signals(features, S=threshold, trend_method="ma_compare", ma_len_days=5, compare_lag_days=2)
                backtest = bt.run_intraday_backtest(signals)
                costs = backtest.position.diff().abs().fillna(backtest.position.abs()) * args.cost_bps / 1e4
                net = pd.Series((backtest.ret_strategy - costs).to_numpy(), index=pd.DatetimeIndex(backtest.date))
                daily = (1 + net).groupby(net.index.normalize()).prod() - 1
                matrices[label] = daily
                grid.append({"strategy": label, "N": n, "M": m, "S": threshold, "trend_method": "ma_compare"})
        frame = pd.DataFrame(matrices).iloc[20:]  # Common warm-up for largest QRS/trend window.
        name = f"QRS_{contract}"
        frame.to_csv(out / f"{name}.csv", index_label="datetime")
        metadata["datasets"][name] = {"input": path.relative_to(qrs_root).as_posix(), "rows": len(frame),
            "start": str(frame.index.min().date()), "end": str(frame.index.max().date()), "candidates": grid}

    published = pd.read_csv(vpin_root / "data" / "processed" / "vpin_daily.csv", parse_dates=["date"])
    for contract in ("T", "TL"):
        raw = published.loc[published.contract == contract].sort_values("date").reset_index(drop=True)
        raw = raw.drop(columns=["future_return"], errors="ignore")
        matrices, grid = {}, []
        for slope_window in (3, 5, 10):
            features = raw.copy()
            features["daily_vpin_slope"] = vpin.rolling_linear_slope(features.daily_mean_vpin, slope_window)
            for threshold in (.7, .8, .9):
                label = f"vpin_slope{slope_window}_p{threshold:g}"
                signals = vpin.generate_vpin_signal(features, high_percentile_threshold=threshold)
                turnover = signals.position.diff().abs().fillna(signals.position.abs())
                net = signals.position * signals.daily_return - turnover * args.cost_bps / 1e4
                ready = features.daily_vpin_percentile.notna() & features.daily_vpin_slope.notna()
                net = net.where(ready.shift(1, fill_value=False))
                matrices[label] = pd.Series(net.to_numpy(), index=pd.DatetimeIndex(signals.date))
                grid.append({"strategy": label, "slope_window": slope_window, "percentile_threshold": threshold})
        frame = pd.DataFrame(matrices)
        dropped = int(frame.isna().any(axis=1).sum())
        frame = frame.dropna()
        name = f"VPIN_{contract}"
        frame.to_csv(out / f"{name}.csv", index_label="datetime")
        metadata["datasets"][name] = {"input": "data/processed/vpin_daily.csv", "rows": len(frame),
            "dropped_unavailable_or_warmup_days": dropped, "start": str(frame.index.min().date()),
            "end": str(frame.index.max().date()), "candidates": grid}
    (out / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({key: {k: v for k, v in value.items() if k != "candidates"} for key, value in metadata["datasets"].items()}, indent=2))


if __name__ == "__main__":
    main()

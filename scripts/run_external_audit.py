"""Strict CSV entry point for daily candidate matrices; does not fill missing returns."""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cscv import run_cscv
from src.dynamic_selection_audit import run_dynamic_selection_audit


def load_matrix(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        columns = next(csv.reader(stream))[1:]
    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate candidate columns are not allowed")
    matrix = pd.read_csv(path, index_col=0, parse_dates=[0])
    if not isinstance(matrix.index, pd.DatetimeIndex) or matrix.index.hasnans or not matrix.index.is_monotonic_increasing or matrix.index.has_duplicates:
        raise ValueError("Matrix requires unique, increasing timestamps")
    if matrix.shape[1] < 2 or not matrix.columns.is_unique:
        raise ValueError("At least two unique candidate columns are required")
    if not np.isfinite(matrix.to_numpy(dtype=float)).all() or (matrix <= -1).any().any():
        raise ValueError("Returns must be finite and greater than -100%; missing is not zero")
    if (matrix.std() == 0).any():
        raise ValueError("Constant candidate cannot be ranked by Sharpe")
    return matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data" / "external")
    args = parser.parse_args()
    out = ROOT / "results" / "external_audit"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in ("QRS_T", "QRS_TL", "VPIN_T", "VPIN_TL"):
        matrix = load_matrix(args.input_dir / f"{name}.csv")
        static = run_cscv(matrix, n_splits=8, periods_per_year=252)
        # Non-overlapping OOS blocks; windows are observed rows, not calendar days.
        dynamic = run_dynamic_selection_audit(matrix, 120, 20, 20, periods_per_year=252)
        static["splits"].to_csv(out / f"{name}_cscv.csv", index=False)
        dynamic["splits"].to_csv(out / f"{name}_walk_forward.csv", index=False)
        rows.append({"dataset": name, "start": str(matrix.index.min().date()), "end": str(matrix.index.max().date()),
            "candidates": matrix.shape[1], "observations": len(matrix), "PBO": static["summary"]["PBO"],
            "dynamic_failure_rate": dynamic["summary"]["dynamic_selection_failure_rate"],
            "windows": dynamic["summary"]["n_windows"], "selected_oos_sharpe": dynamic["summary"]["mean_selected_oos_sharpe"],
            "switches": dynamic["summary"]["parameter_switch_count"]})
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "settings.json").write_text(json.dumps({"static_blocks": 8, "annualization": 252, "train_rows": 120,
        "test_rows": 20, "step_rows": 20, "overlapping_test_windows": False}, indent=2), encoding="utf-8")
    report = "# QRS / VPIN external candidate audit\n\n" + summary.to_markdown(index=False, floatfmt=".4f")
    report += "\n\n输入与候选集见 ../../data/external/provenance.json；输入收益矩阵同时保存。QRS 为 6 组因果 ma_compare 配置，VPIN 为 9 组阈值/斜率配置，均为事先声明的小网格，不能代表完整历史参数搜索的 PBO。\n\n"
    report += "CSCV 使用 8 个连续区块和 70 个对称组合，是回顾性选参诊断；动态审计采用 120 个有效观察训练、20 个观察检验，每 20 个观察前进一次，测试区间不重叠。VPIN 剔除换月收益缺失与预热日期，窗口不是连续交易日；252 为观察频率约定。成本为每单位换手 1 bp 情景，未额外模拟动态切换策略的开平仓成本。\n\n"
    report += "平均窗口夏普不是拼接实盘组合的夏普；PBO 和失败率均不等于亏损概率。原始行情、换月构造及候选策略本身的局限仍适用。QRS 的另两种趋势分支因使用当日收盘映射盘中而未纳入本次因果候选集。\n"
    (out / "report.md").write_text(report, encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

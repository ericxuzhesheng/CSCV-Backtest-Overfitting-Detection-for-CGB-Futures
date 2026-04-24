from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

from .utils import DEFAULT_START_DATE, FIGURES_DIR, PROJECT_ROOT, RESULTS_DIR, TABLES_DIR


CSCV_FIGURES = [
    "pbo_histogram",
    "rank_logit",
    "is_vs_oos",
    "oos_rank_distribution",
]

DYNAMIC_FIGURES = [
    "selection_score_vs_oos",
    "selected_oos_rank",
    "parameter_stability",
    "dynamic_failure_rate",
]


def _fmt(value: object) -> str:
    if isinstance(value, float):
        if pd.isna(value):
            return "n/a"
        if abs(value) >= 100:
            return f"{value:.2f}"
        return f"{value:.4f}"
    return str(value)


def _markdown_table(df: pd.DataFrame, columns: Iterable[str], empty_text_zh: str, empty_text_en: str) -> str:
    cols = [col for col in columns if col in df.columns]
    if df.empty or not cols:
        return f"{empty_text_zh}\n\n{empty_text_en}"
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = ["| " + " | ".join(_fmt(row[col]) for col in cols) + " |" for _, row in df[cols].iterrows()]
    return "\n".join([header, sep, *rows])


def _load_table(name: str) -> pd.DataFrame:
    path = TABLES_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _figure_markdown(contract: str, stems: list[str], prefix: str = "results/") -> str:
    lines = []
    for stem in stems:
        file_name = f"{stem}_{contract}.png"
        path = FIGURES_DIR / file_name
        if path.exists():
            lines.append(f"![{contract} {stem}]({prefix}figures/{file_name})")
    return "\n\n".join(lines)


def _report_figure_markdown(contract: str, stems: list[str]) -> str:
    return _figure_markdown(contract, stems, prefix="")


def _section_or_placeholder(content: str, zh_empty: str, en_empty: str) -> str:
    if content.strip():
        return content
    return f"{zh_empty}\n\n{en_empty}"


def _references() -> str:
    return """1. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. Journal of Computational Finance.
2. Bailey, D. H., & López de Prado, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
3. López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.

The Dynamic Parameter Selection Audit in this repository borrows the walk-forward validation idea to complement CSCV/PBO. It is not standard PBO and does not replace CSCV."""


def generate_readme(start_date: str = DEFAULT_START_DATE) -> Path:
    cscv_summary = _load_table("cscv_summary_all.csv")
    dynamic_summary = _load_table("dynamic_audit_summary_all.csv")
    cscv_table = _markdown_table(
        cscv_summary,
        [
            "contract",
            "sample_start",
            "sample_end",
            "n_strategies",
            "n_combinations",
            "PBO",
            "median_oos_rank",
            "mean_is_performance",
            "mean_oos_performance",
            "degradation_ratio",
        ],
        "暂无 CSCV 结果，请先运行 pipeline。",
        "No CSCV results yet. Run the pipeline first.",
    )
    dynamic_table = _markdown_table(
        dynamic_summary,
        [
            "contract",
            "n_windows",
            "selection_metric",
            "dynamic_selection_failure_rate",
            "mean_selected_oos_percentile",
            "score_oos_corr",
            "score_oos_rank_corr",
            "parameter_switch_count",
            "parameter_entropy",
        ],
        "暂无 Dynamic Audit 结果，请先运行 pipeline。",
        "No dynamic audit results yet. Run the pipeline first.",
    )

    readme = f"""# 国债期货 CSCV 回测过拟合检验框架 | CSCV Backtest Overfitting Detection for CGB Futures

<p align="center">
  <a href="#zh"><img src="https://img.shields.io/badge/LANGUAGE-%E4%B8%AD%E6%96%87-E84D3D?style=for-the-badge&labelColor=3B3F47" alt="LANGUAGE 中文"></a>
  <a href="#en"><img src="https://img.shields.io/badge/LANGUAGE-ENGLISH-2F73C9?style=for-the-badge&labelColor=3B3F47" alt="LANGUAGE ENGLISH"></a>
</p>

<a id="zh"></a>

## 中文

### 1. 项目简介

本仓库是面向国债期货 T / TL 多参数策略的稳健性验证框架，核心仍是标准 CSCV/PBO，同时新增通用的 Dynamic Parameter Selection Audit。仓库输入是通用策略收益矩阵，不绑定任何特定策略族。

### 2. CSCV / PBO 方法原理

CSCV/PBO 是标准组合对称交叉验证框架。它把完整样本切成连续 blocks，枚举对称的 IS/OOS 组合，在 IS 中选择最优策略，然后观察该策略在 OOS 中的排名。若 OOS percentile 低于 0.5，则记为过拟合事件，PBO 为这些事件占比。

### 3. Dynamic Parameter Selection Audit

Dynamic Parameter Selection Audit 是通用 walk-forward 参数选择稳健性诊断。它在训练窗口中根据 `selection_metric` 选择策略，在下一段 OOS 窗口中检验真实表现，并统计 `selected_oos_rank`、`selected_oos_percentile`、`dynamic_selection_failure_rate`、`selection_score_vs_oos_performance` 和 `parameter_stability`。

### 4. CSCV 与 Dynamic Audit 的区别

- CSCV/PBO 检测静态参数搜索在对称样本切分下的过拟合风险。
- Dynamic Audit 检测滚动训练窗口中的动态选参是否稳定。
- `dynamic_selection_failure_rate` 不是标准 PBO。
- Dynamic Audit 不替代 CSCV，而是补充诊断动态选参过程是否把过拟合从静态 grid search 转移到滚动窗口。

### 5. 数据与策略收益矩阵

输入数据标准化为 `datetime/open/high/low/close/volume/open_interest`。策略收益矩阵的行是 5 分钟 bar，列是 `strategy_id / parameter_id`。信号在 bar `t` 形成，收益用 `position.shift(1)` 落在 bar `t+1`，避免 future leakage。默认年化频率为 `252 * 54`。

### 6. T / TL 检验结果

#### CSCV / PBO

{cscv_table}

#### Dynamic Parameter Selection Audit

{dynamic_table}

### 7. 图表展示

#### T

{_section_or_placeholder(_figure_markdown("T", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 T 图表。", "No T figures yet.")}

#### TL

{_section_or_placeholder(_figure_markdown("TL", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 TL 图表。", "No TL figures yet.")}

### 8. 快速开始

```bash
pip install -r requirements.txt
python -m compileall src scripts
```

若缺少数据，请将以下文件放入 `data/raw/`：

- `10年国债期货_5min_3年.xlsx`
- `30年国债期货_5min_2年.xlsx`

### 9. 运行命令

```bash
python scripts/run_cscv_pipeline.py --mode strategy_matrix --contract ALL --start-date {start_date}
python scripts/run_cscv_pipeline.py --mode cscv --contract ALL --n-splits 8 --start-date {start_date}
python scripts/run_cscv_pipeline.py --mode dynamic_audit --contract ALL --train-window-days 60 --test-window-days 10 --rebalance-days 1 --selection-metric sharpe --start-date {start_date}
python scripts/run_cscv_pipeline.py --mode full --contract ALL --n-splits 8 --train-window-days 60 --test-window-days 10 --rebalance-days 1 --selection-metric sharpe --start-date {start_date}
python cscv_t_strategy.py --mode full --contract ALL --n-splits 8
```

### 10. 输出文件

- `results/tables/strategy_returns_T.csv`
- `results/tables/strategy_returns_TL.csv`
- `results/tables/cscv_summary_all.csv`
- `results/tables/dynamic_audit_summary_all.csv`
- `results/tables/parameter_stability_T.csv`
- `results/tables/parameter_stability_TL.csv`
- `results/figures/*.png`
- `results/report.md`

### 11. 方法论来源

{_references()}

### 12. 局限性与免责声明

本仓库用于研究和工程复现，不构成投资建议。结果依赖数据质量、交易成本、滑点、换月规则和参数空间。Dynamic Audit 不会把 OOS 结果反向用于训练，也不应用于策略调参闭环。

<a id="en"></a>

## English

### 1. Project Overview

This repository is a CSCV-based backtest overfitting detection and robustness validation framework for CGB futures strategies. It preserves the standard CSCV/PBO workflow and adds a generic Dynamic Parameter Selection Audit. The input is a generic strategy return matrix and the framework is not tied to any specific strategy family.

### 2. CSCV / PBO Methodology

CSCV/PBO is the standard combinatorially symmetric cross-validation framework. It partitions the return matrix into chronological blocks, enumerates balanced IS/OOS combinations, selects the in-sample winner, and measures where that winner ranks out-of-sample.

### 3. Dynamic Parameter Selection Audit

The Dynamic Parameter Selection Audit is a generic walk-forward parameter-selection diagnostic. It selects parameters inside a training window using a chosen `selection_metric`, evaluates the selected strategy in the next OOS window, and reports `selected_oos_rank`, `selected_oos_percentile`, `dynamic_selection_failure_rate`, score-vs-OOS correlations, and parameter stability.

### 4. Difference between CSCV and Dynamic Audit

- CSCV/PBO measures static parameter-search overfitting risk under symmetric splits.
- Dynamic Audit measures whether rolling parameter selection remains stable out-of-sample.
- `dynamic_selection_failure_rate` is not standard PBO.
- Dynamic Audit complements CSCV; it does not replace it.

### 5. Data and Strategy Return Matrix

The pipeline standardizes raw data into `datetime/open/high/low/close/volume/open_interest`. The strategy return matrix uses timestamps as rows and strategy or parameter IDs as columns. Signals are formed at bar `t`; returns are earned with `position.shift(1)` on bar `t+1`, which is the leakage guard. The annualization frequency is `252 * 54`.

### 6. T / TL Validation Results

#### CSCV / PBO

{cscv_table}

#### Dynamic Parameter Selection Audit

{dynamic_table}

### 7. Figures

#### T

{_section_or_placeholder(_figure_markdown("T", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 T 图表。", "No T figures yet.")}

#### TL

{_section_or_placeholder(_figure_markdown("TL", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 TL 图表。", "No TL figures yet.")}

### 8. Quick Start

```bash
pip install -r requirements.txt
python -m compileall src scripts
```

If data is missing, place these files under `data/raw/`:

- `10年国债期货_5min_3年.xlsx`
- `30年国债期货_5min_2年.xlsx`

### 9. Example Commands

```bash
python scripts/run_cscv_pipeline.py --mode full --contract ALL --n-splits 8 --train-window-days 60 --test-window-days 10 --rebalance-days 1 --selection-metric sharpe --start-date {start_date}
python cscv_t_strategy.py --mode full --contract ALL --n-splits 8
```

### 10. Output Files

- `results/tables/strategy_returns_T.csv`
- `results/tables/strategy_returns_TL.csv`
- `results/tables/cscv_summary_all.csv`
- `results/tables/dynamic_audit_summary_all.csv`
- `results/tables/parameter_stability_T.csv`
- `results/tables/parameter_stability_TL.csv`
- `results/figures/*.png`
- `results/report.md`

### 11. References

{_references()}

### 12. Limitations and Disclaimer

This repository is for research and engineering reproduction only. Results depend on data quality, transaction costs, slippage, roll handling, and the searched parameter universe. Dynamic audit results are diagnostics only and are not fed back into the training window for optimization.
"""
    path = PROJECT_ROOT / "README.md"
    path.write_text(readme, encoding="utf-8")
    return path


def generate_results_report(start_date: str = DEFAULT_START_DATE) -> Path:
    cscv_summary = _load_table("cscv_summary_all.csv")
    dynamic_summary = _load_table("dynamic_audit_summary_all.csv")
    cscv_table = _markdown_table(
        cscv_summary,
        [
            "contract",
            "sample_start",
            "sample_end",
            "rows",
            "n_strategies",
            "n_combinations",
            "PBO",
            "median_oos_rank",
            "mean_is_performance",
            "mean_oos_performance",
            "best_overall_strategy",
            "best_oos_strategy",
        ],
        "暂无 CSCV 结果。",
        "No CSCV results available.",
    )
    dynamic_table = _markdown_table(
        dynamic_summary,
        [
            "contract",
            "n_windows",
            "selection_metric",
            "dynamic_selection_failure_rate",
            "mean_selected_oos_return",
            "mean_selected_oos_sharpe",
            "mean_selected_oos_percentile",
            "score_oos_corr",
            "score_oos_rank_corr",
            "parameter_switch_count",
            "most_frequent_strategy",
            "parameter_entropy",
            "average_holding_windows",
        ],
        "暂无 Dynamic Audit 结果。",
        "No dynamic audit results available.",
    )

    report = f"""# CSCV Backtest Overfitting Report | 国债期货 CSCV 回测过拟合检验报告

## 中文报告

### 1. CSCV 方法

CSCV 是标准组合对称交叉验证方法，用于检测参数搜索导致的回测过拟合。仓库保留了原有 CSCV/PBO 功能，PBO 仍定义为 OOS percentile 低于 0.5 的 split 占比。

### 2. Dynamic Parameter Selection Audit 方法

Dynamic Parameter Selection Audit 是通用 walk-forward 参数选择稳健性诊断。它在训练窗口内按 `selection_metric` 选参，在下一段 OOS 窗口中检验真实表现，并输出 `selected_oos_rank`、`selected_oos_percentile`、`dynamic_selection_failure_rate`、`score_oos_corr`、`score_oos_rank_corr` 和 `parameter_stability`。

### 3. 二者区别

- CSCV/PBO 关注静态参数搜索的过拟合风险。
- Dynamic Audit 关注滚动训练窗口中的动态选参稳定性。
- `dynamic_selection_failure_rate` 不是标准 PBO。
- Dynamic Audit 借鉴 walk-forward validation，但不替代 CSCV。

### 4. 数据说明

默认评估样本从 `{start_date}` 开始，原始数据应放在 `data/raw/`。支持 T 与 TL 两个合约。若数据不存在，pipeline 会直接报缺失，不会伪造结果。

### 5. 策略收益矩阵

策略收益矩阵的行是 5 分钟 bar，列是参数组合。信号在 bar `t` 形成，收益通过 `position.shift(1)` 在 bar `t+1` 实现，避免 future leakage。

### 6. IS/OOS split 设计

CSCV 采用对称 block 切分。Dynamic Audit 采用滚动训练窗口和紧随其后的 OOS 测试窗口，训练集与测试集不重叠，OOS 数据不参与训练窗口选参。

### 7. PBO 计算

PBO 仅对应标准 CSCV/PBO：在每个 CSCV split 内，先用 IS 选出最优策略，再看该策略在 OOS 中是否落入后 50%。

### 8. dynamic_selection_failure_rate 计算

Dynamic Audit 在每个 walk-forward 窗口内记录被选策略的 OOS percentile。若 percentile `< 0.5`，则该窗口记为 failure。`dynamic_selection_failure_rate` 为 failure 窗口占比。

### 9. T / TL 结果

#### CSCV / PBO

{cscv_table}

#### Dynamic Parameter Selection Audit

{dynamic_table}

### 10. 图表

#### T

{_section_or_placeholder(_report_figure_markdown("T", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 T 图表。", "No T figures yet.")}

#### TL

{_section_or_placeholder(_report_figure_markdown("TL", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 TL 图表。", "No TL figures yet.")}

### 11. 局限性

结果未完整建模交易成本、滑点、换月与实盘流动性。Dynamic Audit 是诊断工具，不应把 OOS 结果反向用于训练窗口选参。

### 12. References

{_references()}

### 13. Disclaimer

本仓库仅用于研究与工程复现，不构成投资建议。

## English Report

### 1. CSCV Method

CSCV is the standard combinatorially symmetric cross-validation method for backtest-overfitting detection. The repository preserves the original CSCV/PBO functionality. PBO remains the share of CSCV splits where the selected strategy ranks below the 50th OOS percentile.

### 2. Dynamic Parameter Selection Audit

The Dynamic Parameter Selection Audit is a generic walk-forward parameter-selection diagnostic. It selects parameters in the training window, evaluates the selected strategy in the next OOS window, and reports `selected_oos_rank`, `selected_oos_percentile`, `dynamic_selection_failure_rate`, score-vs-OOS correlations, and parameter stability.

### 3. Difference between the Two

- CSCV/PBO measures static parameter-search overfitting risk.
- Dynamic Audit measures the stability of rolling parameter selection.
- `dynamic_selection_failure_rate` is not standard PBO.
- Dynamic Audit complements CSCV and does not replace it.

### 4. Data

The default evaluation sample starts on `{start_date}`. Raw files should be placed in `data/raw/`. The framework supports T and TL. Missing data stops the pipeline instead of generating fabricated results.

### 5. Strategy Return Matrix

Rows are 5-minute bars and columns are strategy or parameter IDs. Signals are formed on bar `t`; returns are earned on bar `t+1` via `position.shift(1)`, which is the leakage control.

### 6. IS/OOS Split Design

CSCV uses symmetric block splits. Dynamic Audit uses rolling training windows followed by the next OOS test window. OOS data is never used for parameter selection inside the training window.

### 7. PBO Calculation

PBO refers only to the standard CSCV module: pick the in-sample winner and test whether its OOS percentile rank falls into the worse half.

### 8. dynamic_selection_failure_rate Calculation

Dynamic Audit records the selected strategy's OOS percentile in each walk-forward window. A window is a failure when percentile `< 0.5`. The failure rate is the share of such windows.

### 9. T / TL Results

#### CSCV / PBO

{cscv_table}

#### Dynamic Parameter Selection Audit

{dynamic_table}

### 10. Figures

#### T

{_section_or_placeholder(_report_figure_markdown("T", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 T 图表。", "No T figures yet.")}

#### TL

{_section_or_placeholder(_report_figure_markdown("TL", CSCV_FIGURES + DYNAMIC_FIGURES), "暂无 TL 图表。", "No TL figures yet.")}

### 11. Limitations

The outputs do not fully model transaction costs, slippage, rolling mechanics, or live-execution constraints. Dynamic Audit is diagnostic only and should not be fed back into the training window as an optimization loop.

### 12. References

{_references()}

### 13. Disclaimer

This repository is for research and engineering reproduction only and does not constitute investment advice.
"""
    path = RESULTS_DIR / "report.md"
    path.write_text(report, encoding="utf-8")
    return path


def generate_all_reports(start_date: str = DEFAULT_START_DATE) -> Dict[str, Path]:
    return {
        "README.md": generate_readme(start_date),
        "results/report.md": generate_results_report(start_date),
    }

# 国债期货 CSCV 回测过拟合检验框架 | CSCV Backtest Overfitting Detection for CGB Futures

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

### 4. 核心对比：固定参数 (CSCV) vs. 动态参数 (Dynamic Audit)

本框架同时提供两种维度的过拟合检测，它们分别回答了不同的稳健性问题：

- **固定参数 (CSCV/PBO)**：回答“如果我们只选一个固定参数跑全过程，这个选参过程过拟合了吗？”
- **动态参数 (Dynamic Audit)**：回答“如果我们允许根据最近表现动态切换参数，这个‘择优’逻辑在样本外是否失效？”

#### 4.1 核心指标深度对比

| 维度 | T (10年国债期货) | TL (30年国债期货) |
| :--- | :--- | :--- |
| **1. 静态过拟合 (CSCV/PBO)** | **0.6429 (高风险)** | **0.5000 (中性)** |
| *解读* | 静态选参在 64% 的情况下选出的“最优”在样本外表现平庸。 | 选参逻辑在 50% 情况下有效，接近随机基准。 |
| **2. 动态失效概率 (Dynamic Failure)** | **0.5351** | **0.4748** |
| *解读* | 动态切换参数依然有超过一半的窗口在样本外排名靠后。 | 动态选参表现略优于中位数（50%），相对更稳健。 |
| **3. 性能衰减 (Degradation)** | **-14.73%** | **+3.41%** |
| *解读* | 样本外表现出现显著负值衰减。 | 样本外表现保持正向稳定性。 |
| **4. 参数稳定性 (Switching)** | **157 次切换 (高熵)** | **127 次切换 (低熵)** |
| *解读* | T 合约的最优参数极其不稳定，可能在捕捉噪声。 | TL 合约的最优参数具有更强的延续性。 |

#### 4.2 可视化对比分析

为了更直观地观察过拟合，我们将两种框架的典型图表进行配对：

##### **对比 A：过拟合概率分布**
- **CSCV (PBO 直方图)**：衡量参数空间的整体陷阱。
- **Dynamic (失效频率图)**：衡量选参逻辑在时间序列上的连续稳定性。

| T 合约 (高风险) | TL 合约 (稳健) |
| :---: | :---: |
| ![T pbo_histogram](results/figures/pbo_histogram_T.png) | ![TL pbo_histogram](results/figures/pbo_histogram_TL.png) |
| ![T dynamic_failure_rate](results/figures/dynamic_failure_rate_T.png) | ![TL dynamic_failure_rate](results/figures/dynamic_failure_rate_TL.png) |

##### **对比 B：预测力验证**
- **CSCV (IS vs OOS)**：展示 IS 排名与 OOS 表现的非线性关系。
- **Dynamic (Score vs OOS)**：展示当前选参指标对下一期表现的实际预测能力（相关性）。

| T 合约 (预测力差) | TL 合约 (有一定延续性) |
| :---: | :---: |
| ![T is_vs_oos](results/figures/is_vs_oos_T.png) | ![TL is_vs_oos](results/figures/is_vs_oos_TL.png) |
| ![T selection_score_vs_oos](results/figures/selection_score_vs_oos_T.png) | ![TL selection_score_vs_oos](results/figures/selection_score_vs_oos_TL.png) |

#### 4.3 综合结论
1. **策略脆弱性**：T 合约在两个框架下均显示出较高的过拟合风险。这意味着在 T 合约上进行参数优化（无论是静态还是滚动动态）都极易陷入噪声陷阱。
2. **市场特性差异**：TL 合约展现了更好的参数延续性（Score-OOS 正相关性更高，Switching 更少）。这可能源于 30 年债期货趋势性更强，参数对趋势的捕捉更稳健。
3. **互补性说明**：CSCV 发现的是“空间”上的过拟合（参数组合多导致的偶然性），而 Dynamic Audit 发现的是“时间”上的失效（历史最优在未来失效的频率）。

### 5. CSCV 与 Dynamic Audit 的区别 (详细补充)

### 5. 数据与策略收益矩阵

输入数据标准化为 `datetime/open/high/low/close/volume/open_interest`。策略收益矩阵的行是 5 分钟 bar，列是 `strategy_id / parameter_id`。信号在 bar `t` 形成，收益用 `position.shift(1)` 落在 bar `t+1`，避免 future leakage。默认年化频率为 `252 * 54`。

### 6. T / TL 检验结果

#### CSCV / PBO

| contract | sample_start | sample_end | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | degradation_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | -0.1473 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | 0.0341 |

#### Dynamic Parameter Selection Audit

| contract | n_windows | selection_metric | dynamic_selection_failure_rate | mean_selected_oos_percentile | score_oos_corr | score_oos_rank_corr | parameter_switch_count | parameter_entropy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 456 | sharpe | 0.5351 | 0.4588 | -0.0065 | -0.0029 | 157 | 4.0459 |
| TL | 457 | sharpe | 0.4748 | 0.5387 | 0.0522 | 0.0298 | 127 | 3.6166 |

### 7. 图表展示

#### T

![T pbo_histogram](results/figures/pbo_histogram_T.png)

![T rank_logit](results/figures/rank_logit_T.png)

![T is_vs_oos](results/figures/is_vs_oos_T.png)

![T oos_rank_distribution](results/figures/oos_rank_distribution_T.png)

![T selection_score_vs_oos](results/figures/selection_score_vs_oos_T.png)

![T selected_oos_rank](results/figures/selected_oos_rank_T.png)

![T parameter_stability](results/figures/parameter_stability_T.png)

![T dynamic_failure_rate](results/figures/dynamic_failure_rate_T.png)

#### TL

![TL pbo_histogram](results/figures/pbo_histogram_TL.png)

![TL rank_logit](results/figures/rank_logit_TL.png)

![TL is_vs_oos](results/figures/is_vs_oos_TL.png)

![TL oos_rank_distribution](results/figures/oos_rank_distribution_TL.png)

![TL selection_score_vs_oos](results/figures/selection_score_vs_oos_TL.png)

![TL selected_oos_rank](results/figures/selected_oos_rank_TL.png)

![TL parameter_stability](results/figures/parameter_stability_TL.png)

![TL dynamic_failure_rate](results/figures/dynamic_failure_rate_TL.png)

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
python scripts/run_cscv_pipeline.py --mode strategy_matrix --contract ALL --start-date 2024-01-01
python scripts/run_cscv_pipeline.py --mode cscv --contract ALL --n-splits 8 --start-date 2024-01-01
python scripts/run_cscv_pipeline.py --mode dynamic_audit --contract ALL --train-window-days 60 --test-window-days 10 --rebalance-days 1 --selection-metric sharpe --start-date 2024-01-01
python scripts/run_cscv_pipeline.py --mode full --contract ALL --n-splits 8 --train-window-days 60 --test-window-days 10 --rebalance-days 1 --selection-metric sharpe --start-date 2024-01-01
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

1. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. Journal of Computational Finance.
2. Bailey, D. H., & López de Prado, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
3. López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.

The Dynamic Parameter Selection Audit in this repository borrows the walk-forward validation idea to complement CSCV/PBO. It is not standard PBO and does not replace CSCV.

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

| contract | sample_start | sample_end | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | degradation_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | -0.1473 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | 0.0341 |

#### Dynamic Parameter Selection Audit

| contract | n_windows | selection_metric | dynamic_selection_failure_rate | mean_selected_oos_percentile | score_oos_corr | score_oos_rank_corr | parameter_switch_count | parameter_entropy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 456 | sharpe | 0.5351 | 0.4588 | -0.0065 | -0.0029 | 157 | 4.0459 |
| TL | 457 | sharpe | 0.4748 | 0.5387 | 0.0522 | 0.0298 | 127 | 3.6166 |

### 7. Figures

#### T

![T pbo_histogram](results/figures/pbo_histogram_T.png)

![T rank_logit](results/figures/rank_logit_T.png)

![T is_vs_oos](results/figures/is_vs_oos_T.png)

![T oos_rank_distribution](results/figures/oos_rank_distribution_T.png)

![T selection_score_vs_oos](results/figures/selection_score_vs_oos_T.png)

![T selected_oos_rank](results/figures/selected_oos_rank_T.png)

![T parameter_stability](results/figures/parameter_stability_T.png)

![T dynamic_failure_rate](results/figures/dynamic_failure_rate_T.png)

#### TL

![TL pbo_histogram](results/figures/pbo_histogram_TL.png)

![TL rank_logit](results/figures/rank_logit_TL.png)

![TL is_vs_oos](results/figures/is_vs_oos_TL.png)

![TL oos_rank_distribution](results/figures/oos_rank_distribution_TL.png)

![TL selection_score_vs_oos](results/figures/selection_score_vs_oos_TL.png)

![TL selected_oos_rank](results/figures/selected_oos_rank_TL.png)

![TL parameter_stability](results/figures/parameter_stability_TL.png)

![TL dynamic_failure_rate](results/figures/dynamic_failure_rate_TL.png)

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
python scripts/run_cscv_pipeline.py --mode full --contract ALL --n-splits 8 --train-window-days 60 --test-window-days 10 --rebalance-days 1 --selection-metric sharpe --start-date 2024-01-01
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

1. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. Journal of Computational Finance.
2. Bailey, D. H., & López de Prado, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
3. López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.

The Dynamic Parameter Selection Audit in this repository borrows the walk-forward validation idea to complement CSCV/PBO. It is not standard PBO and does not replace CSCV.

### 12. Limitations and Disclaimer

This repository is for research and engineering reproduction only. Results depend on data quality, transaction costs, slippage, roll handling, and the searched parameter universe. Dynamic audit results are diagnostics only and are not fed back into the training window for optimization.

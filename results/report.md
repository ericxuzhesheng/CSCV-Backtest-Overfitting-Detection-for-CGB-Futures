# CSCV Backtest Overfitting Report | 国债期货 CSCV 回测过拟合检验报告

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

默认评估样本从 `2024-01-01` 开始，原始数据应放在 `data/raw/`。支持 T 与 TL 两个合约。若数据不存在，pipeline 会直接报缺失，不会伪造结果。

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

| contract | sample_start | sample_end | rows | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | best_overall_strategy | best_oos_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 28352 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | nf_0031_ns_0107 | nf_0031_ns_0107 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 28451 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | nf_0047_ns_1630 | nf_0047_ns_1630 |

#### Dynamic Parameter Selection Audit

| contract | n_windows | selection_metric | dynamic_selection_failure_rate | mean_selected_oos_return | mean_selected_oos_sharpe | mean_selected_oos_percentile | score_oos_corr | score_oos_rank_corr | parameter_switch_count | most_frequent_strategy | parameter_entropy | average_holding_windows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 456 | sharpe | 0.5351 | -0.0006 | -1.0419 | 0.4588 | -0.0065 | -0.0029 | 157 | nf_0090_ns_0107 | 4.0459 | 2.8861 |
| TL | 457 | sharpe | 0.4748 | 0.0018 | 1.0953 | 0.5387 | 0.0522 | 0.0298 | 127 | nf_0026_ns_0160 | 3.6166 | 3.5703 |

### 10. 图表

#### T

![T pbo_histogram](figures/pbo_histogram_T.png)

![T rank_logit](figures/rank_logit_T.png)

![T is_vs_oos](figures/is_vs_oos_T.png)

![T oos_rank_distribution](figures/oos_rank_distribution_T.png)

![T selection_score_vs_oos](figures/selection_score_vs_oos_T.png)

![T selected_oos_rank](figures/selected_oos_rank_T.png)

![T parameter_stability](figures/parameter_stability_T.png)

![T dynamic_failure_rate](figures/dynamic_failure_rate_T.png)

#### TL

![TL pbo_histogram](figures/pbo_histogram_TL.png)

![TL rank_logit](figures/rank_logit_TL.png)

![TL is_vs_oos](figures/is_vs_oos_TL.png)

![TL oos_rank_distribution](figures/oos_rank_distribution_TL.png)

![TL selection_score_vs_oos](figures/selection_score_vs_oos_TL.png)

![TL selected_oos_rank](figures/selected_oos_rank_TL.png)

![TL parameter_stability](figures/parameter_stability_TL.png)

![TL dynamic_failure_rate](figures/dynamic_failure_rate_TL.png)

### 11. 局限性

结果未完整建模交易成本、滑点、换月与实盘流动性。Dynamic Audit 是诊断工具，不应把 OOS 结果反向用于训练窗口选参。

### 12. References

1. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. Journal of Computational Finance.
2. Bailey, D. H., & López de Prado, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
3. López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.

The Dynamic Parameter Selection Audit in this repository borrows the walk-forward validation idea to complement CSCV/PBO. It is not standard PBO and does not replace CSCV.

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

The default evaluation sample starts on `2024-01-01`. Raw files should be placed in `data/raw/`. The framework supports T and TL. Missing data stops the pipeline instead of generating fabricated results.

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

| contract | sample_start | sample_end | rows | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | best_overall_strategy | best_oos_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 28352 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | nf_0031_ns_0107 | nf_0031_ns_0107 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 28451 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | nf_0047_ns_1630 | nf_0047_ns_1630 |

#### Dynamic Parameter Selection Audit

| contract | n_windows | selection_metric | dynamic_selection_failure_rate | mean_selected_oos_return | mean_selected_oos_sharpe | mean_selected_oos_percentile | score_oos_corr | score_oos_rank_corr | parameter_switch_count | most_frequent_strategy | parameter_entropy | average_holding_windows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 456 | sharpe | 0.5351 | -0.0006 | -1.0419 | 0.4588 | -0.0065 | -0.0029 | 157 | nf_0090_ns_0107 | 4.0459 | 2.8861 |
| TL | 457 | sharpe | 0.4748 | 0.0018 | 1.0953 | 0.5387 | 0.0522 | 0.0298 | 127 | nf_0026_ns_0160 | 3.6166 | 3.5703 |

### 10. Figures

#### T

![T pbo_histogram](figures/pbo_histogram_T.png)

![T rank_logit](figures/rank_logit_T.png)

![T is_vs_oos](figures/is_vs_oos_T.png)

![T oos_rank_distribution](figures/oos_rank_distribution_T.png)

![T selection_score_vs_oos](figures/selection_score_vs_oos_T.png)

![T selected_oos_rank](figures/selected_oos_rank_T.png)

![T parameter_stability](figures/parameter_stability_T.png)

![T dynamic_failure_rate](figures/dynamic_failure_rate_T.png)

#### TL

![TL pbo_histogram](figures/pbo_histogram_TL.png)

![TL rank_logit](figures/rank_logit_TL.png)

![TL is_vs_oos](figures/is_vs_oos_TL.png)

![TL oos_rank_distribution](figures/oos_rank_distribution_TL.png)

![TL selection_score_vs_oos](figures/selection_score_vs_oos_TL.png)

![TL selected_oos_rank](figures/selected_oos_rank_TL.png)

![TL parameter_stability](figures/parameter_stability_TL.png)

![TL dynamic_failure_rate](figures/dynamic_failure_rate_TL.png)

### 11. Limitations

The outputs do not fully model transaction costs, slippage, rolling mechanics, or live-execution constraints. Dynamic Audit is diagnostic only and should not be fed back into the training window as an optimization loop.

### 12. References

1. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. Journal of Computational Finance.
2. Bailey, D. H., & López de Prado, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.
3. López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.

The Dynamic Parameter Selection Audit in this repository borrows the walk-forward validation idea to complement CSCV/PBO. It is not standard PBO and does not replace CSCV.

### 13. Disclaimer

This repository is for research and engineering reproduction only and does not constitute investment advice.

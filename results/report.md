# CSCV Backtest Overfitting Report | 国债期货 CSCV 回测过拟合报告

## 中文报告

### CSCV 方法

CSCV 全称为 Combinatorially Symmetric Cross-Validation，组合对称交叉验证。本项目参考 Bailey, Borwein, López de Prado and Zhu 关于 *The Probability of Backtest Overfitting* 的研究，将其用于国债期货 T / TL 5 分钟策略参数检验，评估不同参数组合是否只是样本内拟合优异，而缺乏样本外稳健性。


将样本划分为 $S$ 个连续子样本：

$$
D = \{D_1, D_2, \ldots, D_S\}
$$

每次选择一半子样本作为样本内：

$$
D_{IS}^{(k)} \subset D, \quad D_{OOS}^{(k)} = D \setminus D_{IS}^{(k)}
$$

在样本内选择最优策略：

$$
j^* = \arg\max_j Sharpe_{IS}^{(k)}(j)
$$

观察该策略在样本外的百分位排名：

$$
Rank_{OOS}^{(k)}(j^*)
$$

本项目中 rank 方向为 $0 =$ 最差，$1 =$ 最好。如果样本外排名落入较差一半，则记为过拟合事件：

$$
I_k = \mathbb{1}(Rank_{OOS}^{(k)} < 0.5)
$$

PBO 定义为：

$$
PBO = \frac{1}{K} \sum_{k=1}^{K} I_k
$$

Rank logit 使用：

$$
\log\left(\frac{Rank_{OOS}^{(k)}}{1 - Rank_{OOS}^{(k)}}\right)
$$


### 数据说明

原始数据来自本地 Excel 文件，标准字段为 `datetime/open/high/low/close/volume/open_interest`。pipeline 自动识别 sheet、表头、中文和英文字段，删除重复时间戳并按时间升序排序。默认评估样本从 `2024-01-01` 开始。

### 策略收益矩阵

策略保留原始牛熊指标逻辑：用成交量/持仓量换手与收益波动率构造 fast/slow 指标。当 fast 高于 slow 时做多，低于 slow 时做空，并保留连续亏损冷却机制。每个参数组合对应一列收益；收益使用上一根 bar 的仓位计算，避免未来函数。

### IS/OOS split 设计与 PBO 计算

收益矩阵被切为 8 个连续 blocks，每次选择 4 个 blocks 为样本内，剩余 4 个为样本外。样本内按 Sharpe ratio 选出最优参数，并记录其样本外 Sharpe、样本外百分位排名和 rank logit。PBO 为样本外排名低于 0.5 的 split 占比。

### T/TL 结果

| contract | sample_start | sample_end | rows | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | best_overall_strategy | best_oos_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 28352 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | nf_0031_ns_0107 | nf_0031_ns_0107 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 28451 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | nf_0047_ns_1630 | nf_0047_ns_1630 |

### 图表

#### T

![T PBO histogram](figures/pbo_histogram_T.png)

![T Rank logit](figures/rank_logit_T.png)

![T IS vs OOS](figures/is_vs_oos_T.png)

![T OOS rank distribution](figures/oos_rank_distribution_T.png)

#### TL

![TL PBO histogram](figures/pbo_histogram_TL.png)

![TL Rank logit](figures/rank_logit_TL.png)

![TL IS vs OOS](figures/is_vs_oos_TL.png)

![TL OOS rank distribution](figures/oos_rank_distribution_TL.png)

### 局限性

结果未显式纳入交易成本、滑点、合约换月细节和实盘流动性冲击。CSCV 衡量的是参数搜索中的样本内过拟合风险，不保证未来收益。

### References

- Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). *The Probability of Backtest Overfitting*. Journal of Computational Finance.
- Bailey, D. H., & López de Prado, M. (2012/2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.

### Disclaimer

本项目用于个人研究与工程化复现，不代表原作者或任何机构观点，不构成投资建议。

## English Report

### CSCV Method

CSCV means Combinatorially Symmetric Cross-Validation. This report applies CSCV/PBO to 5-minute CGB futures strategy parameter validation, following the backtest-overfitting literature by Bailey, Borwein, López de Prado and Zhu.

### Data

The pipeline standardizes Excel inputs into `datetime/open/high/low/close/volume/open_interest`, auto-detects sheet/header layout, removes duplicated timestamps, and sorts observations chronologically. The default evaluation sample starts from `2024-01-01`.

### Strategy Return Matrix

The original bull/bear indicator strategy is retained. Fast and slow indicators are built from turnover and return volatility; the strategy goes long when fast exceeds slow and short otherwise, with the original consecutive-loss cooldown control. Positions are shifted by one bar before return calculation.

### IS/OOS Splits and PBO

The return matrix is split into 8 chronological blocks. Each CSCV split uses 4 blocks as in-sample and 4 blocks as out-of-sample. The in-sample winner is selected by Sharpe ratio and then ranked out-of-sample. PBO is the fraction of splits where the selected strategy ranks in the worse half out-of-sample.

### T/TL Results

| contract | sample_start | sample_end | rows | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | best_overall_strategy | best_oos_strategy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 28352 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | nf_0031_ns_0107 | nf_0031_ns_0107 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 28451 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | nf_0047_ns_1630 | nf_0047_ns_1630 |

### Figures

#### T

![T PBO histogram](figures/pbo_histogram_T.png)

![T Rank logit](figures/rank_logit_T.png)

![T IS vs OOS](figures/is_vs_oos_T.png)

![T OOS rank distribution](figures/oos_rank_distribution_T.png)

#### TL

![TL PBO histogram](figures/pbo_histogram_TL.png)

![TL Rank logit](figures/rank_logit_TL.png)

![TL IS vs OOS](figures/is_vs_oos_TL.png)

![TL OOS rank distribution](figures/oos_rank_distribution_TL.png)

### Limitations and Disclaimer

The results do not fully model transaction costs, slippage, contract roll mechanics, or live execution constraints. CSCV measures overfitting risk in the research process; it does not guarantee future profitability.

# 国债期货 CSCV 回测过拟合检验框架 | CSCV Backtest Overfitting Detection for CGB Futures

<p align="center">
  <a href="#zh"><img src="https://img.shields.io/badge/LANGUAGE-%E4%B8%AD%E6%96%87-E84D3D?style=for-the-badge&labelColor=3B3F47" alt="LANGUAGE 中文"></a>
  <a href="#en"><img src="https://img.shields.io/badge/LANGUAGE-ENGLISH-2F73C9?style=for-the-badge&labelColor=3B3F47" alt="LANGUAGE ENGLISH"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Asset-CGB%20Futures-F2C94C?style=for-the-badge" alt="CGB Futures">
  <img src="https://img.shields.io/badge/Validation-CSCV%20%2F%20PBO-7AC943?style=for-the-badge" alt="CSCV / PBO">
</p>

<a id="zh"></a>

## 简体中文

当前语言：中文 | [Switch to English](#en)

---

### 项目简介

本项目是一个基于组合对称交叉验证（CSCV, Combinatorially Symmetric Cross-Validation）的国债期货策略稳健性检验框架，用于识别回测过拟合、参数选择偏误和样本外失效风险。当前支持 10 年国债期货 T 和 30 年国债期货 TL 的 5 分钟数据。

默认回测与 CSCV 评估样本从 `2024-01-01` 开始。更早数据仅可作为滚动指标预热历史，不进入收益矩阵、CSCV 评估或结果报告。

### CSCV 方法原理

CSCV 常用于检测金融策略回测过拟合风险，典型来源是 Bailey, Borwein, López de Prado and Zhu 关于 *The Probability of Backtest Overfitting* 的研究。核心思想是将完整样本划分为若干个连续 blocks，枚举对称的 in-sample / out-of-sample 组合；每个 split 中先在样本内选出表现最好的策略或参数，再观察该策略在样本外的排名。如果样本内最优策略在样本外经常表现很差，则说明存在严重回测过拟合风险。


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


### 为什么量化策略需要过拟合检验

多参数搜索会放大偶然高收益策略被选中的概率。CSCV/PBO 不只看最优参数的历史收益，而是检验“样本内胜出者”在样本外是否系统性退化，更适合评估参数集合的整体稳健性。

### 数据与策略收益矩阵

输入数据字段会标准化为 `datetime/open/high/low/close/volume/open_interest`。策略收益矩阵的行为 5 分钟时间戳，列为参数组合。信号在 bar `t` 形成，收益使用 `position.shift(1)` 对应 bar `t+1`，避免未来函数。

### CSCV 计算流程

1. 构建全部参数组合的策略收益矩阵。
2. 将收益矩阵切分为 `n_splits=8` 个连续 blocks。
3. 枚举一半 blocks 作为样本内，另一半作为样本外。
4. 在样本内按 Sharpe ratio 选择最优策略。
5. 记录该策略在样本外的 Sharpe、百分位排名、rank logit 和过拟合事件。
6. 汇总 PBO、样本内/样本外表现与稳健性指标。

### PBO 与 rank logit 解释

PBO = Probability of Backtest Overfitting，衡量样本内选出的最优策略在样本外落入较差排名区间的概率。Rank logit 对样本外 rank 进行 logit 变换，用于观察样本内最优策略在样本外是否系统性退化。

### T / TL 检验结果

| contract | sample_start | sample_end | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | degradation_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | -0.1473 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | 0.0341 |

### 图表展示

#### T

![T PBO histogram](results/figures/pbo_histogram_T.png)

![T Rank logit](results/figures/rank_logit_T.png)

![T IS vs OOS](results/figures/is_vs_oos_T.png)

![T OOS rank distribution](results/figures/oos_rank_distribution_T.png)

#### TL

![TL PBO histogram](results/figures/pbo_histogram_TL.png)

![TL Rank logit](results/figures/rank_logit_TL.png)

![TL IS vs OOS](results/figures/is_vs_oos_TL.png)

![TL OOS rank distribution](results/figures/oos_rank_distribution_TL.png)

### 快速开始

```bash
pip install -r requirements.txt
```

本仓库已在 `data/raw/` 中包含用于复现实证结果的两个原始 Excel：

- `10年国债期货_5min_3年.xlsx`
- `30年国债期货_5min_2年.xlsx`

如果文件仍在仓库根目录，pipeline 也会临时读取；推荐以 `data/raw/` 为规范数据目录。

### 运行命令

```bash
python scripts/run_cscv_pipeline.py --contract T --n-splits 8
python scripts/run_cscv_pipeline.py --contract TL --n-splits 8
python scripts/run_cscv_pipeline.py --contract ALL --n-splits 8
python cscv_t_strategy.py --contract ALL --n-splits 8
```

### 输出文件

- `results/tables/parameter_grid_T.csv`, `results/tables/parameter_grid_TL.csv`
- `results/tables/strategy_returns_T.csv`, `results/tables/strategy_returns_TL.csv`
- `results/tables/cscv_splits_T.csv`, `results/tables/cscv_splits_TL.csv`
- `results/tables/cscv_summary_T.csv`, `results/tables/cscv_summary_TL.csv`, `results/tables/cscv_summary_all.csv`
- `results/figures/*.png`
- `results/report.md`

完整策略收益矩阵 CSV 可能非常大，属于可复现运行产物，默认在本地生成但不纳入普通 Git 提交。

### 方法论来源

- Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). *The Probability of Backtest Overfitting*. Journal of Computational Finance.
- Bailey, D. H., & López de Prado, M. (2012/2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- 华泰证券. (2019-06-17). *华泰人工智能系列之二十二：基于CSCV框架的回测过拟合概率*.
- 华泰证券. (2019-09-27). *华泰金工量化择时系列：波动率与换手率构造牛熊指标*.

本项目参考 CSCV 和 PBO 的经典研究，用于检测量化策略在参数搜索和多策略筛选过程中的样本内过拟合风险。代码实现是个人研究与工程化复现，不代表原作者或任何机构观点。

### 许可证

本项目采用 MIT License，详见 `LICENSE`。

### 局限性与免责声明

本项目仅用于量化研究和工程复现。策略结果受数据质量、交易成本、滑点、合约换月、市场制度和参数空间影响，不构成投资建议。

<a id="en"></a>

## English

Current language: English | [Switch to Chinese](#zh)

---

### Project Overview

This repository provides a CSCV-based validation framework for detecting backtest overfitting and evaluating the robustness of Chinese Government Bond Futures trading strategies. It supports 10-year CGB futures T and 30-year CGB futures TL on 5-minute bars.

The default backtest and CSCV evaluation sample starts from `2024-01-01`. Earlier observations may be used only as rolling-indicator warm-up history.

### CSCV Methodology

CSCV stands for Combinatorially Symmetric Cross-Validation. It is commonly used to detect financial strategy backtest overfitting, with a canonical reference in Bailey, Borwein, López de Prado and Zhu's research on *The Probability of Backtest Overfitting*. The method partitions the full sample into chronological blocks, enumerates symmetric in-sample/out-of-sample combinations, selects the best strategy in-sample, and evaluates where that selected strategy ranks out-of-sample.


Partition the full sample into $S$ chronological subsamples:

$$
D = \{D_1, D_2, \ldots, D_S\}
$$

For each split, choose half of the subsamples as in-sample:

$$
D_{IS}^{(k)} \subset D, \quad D_{OOS}^{(k)} = D \setminus D_{IS}^{(k)}
$$

Select the best strategy in-sample:

$$
j^* = \arg\max_j Sharpe_{IS}^{(k)}(j)
$$

Observe that selected strategy's out-of-sample percentile rank:

$$
Rank_{OOS}^{(k)}(j^*)
$$

In this project, rank direction is $0 =$ worst and $1 =$ best. If the selected strategy falls into the worse half out-of-sample, it is counted as an overfitting event:

$$
I_k = \mathbb{1}(Rank_{OOS}^{(k)} < 0.5)
$$

PBO is defined as:

$$
PBO = \frac{1}{K} \sum_{k=1}^{K} I_k
$$

Rank logit is:

$$
\log\left(\frac{Rank_{OOS}^{(k)}}{1 - Rank_{OOS}^{(k)}}\right)
$$


### Why Backtest Overfitting Detection Matters

Parameter searches can select strategies that won in-sample by chance. CSCV/PBO evaluates whether in-sample winners remain competitive out-of-sample across many symmetric splits.

### Data and Strategy Return Matrix

The loader standardizes fields to `datetime/open/high/low/close/volume/open_interest`. The strategy return matrix has timestamps as rows and parameter combinations as columns. Signals are formed at bar `t`; returns use `position.shift(1)` and are earned on bar `t+1`.

### CSCV Workflow

1. Build the strategy return matrix for all parameter combinations.
2. Split the matrix into `n_splits=8` chronological blocks.
3. Enumerate balanced IS/OOS block combinations.
4. Select the IS-best strategy by Sharpe ratio.
5. Record OOS Sharpe, OOS percentile rank, rank logit, and overfit event.
6. Aggregate PBO and robustness statistics.

### PBO and Rank Logit

PBO is the Probability of Backtest Overfitting. It measures how often the strategy selected as in-sample best falls into the worse half of the out-of-sample ranking distribution. Rank logit transforms the OOS rank percentile to diagnose systematic degradation.

### T / TL Validation Results

| contract | sample_start | sample_end | n_strategies | n_combinations | PBO | median_oos_rank | mean_is_performance | mean_oos_performance | degradation_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2024-01-02 09:35:00 | 2026-04-24 15:15:00 | 9123 | 70 | 0.6429 | 0.3971 | 2.7149 | -0.3999 | -0.1473 |
| TL | 2024-01-02 09:35:00 | 2026-04-25 11:30:00 | 9123 | 70 | 0.5000 | 0.5106 | 2.7003 | 0.0920 | 0.0341 |

### Figures

#### T

![T PBO histogram](results/figures/pbo_histogram_T.png)

![T Rank logit](results/figures/rank_logit_T.png)

![T IS vs OOS](results/figures/is_vs_oos_T.png)

![T OOS rank distribution](results/figures/oos_rank_distribution_T.png)

#### TL

![TL PBO histogram](results/figures/pbo_histogram_TL.png)

![TL Rank logit](results/figures/rank_logit_TL.png)

![TL IS vs OOS](results/figures/is_vs_oos_TL.png)

![TL OOS rank distribution](results/figures/oos_rank_distribution_TL.png)

### Quick Start

```bash
pip install -r requirements.txt
```

The two raw Excel files used for the published results are included under `data/raw/`; root-level fallback is also supported for local runs.

### Example Commands

```bash
python scripts/run_cscv_pipeline.py --contract T --n-splits 8
python scripts/run_cscv_pipeline.py --contract TL --n-splits 8
python scripts/run_cscv_pipeline.py --contract ALL --n-splits 8
python cscv_t_strategy.py --contract ALL --n-splits 8
```

### Output Files

Outputs are written under `results/tables/`, `results/figures/`, and `results/report.md`. Full strategy return matrices can be very large; they are reproducible local artifacts and are excluded from normal Git commits.

### References

- Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014). *The Probability of Backtest Overfitting*. Journal of Computational Finance.
- Bailey, D. H., & López de Prado, M. (2012/2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Huatai Securities. (2019-06-17). *Huatai Artificial Intelligence Series No. 22: Probability of Backtest Overfitting Based on the CSCV Framework*. Chinese research report.
- Huatai Securities. (2019-09-27). *Huatai Quantitative Market Timing Series: Constructing Bull-Bear Indicators with Volatility and Turnover*. Chinese research report.

### License

This project is released under the MIT License. See `LICENSE`.

### Limitations and Disclaimer

This project is for quantitative research and engineering reproduction only. Results depend on data quality, trading costs, slippage, contract rolling assumptions, market rules, and the parameter search space. Nothing here is investment advice.

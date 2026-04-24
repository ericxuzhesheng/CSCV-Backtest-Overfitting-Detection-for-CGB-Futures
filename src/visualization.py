from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_pbo_histogram(splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(splits["oos_rank_pct"], bins=20, color="#4C78A8", edgecolor="white")
    ax.axvline(0.5, color="#D62728", linestyle="--", linewidth=1.5, label="Overfit threshold")
    ax.set_title(f"{contract} PBO Histogram")
    ax.set_xlabel("OOS percentile rank (0=worst, 1=best)")
    ax.set_ylabel("Split count")
    ax.legend(frameon=False)
    return _save(fig, out_dir / f"pbo_histogram_{contract}.png")


def plot_rank_logit(splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(splits["split_id"], splits["rank_logit"], marker="o", linewidth=1.2, color="#2CA02C")
    ax.axhline(0.0, color="#333333", linestyle="--", linewidth=1.0)
    ax.set_title(f"{contract} Rank Logit by CSCV Split")
    ax.set_xlabel("Split ID")
    ax.set_ylabel("Rank logit")
    ax.grid(alpha=0.25)
    return _save(fig, out_dir / f"rank_logit_{contract}.png")


def plot_is_vs_oos(splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(splits["is_performance"], splits["oos_performance"], alpha=0.75, color="#9467BD")
    ax.axhline(0.0, color="#666666", linewidth=0.8)
    ax.axvline(0.0, color="#666666", linewidth=0.8)
    ax.set_title(f"{contract} IS vs OOS Performance")
    ax.set_xlabel("IS selected strategy Sharpe")
    ax.set_ylabel("OOS selected strategy Sharpe")
    ax.grid(alpha=0.25)
    return _save(fig, out_dir / f"is_vs_oos_{contract}.png")


def plot_oos_rank_distribution(splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(splits["oos_rank_pct"], bins=10, color="#F58518", edgecolor="white")
    ax.set_title(f"{contract} OOS Rank Distribution")
    ax.set_xlabel("OOS percentile rank (0=worst, 1=best)")
    ax.set_ylabel("Split count")
    return _save(fig, out_dir / f"oos_rank_distribution_{contract}.png")


def generate_all_figures(splits: pd.DataFrame, contract: str, out_dir: Path) -> list[Path]:
    return [
        plot_pbo_histogram(splits, contract, out_dir),
        plot_rank_logit(splits, contract, out_dir),
        plot_is_vs_oos(splits, contract, out_dir),
        plot_oos_rank_distribution(splits, contract, out_dir),
    ]


def plot_selection_score_vs_oos(dynamic_splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        dynamic_splits["selection_score"],
        dynamic_splits["selected_oos_score"],
        alpha=0.75,
        color="#1F77B4",
    )
    ax.axhline(0.0, color="#666666", linewidth=0.8)
    ax.axvline(0.0, color="#666666", linewidth=0.8)
    ax.set_title(f"{contract} Selection Score vs OOS Performance")
    ax.set_xlabel("Training selection score")
    ax.set_ylabel("Selected strategy OOS score")
    ax.grid(alpha=0.25)
    return _save(fig, out_dir / f"selection_score_vs_oos_{contract}.png")


def plot_selected_oos_rank(dynamic_splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(dynamic_splits["selected_oos_percentile"], bins=10, color="#59A14F", edgecolor="white")
    ax.axvline(0.5, color="#D62728", linestyle="--", linewidth=1.5, label="Failure threshold")
    ax.set_title(f"{contract} Selected Strategy OOS Percentile")
    ax.set_xlabel("Selected OOS percentile (0=worst, 1=best)")
    ax.set_ylabel("Window count")
    ax.legend(frameon=False)
    return _save(fig, out_dir / f"selected_oos_rank_{contract}.png")


def plot_parameter_stability(dynamic_splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    counts = dynamic_splits["selected_strategy"].value_counts().head(10).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(counts.index, counts.values, color="#9C755F")
    ax.set_title(f"{contract} Parameter Stability")
    ax.set_xlabel("Selected window count")
    ax.set_ylabel("Strategy")
    return _save(fig, out_dir / f"parameter_stability_{contract}.png")


def plot_dynamic_failure_rate(dynamic_splits: pd.DataFrame, contract: str, out_dir: Path) -> Path:
    counts = dynamic_splits["failure_flag"].value_counts().reindex([0, 1], fill_value=0)
    labels = ["Success", "Failure"]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(labels, counts.values, color=["#4E79A7", "#E15759"])
    ax.set_title(f"{contract} Dynamic Selection Failure Rate")
    ax.set_xlabel("Window outcome")
    ax.set_ylabel("Window count")
    return _save(fig, out_dir / f"dynamic_failure_rate_{contract}.png")


def generate_dynamic_audit_figures(dynamic_splits: pd.DataFrame, contract: str, out_dir: Path) -> list[Path]:
    return [
        plot_selection_score_vs_oos(dynamic_splits, contract, out_dir),
        plot_selected_oos_rank(dynamic_splits, contract, out_dir),
        plot_parameter_stability(dynamic_splits, contract, out_dir),
        plot_dynamic_failure_rate(dynamic_splits, contract, out_dir),
    ]

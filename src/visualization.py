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

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import FIGURES_DIR, RESULTS_DIR, TABLES_DIR


REQUIRED_TABLES = [
    "parameter_grid_T.csv",
    "parameter_grid_TL.csv",
    "cscv_splits_T.csv",
    "cscv_splits_TL.csv",
    "cscv_summary_T.csv",
    "cscv_summary_TL.csv",
    "cscv_summary_all.csv",
]

REQUIRED_FIGURES = [
    "pbo_histogram_T.png",
    "rank_logit_T.png",
    "is_vs_oos_T.png",
    "oos_rank_distribution_T.png",
    "pbo_histogram_TL.png",
    "rank_logit_TL.png",
    "is_vs_oos_TL.png",
    "oos_rank_distribution_TL.png",
]


def main() -> None:
    missing = []
    for name in REQUIRED_TABLES:
        if not (TABLES_DIR / name).exists():
            missing.append(str(TABLES_DIR / name))
    for name in REQUIRED_FIGURES:
        if not (FIGURES_DIR / name).exists():
            missing.append(str(FIGURES_DIR / name))
    if not (RESULTS_DIR / "report.md").exists():
        missing.append(str(RESULTS_DIR / "report.md"))
    if not (ROOT / "README.md").exists():
        missing.append(str(ROOT / "README.md"))

    if missing:
        print("Missing required outputs:")
        for path in missing:
            print(f"  - {path}")
        raise SystemExit(1)

    print("Validation passed: required CSCV tables, figures, README, and report exist.")


if __name__ == "__main__":
    main()

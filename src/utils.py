from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
REPORT_DIR = PROJECT_ROOT / "report"
PERIODS_PER_YEAR = 252 * 54
DEFAULT_START_DATE = "2024-01-01"


@dataclass(frozen=True)
class ContractConfig:
    code: str
    display_name: str
    file_name: str


CONTRACTS: Dict[str, ContractConfig] = {
    "T": ContractConfig(
        code="T",
        display_name="10Y CGB Futures",
        file_name="10年国债期货_5min_3年.xlsx",
    ),
    "TL": ContractConfig(
        code="TL",
        display_name="30Y CGB Futures",
        file_name="30年国债期货_5min_2年.xlsx",
    ),
}


def selected_contracts(contract: str) -> List[str]:
    key = contract.upper()
    if key == "ALL":
        return ["T", "TL"]
    if key not in CONTRACTS:
        raise ValueError(f"Unsupported contract: {contract}. Use T, TL, or ALL.")
    return [key]


def ensure_output_dirs() -> None:
    for path in [DATA_RAW_DIR, TABLES_DIR, FIGURES_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def find_contract_file(contract: str) -> Path:
    cfg = CONTRACTS[contract]
    candidates = [
        DATA_RAW_DIR / cfg.file_name,
        PROJECT_ROOT / cfg.file_name,
    ]
    for path in candidates:
        if path.exists():
            return path
    searched = ", ".join(str(p.relative_to(PROJECT_ROOT)) for p in candidates)
    raise FileNotFoundError(
        f"Missing data file for {contract}: {cfg.file_name}. "
        f"Place it in data/raw/. Searched: {searched}"
    )


def make_strategy_id(n_fast: int, n_slow: int) -> str:
    return f"nf_{int(n_fast):04d}_ns_{int(n_slow):04d}"


def parse_strategy_id(strategy_id: str) -> Dict[str, int]:
    parts = strategy_id.split("_")
    return {"N_fast": int(parts[1]), "N_slow": int(parts[3])}


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def existing_figure_links(contract: str) -> Iterable[tuple[str, str]]:
    figure_names = [
        ("PBO histogram", f"pbo_histogram_{contract}.png"),
        ("Rank logit", f"rank_logit_{contract}.png"),
        ("IS vs OOS", f"is_vs_oos_{contract}.png"),
        ("OOS rank distribution", f"oos_rank_distribution_{contract}.png"),
        ("Selection score vs OOS", f"selection_score_vs_oos_{contract}.png"),
        ("Selected OOS rank", f"selected_oos_rank_{contract}.png"),
        ("Parameter stability", f"parameter_stability_{contract}.png"),
        ("Dynamic failure rate", f"dynamic_failure_rate_{contract}.png"),
    ]
    for label, name in figure_names:
        if (FIGURES_DIR / name).exists():
            yield label, f"figures/{name}"

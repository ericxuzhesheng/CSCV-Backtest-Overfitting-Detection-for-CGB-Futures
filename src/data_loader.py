from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from .utils import find_contract_file


FIELD_ALIASES: Dict[str, Iterable[str]] = {
    "datetime": ["datetime", "time", "date", "日期", "时间", "交易时间", "时间戳"],
    "open": ["open", "开盘", "开盘价"],
    "high": ["high", "最高", "最高价"],
    "low": ["low", "最低", "最低价"],
    "close": ["close", "收盘", "收盘价", "最新价"],
    "volume": ["volume", "vol", "成交量", "交易量"],
    "open_interest": ["open_interest", "openinterest", "oi", "持仓量", "持仓"],
}


def _norm(value: object) -> str:
    return "".join(str(value).strip().lower().split())


def _standardize_columns(columns: Iterable[object]) -> Dict[object, str]:
    mapping: Dict[object, str] = {}
    for col in columns:
        normed = _norm(col)
        for target, aliases in FIELD_ALIASES.items():
            if normed in {_norm(alias) for alias in aliases}:
                mapping[col] = target
                break
    return mapping


def _find_header_row(raw: pd.DataFrame, search_rows: int = 50) -> Optional[int]:
    required = {"time", "open", "high", "low", "close"}
    n = min(search_rows, len(raw))
    for i in range(n):
        row = {_norm(value) for value in raw.iloc[i].tolist()}
        if required.issubset(row) or {"datetime", "open", "high", "low", "close"}.issubset(row):
            return i
        if {"时间", "开盘", "最高", "最低", "收盘"}.issubset(row):
            return i
    return None


def _load_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    if raw.empty:
        raise ValueError(f"Sheet is empty: {path.name}::{sheet_name}")

    header_row = _find_header_row(raw)
    if header_row is None:
        data = pd.read_excel(path, sheet_name=sheet_name)
    else:
        header = ["" if pd.isna(x) else str(x).strip() for x in raw.iloc[header_row].tolist()]
        data = raw.iloc[header_row + 1 :].copy()
        data.columns = header

    data = data.dropna(axis=1, how="all")
    data = data.rename(columns=_standardize_columns(data.columns))
    required = {"datetime", "close", "volume"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(
            f"Missing required columns {sorted(missing)} in {path.name}::{sheet_name}; "
            f"columns={list(data.columns)}"
        )

    data["datetime"] = pd.to_datetime(data["datetime"], errors="coerce")
    data = data.dropna(subset=["datetime"]).copy()
    for col in ["open", "high", "low", "close", "volume", "open_interest"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["close"])
    data["volume"] = data["volume"].fillna(0.0)
    if "open_interest" in data.columns:
        data["open_interest"] = data["open_interest"].replace(0, pd.NA).ffill()

    ordered = [c for c in ["open", "high", "low", "close", "volume", "open_interest"] if c in data.columns]
    out = data.set_index("datetime")[ordered]
    out = out[~out.index.duplicated(keep="last")].sort_index()
    if out.empty:
        raise ValueError(f"No valid rows after preprocessing: {path.name}::{sheet_name}")
    return out


def load_price_data(path: Path) -> pd.DataFrame:
    excel = pd.ExcelFile(path)
    errors = []
    for sheet in excel.sheet_names:
        try:
            return _load_sheet(path, sheet)
        except Exception as exc:  # pragma: no cover - included in error message.
            errors.append(f"{sheet}: {exc}")
    raise ValueError(f"Could not load any sheet from {path}. Errors: {' | '.join(errors)}")


def load_contract_data(contract: str) -> pd.DataFrame:
    return load_price_data(find_contract_file(contract))

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_external_audit import load_matrix
from src.cscv import run_cscv
from src.dynamic_selection_audit import run_dynamic_selection_audit


def test_generic_ids_and_daily_annualization():
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(rng.normal(.0002, .01, (160, 3)), columns=["qrs_a", "qrs_b", "vpin_a"], index=pd.bdate_range("2024-01-01", periods=160))
    daily = run_cscv(frame, periods_per_year=252)
    intraday = run_cscv(frame)
    assert daily["summary"]["PBO"] == intraday["summary"]["PBO"]
    np.testing.assert_allclose(daily["splits"].is_performance * np.sqrt(54), intraday["splits"].is_performance)
    audit = run_dynamic_selection_audit(frame, 80, 20, 20, periods_per_year=252)
    splits = audit["splits"]
    assert (pd.to_datetime(splits.train_end) < pd.to_datetime(splits.test_start)).all()
    assert (pd.to_datetime(splits.test_end.iloc[:-1]).to_numpy() < pd.to_datetime(splits.test_start.iloc[1:]).to_numpy()).all()


def test_external_missing_returns_are_rejected(tmp_path):
    frame = pd.DataFrame({"a": [.01, np.nan, -.01], "b": [.02, -.01, .01]}, index=pd.bdate_range("2024-01-01", periods=3))
    path = tmp_path / "matrix.csv"
    frame.to_csv(path)
    with pytest.raises(ValueError, match="missing is not zero"):
        load_matrix(path)


def test_duplicate_csv_headers_are_rejected_before_pandas_renames_them(tmp_path):
    path = tmp_path / "duplicate.csv"
    path.write_text("date,a,a\n2024-01-01,.01,.02\n2024-01-02,.02,.01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate candidate"):
        load_matrix(path)

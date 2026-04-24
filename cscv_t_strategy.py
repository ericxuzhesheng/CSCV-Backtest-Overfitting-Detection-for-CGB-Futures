from __future__ import annotations

"""Compatibility CLI wrapper for the CSCV CGB futures framework.

The original bull/bear indicator strategy logic has been refactored into
``src.strategy_matrix`` and the CSCV implementation into ``src.cscv``.
"""

from scripts.run_cscv_pipeline import main


if __name__ == "__main__":
    main()

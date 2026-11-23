import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from data.cache import get_connection, save_ohlcv
from data.reconcile import rebuild_universe


class RebuildCacheFreshnessTests(unittest.TestCase):
    def test_stale_fetch_does_not_remove_newer_cached_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "cache.db")
            with patch("data.cache.DB_PATH", db_path):
                conn = get_connection()
                try:
                    newer = pd.DataFrame(
                        {
                            "Open": [10.0],
                            "High": [11.0],
                            "Low": [9.0],
                            "Close": [10.5],
                            "Volume": [100],
                        },
                        index=pd.to_datetime(["2026-11-23"]),
                    )
                    save_ohlcv(conn, "TCS", newer)
                finally:
                    conn.close()

                fetched = pd.DataFrame(
                    {
                        "Open": [10.0] * 30,
                        "High": [11.0] * 30,
                        "Low": [9.0] * 30,
                        "Close": [10.5] * 30,
                        "Volume": [100] * 30,
                    },
                    index=pd.date_range(end="2026-11-20", periods=30, freq="D"),
                )
                qc = {
                    "status": "SINGLE-SOURCE",
                    "n_rows": len(fetched),
                    "last_date": "2026-11-20",
                    "sources": "yfinance",
                    "n_common": 0,
                    "agree_pct": None,
                    "ticks_repaired": 0,
                }

                with (
                    patch("data.fetcher.fetch_index"),
                    patch("data.reconcile.fetch_reconciled", return_value=(fetched, qc)),
                ):
                    rebuild_universe(["TCS"], "NIFTY 50", max_workers=1)

                conn = get_connection()
                try:
                    latest = conn.execute(
                        "SELECT MAX(date) FROM ohlcv WHERE symbol='TCS'"
                    ).fetchone()[0]
                finally:
                    conn.close()

                self.assertEqual(latest, "2026-11-23")


if __name__ == "__main__":
    unittest.main()

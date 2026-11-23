import sys
import unittest
from datetime import date
from types import ModuleType
from unittest.mock import Mock, patch

import pandas as pd

from data.fetcher import _fetch_yfinance


class YahooFinanceDateRangeTests(unittest.TestCase):
    def test_includes_requested_end_date(self):
        history = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [105.0],
                "Low": [99.0],
                "Close": [103.0],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2026-11-23"]),
        )
        yfinance = ModuleType("yfinance")
        yfinance.download = Mock(return_value=history)

        with patch.dict(sys.modules, {"yfinance": yfinance}):
            result = _fetch_yfinance(
                "TCS", date(2026, 11, 1), date(2026, 11, 23)
            )

        self.assertEqual(result.index[-1].date(), date(2026, 11, 23))
        self.assertEqual(yfinance.download.call_args.kwargs["end"], date(2026, 11, 24))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import pandas as pd

from test_stock import _yahoo_ticker, lookup_stock_name


class YahooTickerTests(unittest.TestCase):
    def test_adds_nse_suffix(self):
        self.assertEqual(_yahoo_ticker("reliance"), "RELIANCE.NS")

    def test_does_not_duplicate_existing_suffix(self):
        self.assertEqual(_yahoo_ticker("tcs.ns"), "TCS.NS")


class LookupStockNameTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame(
            [
                {"Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 103.0},
                {"Open": 104.0, "High": 109.0, "Low": 102.0, "Close": 108.0},
            ],
            index=pd.to_datetime(["2026-10-29", "2026-10-30"]),
        )

    @patch("test_stock.yf.Ticker")
    def test_uses_long_name_from_yfinance(self, ticker):
        ticker.return_value.get_info.return_value = {
            "longName": "Reliance Industries Limited",
            "shortName": "RELIANCE",
        }
        ticker.return_value.history.return_value = self.history

        result = lookup_stock_name("RELIANCE")

        ticker.assert_called_once_with("RELIANCE.NS")
        self.assertEqual(result["Stock_Name"], "Reliance Industries Limited")
        self.assertEqual(result["Status"], "OK")
        ticker.return_value.history.assert_called_once_with(
            period="5d", interval="1d", auto_adjust=False
        )
        self.assertEqual(result["OHLC_Date"], "2026-10-30")
        self.assertEqual(
            [result["Open"], result["High"], result["Low"], result["Close"]],
            [104.0, 109.0, 102.0, 108.0],
        )
        self.assertEqual(result["OHLC_Status"], "OK")

    @patch("test_stock.yf.Ticker")
    def test_uses_short_name_when_long_name_is_missing(self, ticker):
        ticker.return_value.get_info.return_value = {"shortName": "Tata Consultancy Services"}
        ticker.return_value.history.return_value = self.history

        result = lookup_stock_name("TCS.NS")

        self.assertEqual(result["Stock_Name"], "Tata Consultancy Services")
        self.assertEqual(result["Status"], "OK")

    @patch("test_stock.yf.Ticker")
    def test_returns_explicit_error_when_yfinance_fails(self, ticker):
        ticker.return_value.get_info.side_effect = RuntimeError("network unavailable")
        ticker.return_value.history.return_value = self.history

        result = lookup_stock_name("RELIANCE")

        self.assertEqual(result["Status"], "ERROR")
        self.assertIn("network unavailable", result["Error"])

    @patch("test_stock.yf.Ticker")
    def test_reports_empty_ohlc_data(self, ticker):
        ticker.return_value.get_info.return_value = {"longName": "Reliance Industries Limited"}
        ticker.return_value.history.return_value = pd.DataFrame()

        result = lookup_stock_name("RELIANCE")

        self.assertEqual(result["Status"], "OK")
        self.assertEqual(result["OHLC_Status"], "NO_DATA")
        self.assertIn("no daily price history", result["Error"])

    @patch("test_stock.yf.Ticker")
    def test_reports_ohlc_failure_separately_from_name(self, ticker):
        ticker.return_value.get_info.return_value = {"longName": "Reliance Industries Limited"}
        ticker.return_value.history.side_effect = RuntimeError("quote unavailable")

        result = lookup_stock_name("RELIANCE")

        self.assertEqual(result["Status"], "OK")
        self.assertEqual(result["OHLC_Status"], "ERROR")
        self.assertIn("quote unavailable", result["Error"])


if __name__ == "__main__":
    unittest.main()

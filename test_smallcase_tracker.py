import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from portfolio_smallcase_tracker import (
    BUY_SELL_COLUMNS,
    SUMMARY_COLUMNS,
    _build_buy_sell_ledger,
    _calculate_cagr,
    _enrich_monthly_summary,
    _run_rebalance,
    monthly_rebalance_dates,
    parse_args,
)

class TrackerArgumentTests(unittest.TestCase):
    def test_cli_default_start_date_matches_tracker_default(self):
        with patch("sys.argv", ["portfolio_smallcase_tracker.py"]):
            args = parse_args()
        self.assertEqual(args.start_date, date(2026, 4, 25))


class PortfolioPerformanceTests(unittest.TestCase):
    def test_cagr_uses_actual_elapsed_days(self):
        cagr = _calculate_cagr(
            100_000,
            110_000,
            "2025-01-01",
            "2026-01-01",
        )
        self.assertAlmostEqual(cagr, 10.0, places=1)

    def test_summary_includes_monthly_gain_and_cagr(self):
        summary = pd.DataFrame([
            {
                "Execution_Date": "2026-04-25",
                "Opening_Portfolio_Value": 1_000_000,
                "Closing_Portfolio_Value": 1_000_000,
                "Monthly_Profit_Loss": 0,
            },
            {
                "Execution_Date": "2026-05-25",
                "Opening_Portfolio_Value": 1_000_000,
                "Closing_Portfolio_Value": 1_050_000,
                "Monthly_Profit_Loss": 50_000,
            },
        ])

        enriched = _enrich_monthly_summary(summary, 1_000_000)

        self.assertEqual(list(enriched.columns), SUMMARY_COLUMNS)
        self.assertAlmostEqual(enriched.loc[1, "Monthly_Gain_%"], 5.0)
        expected_cagr = _calculate_cagr(
            1_000_000, 1_050_000, "2026-04-25", "2026-05-25"
        )
        self.assertAlmostEqual(enriched.loc[1, "CAGR_%"], expected_cagr)


class MonthlyRebalanceDatesTests(unittest.TestCase):
    def test_dates_are_scheduled_on_the_25th_and_limited_to_as_of_date(self):
        dates = monthly_rebalance_dates(
            date(2026, 9, 25), date(2026, 11, 24)
        )
        self.assertEqual(dates, [date(2026, 9, 25), date(2026, 10, 25)])


class PortfolioRebalanceTests(unittest.TestCase):
    def test_sells_only_below_60_and_buys_highest_ranked_unowned_from_proceeds(self):
        positions = {
            "KEEP": {
                "Quantity": 10,
                "Entry_Date": "2026-09-25",
                "Entry_Price": 10.0,
                "Cost_Basis": 100.0,
                "Last_Price": 10.0,
                "Last_Price_Date": "2026-10-23",
                "Rank": 60,
            },
            "EXIT": {
                "Quantity": 10,
                "Entry_Date": "2026-09-25",
                "Entry_Price": 8.0,
                "Cost_Basis": 80.0,
                "Last_Price": 8.0,
                "Last_Price_Date": "2026-10-23",
                "Rank": 20,
            },
        }
        prices = {
            "KEEP": pd.Series([10.0], index=pd.to_datetime(["2026-10-23"])),
            "EXIT": pd.Series([10.0], index=pd.to_datetime(["2026-10-23"])),
            "BEST": pd.Series([20.0], index=pd.to_datetime(["2026-10-23"])),
            "NEXT": pd.Series([25.0], index=pd.to_datetime(["2026-10-23"])),
        }
        ranked = [
            {"Symbol": "BEST", "Rank": 1, "Price": 20, "Price_Date": "2026-10-23"},
            {"Symbol": "KEEP", "Rank": 60, "Price": 10, "Price_Date": "2026-10-23"},
            {"Symbol": "EXIT", "Rank": 61, "Price": 10, "Price_Date": "2026-10-23"},
            {"Symbol": "NEXT", "Rank": 61, "Price": 25, "Price_Date": "2026-10-23"},
        ]

        result, cash, trades, statuses = _run_rebalance(
            ranked_rows=ranked,
            positions=positions,
            cash_balance=0.0,
            initial_capital=1_000.0,
            top_n=2,
            exit_rank=60,
            rebalance_date=date(2026, 10, 25),
            execution_date=date(2026, 10, 23),
            price_lookup=prices,
            initial=False,
        )

        self.assertEqual(set(result), {"KEEP", "BEST"})
        self.assertEqual(statuses["KEEP"], "RETAINED")
        self.assertEqual(statuses["EXIT"], "SOLD_RANK_BELOW_60")
        self.assertEqual(statuses["BEST"], "NEW_BUY")
        self.assertEqual([trade["Action"] for trade in trades], ["SELL", "BUY"])
        self.assertAlmostEqual(trades[0]["Realized_PnL"], 20.0)
        self.assertEqual(trades[1]["Gross_Amount"], 100.0)
        self.assertAlmostEqual(cash, 0.0)

    def test_initial_allocation_is_equal_budget_with_cash_for_whole_shares(self):
        ranked = [
            {"Symbol": "A", "Rank": 1, "Price": 100, "Price_Date": "2026-09-25"},
            {"Symbol": "B", "Rank": 2, "Price": 200, "Price_Date": "2026-09-25"},
        ]
        prices = {
            "A": pd.Series([100.0], index=pd.to_datetime(["2026-09-25"])),
            "B": pd.Series([200.0], index=pd.to_datetime(["2026-09-25"])),
        }
        positions, cash, trades, statuses = _run_rebalance(
            ranked_rows=ranked,
            positions={},
            cash_balance=1_000.0,
            initial_capital=1_000.0,
            top_n=2,
            exit_rank=60,
            rebalance_date=date(2026, 9, 25),
            execution_date=date(2026, 9, 25),
            price_lookup=prices,
            initial=True,
        )
        self.assertEqual(positions["A"]["Quantity"], 5)
        self.assertEqual(positions["B"]["Quantity"], 2)
        self.assertEqual(len(trades), 2)
        self.assertEqual(statuses, {"A": "INITIAL_BUY", "B": "INITIAL_BUY"})
        self.assertEqual(cash, 100.0)

    def test_does_not_rebuy_a_stock_ranked_below_the_exit_threshold(self):
        position = {
            "Quantity": 10,
            "Entry_Date": "2026-09-25",
            "Entry_Price": 8.0,
            "Cost_Basis": 80.0,
            "Last_Price": 8.0,
            "Last_Price_Date": "2026-10-23",
            "Rank": 20,
        }
        prices = {
            "EXIT": pd.Series([10.0], index=pd.to_datetime(["2026-10-23"])),
        }
        ranked = [
            {"Symbol": "EXIT", "Rank": 61, "Price": 10, "Price_Date": "2026-10-23"},
        ]
        positions, cash, trades, statuses = _run_rebalance(
            ranked_rows=ranked,
            positions={"EXIT": position},
            cash_balance=0.0,
            initial_capital=1_000.0,
            top_n=1,
            exit_rank=60,
            rebalance_date=date(2026, 10, 25),
            execution_date=date(2026, 10, 23),
            price_lookup=prices,
            initial=False,
        )
        self.assertEqual(positions, {})
        self.assertEqual([trade["Action"] for trade in trades], ["SELL"])
        self.assertEqual(statuses["EXIT"], "SOLD_RANK_BELOW_60")
        self.assertEqual(cash, 100.0)

    def test_buy_sell_ledger_pairs_closed_shares_and_shows_open_shares(self):
        transactions = [
            {
                "Execution_Date": "2026-09-25",
                "Symbol": "ABC",
                "Action": "BUY",
                "Quantity": 10,
                "Price": 10.0,
                "Gross_Amount": 100.0,
            },
            {
                "Execution_Date": "2026-10-25",
                "Symbol": "ABC",
                "Action": "SELL",
                "Quantity": 6,
                "Price": 12.0,
                "Gross_Amount": 72.0,
            },
            {
                "Execution_Date": "2026-10-25",
                "Symbol": "ABC",
                "Action": "BUY",
                "Quantity": 2,
                "Price": 11.0,
                "Gross_Amount": 22.0,
            },
        ]
        current = pd.DataFrame([{
            "Symbol": "ABC",
            "Quantity": 6,
            "Last_Price": 13.0,
        }])

        ledger = _build_buy_sell_ledger(transactions, current)

        self.assertEqual(list(ledger.columns), BUY_SELL_COLUMNS)
        self.assertEqual(ledger["Status"].tolist(), ["CLOSED", "OPEN", "OPEN"])
        closed = ledger.loc[ledger["Status"] == "CLOSED"].iloc[0]
        self.assertEqual(closed["Buy_Date"], "2026-09-25")
        self.assertEqual(closed["Sell_Date"], "2026-10-25")
        self.assertEqual(closed["Buy_Quantity"], 6)
        self.assertEqual(closed["Sell_Quantity"], 6)
        self.assertEqual(closed["Buy_Total"], 60.0)
        self.assertEqual(closed["Sell_Total"], 72.0)
        self.assertEqual(closed["Realized_PnL"], 12.0)
        open_rows = ledger.loc[ledger["Status"] == "OPEN"]
        self.assertEqual(open_rows["Open_Quantity"].tolist(), [4, 2])
        self.assertEqual(open_rows["Current_Value"].tolist(), [52.0, 26.0])
        self.assertEqual(open_rows["Unrealized_PnL"].tolist(), [12.0, 4.0])


if __name__ == "__main__":
    unittest.main()

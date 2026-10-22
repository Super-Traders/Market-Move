import argparse
import csv
import sqlite3
import sys
from pathlib import Path

from config import DB_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show date coverage and row counts for cached symbols."
    )
    parser.add_argument(
        "--include-index",
        action="store_true",
        help="Include index symbols such as IDX:NIFTY 500.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optionally save the report to a CSV file.",
    )
    args = parser.parse_args()

    db_path = Path(DB_PATH).resolve()
    if not db_path.is_file():
        print(f"[ERROR] Cache database not found: {db_path}", file=sys.stderr)
        return 1

    query = """
        SELECT
            symbol,
            MIN(date) AS start_date,
            MAX(date) AS end_date,
            COUNT(*) AS record_count
        FROM ohlcv
    """
    if not args.include_index:
        query += "\nWHERE symbol NOT LIKE 'IDX:%'"
    query += "\nGROUP BY symbol\nORDER BY symbol"

    try:
        # mode=ro prevents SQLite from creating or changing the database.
        with sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True) as conn:
            rows = conn.execute(query).fetchall()
    except sqlite3.Error as exc:
        print(f"[ERROR] Could not read cache database: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print("No cached records found.")
        return 0

    headers = ("SYMBOL", "START DATE", "END DATE", "RECORDS")
    widths = [
        max(len(headers[0]), max(len(str(row[0])) for row in rows)),
        len(headers[1]),
        len(headers[2]),
        len(headers[3]),
    ]

    print(
        f"{headers[0]:<{widths[0]}}  "
        f"{headers[1]:<{widths[1]}}  "
        f"{headers[2]:<{widths[2]}}  "
        f"{headers[3]:>{widths[3]}}"
    )
    print("-" * (sum(widths) + 6))

    for symbol, start_date, end_date, count in rows:
        print(
            f"{symbol:<{widths[0]}}  "
            f"{start_date:<{widths[1]}}  "
            f"{end_date:<{widths[2]}}  "
            f"{count:>{widths[3]},}"
        )

    total_records = sum(row[3] for row in rows)
    print(f"\nSymbols: {len(rows):,} | Records: {total_records:,}")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(("symbol", "start_date", "end_date", "record_count"))
            writer.writerows(rows)
        print(f"Saved CSV report: {args.csv.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
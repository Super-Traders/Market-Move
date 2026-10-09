import pandas as pd
import sqlite3
from config import DB_PATH

def fetch_stock_from_cache(symbol, from_date=None, to_date=None):
    """
    Return a DataFrame for a stock from the SQLite cache DB.
    symbol: e.g. 'RELIANCE', 'TCS'
    from_date: 'YYYY-MM-DD'
    to_date: 'YYYY-MM-DD'
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
                    # SELECT date, open, high, low, close, volume
        query = """
            SELECT date, open, high, low, close, volume,symbol
            FROM ohlcv
            WHERE symbol = ?
        """
        params = [symbol]

        if from_date:
            query += " AND date >= ?"
            params.append(str(from_date))

        if to_date:
            query += " AND date <= ?"
            params.append(str(to_date))

        query += " ORDER BY date ASC"

        df = pd.read_sql_query(query, conn, params=params)
        # print(df)

        if df.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "symbol"])

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df.columns = ["Open", "High", "Low", "Close", "Volume", "symbol"]

        return df

    finally:
        conn.close()


def fetch_stock_list():
    """
    Return a list of all stock symbols in the SQLite cache DB.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        query = "SELECT DISTINCT symbol FROM ohlcv"
        df = pd.read_sql_query(query, conn)
        return df["symbol"].tolist()
    finally:
        conn.close()



# Example usage
# stock_list = fetch_stock_list()
# print(stock_list)

df = fetch_stock_from_cache("IDX:NIFTY 50", from_date="2026-01-01", to_date="2026-12-31")
print(df.head())
print(df.tail())


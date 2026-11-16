"""
Update cache with a selected stock or index.

This script updates the SQLite cache database with data for a given symbol.
It can be used to refresh the OHLCV data for a specific stock or index.
"""

import os
import sys
from datetime import date

from data.cache  import get_connection, save_ohlcv, load_ohlcv, needs_update


def update_cache_for_symbol(symbol: str, source: str = "stock"):
    """
    Update the cache database with OHLCV data for the given symbol.
    
    Args:
        symbol: The stock or index symbol to update (e.g., "NIFTY", "TCS", "NIFTY500")
        source: The data source to use (default: "stock")
    
    Returns:
        bool: True if the update was successful, False otherwise
    """
    # Ensure the database file exists
    db_path = os.path.join(os.path.dirname(__file__), "data", "cache.db")
    if not os.path.exists(db_path):
        print(f"Error: Cache database not found at {db_path}")
        return False
    
    # Connect to the database
    conn = get_connection()
    try:
        # Check if we need to update this symbol
        if needs_update(conn, symbol):
            print(f"Updating cache for symbol: {symbol}")
            
            # Fetch the latest OHLCV data for the symbol
            df = load_ohlcv(conn, symbol)
            
            if not df.empty:
                # Save the OHLCV data to the database
                save_ohlcv(conn, symbol, df, source=source)
                print(f"Successfully updated cache for {symbol}")
                return True
            else:
                print(f"No data found for symbol: {symbol}")
                return False
        else:
            print(f"Symbol {symbol} is up to date. No update needed.")
            return True
    except Exception as e:
        print(f"Error updating cache for {symbol}: {e}")
        return False
    finally:
        conn.close()


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python update_cache_pgm.py <symbol>")
        print("Example: python update_cache_pgm.py NIFTY")
        sys.exit(1)
    
    symbol = sys.argv[1]
    
    # Validate the symbol (basic check)
    if not symbol or not isinstance(symbol, str):
        print("Error: Symbol must be a non-empty string")
        sys.exit(1)
    
    success = update_cache_for_symbol(symbol)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
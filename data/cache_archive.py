"""Export and restore the SQLite market-data cache as verified CSV chunks."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.cache import get_connection

FORMAT_VERSION = 1
OHLCV_COLUMNS = (
    "symbol", "date", "open", "high", "low", "close", "volume", "source",
)
FETCH_LOG_COLUMNS = ("symbol", "last_fetched")
QUALITY_COLUMNS = (
    "symbol", "sources", "n_rows", "n_common", "agree_pct", "ticks_repaired",
    "last_date", "status", "validated_on",
)
CHUNK_ROWS = 1000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as archive_file:
        for block in iter(lambda: archive_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv_gz(path: Path, columns: Iterable[str], rows: Iterable[tuple]) -> int:
    count = 0
    with gzip.open(path, "wt", encoding="utf-8", newline="") as archive_file:
        writer = csv.writer(archive_file, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _table_rows(conn: sqlite3.Connection, table: str, columns: tuple[str, ...]):
    column_sql = ", ".join(columns)
    cursor = conn.execute(f"SELECT {column_sql} FROM {table} ORDER BY {columns[0]}")
    yield from cursor


def export_cache(
    conn: sqlite3.Connection,
    output_dir: Path,
    symbols_per_chunk: int = 25,
) -> dict:
    """Write an internally consistent point-in-time snapshot to compressed CSVs."""
    if symbols_per_chunk < 1:
        raise ValueError("symbols_per_chunk must be at least 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    conn.commit()
    conn.execute("BEGIN")
    try:
        symbols = [
            row[0]
            for row in conn.execute("SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol")
        ]
        chunks = []
        for chunk_number, start in enumerate(range(0, len(symbols), symbols_per_chunk), 1):
            chunk_symbols = symbols[start:start + symbols_per_chunk]
            placeholders = ",".join("?" for _ in chunk_symbols)
            columns_sql = ", ".join(OHLCV_COLUMNS)
            rows = conn.execute(
                f"SELECT {columns_sql} FROM ohlcv "
                f"WHERE symbol IN ({placeholders}) ORDER BY symbol, date",
                chunk_symbols,
            )
            filename = f"ohlcv_{chunk_number:04d}.csv.gz"
            path = output_dir / filename
            row_count = _write_csv_gz(path, OHLCV_COLUMNS, rows)
            chunks.append({
                "file": filename,
                "symbols": len(chunk_symbols),
                "rows": row_count,
                "sha256": _sha256(path),
            })

        tables = {}
        for table, columns, filename in (
            ("fetch_log", FETCH_LOG_COLUMNS, "fetch_log.csv.gz"),
            ("data_quality", QUALITY_COLUMNS, "data_quality.csv.gz"),
        ):
            path = output_dir / filename
            row_count = _write_csv_gz(path, columns, _table_rows(conn, table, columns))
            tables[table] = {
                "file": filename,
                "rows": row_count,
                "sha256": _sha256(path),
            }

        manifest = {
            "format_version": FORMAT_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "symbols_per_chunk": symbols_per_chunk,
            "ohlcv": {
                "symbols": len(symbols),
                "rows": sum(chunk["rows"] for chunk in chunks),
                "chunks": chunks,
            },
            "tables": tables,
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return manifest
    finally:
        conn.rollback()


def _verified_file(directory: Path, entry: dict) -> Path:
    filename = entry.get("file")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise ValueError(f"Invalid archive filename: {filename!r}")
    path = directory / filename
    if not path.is_file():
        raise ValueError(f"Archive file is missing: {path}")
    if _sha256(path) != entry.get("sha256"):
        raise ValueError(f"Checksum mismatch: {path}")
    return path


def _as_float(value: str, column: str, line_number: int):
    if value == "":
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {column} on CSV line {line_number}: {value!r}") from exc
    return parsed if math.isfinite(parsed) else None


def _as_int(value: str, column: str, line_number: int):
    parsed = _as_float(value, column, line_number)
    if parsed is None:
        return None
    if not parsed.is_integer():
        raise ValueError(f"Invalid {column} on CSV line {line_number}: {value!r}")
    return int(parsed)


def _read_rows(path: Path, expected_columns: tuple[str, ...]):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as archive_file:
        reader = csv.reader(archive_file)
        header = next(reader, None)
        if tuple(header or ()) != expected_columns:
            raise ValueError(f"Unexpected columns in {path.name}: {header!r}")
        for line_number, row in enumerate(reader, 2):
            if len(row) != len(expected_columns):
                raise ValueError(f"Invalid field count in {path.name} line {line_number}")
            yield line_number, row


def _load_ohlcv(conn: sqlite3.Connection, path: Path) -> int:
    insert_sql = (
        "INSERT OR REPLACE INTO ohlcv "
        "(symbol, date, open, high, low, close, volume, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    batch = []
    count = 0
    for line_number, row in _read_rows(path, OHLCV_COLUMNS):
        symbol, row_date, open_, high, low, close, volume, source = row
        if not symbol:
            raise ValueError(f"Missing symbol in {path.name} line {line_number}")
        try:
            normalized_date = date.fromisoformat(row_date).isoformat()
        except ValueError as exc:
            raise ValueError(
                f"Invalid date in {path.name} line {line_number}: {row_date!r}"
            ) from exc
        batch.append((
            symbol,
            normalized_date,
            _as_float(open_, "open", line_number),
            _as_float(high, "high", line_number),
            _as_float(low, "low", line_number),
            _as_float(close, "close", line_number),
            _as_int(volume, "volume", line_number),
            source or None,
        ))
        count += 1
        if len(batch) >= CHUNK_ROWS:
            conn.executemany(insert_sql, batch)
            batch.clear()
    if batch:
        conn.executemany(insert_sql, batch)
    return count


def _load_metadata_table(
    conn: sqlite3.Connection,
    path: Path,
    table: str,
    columns: tuple[str, ...],
) -> int:
    insert_sql = (
        f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})"
    )
    numeric_columns = {
        "n_rows", "n_common", "agree_pct", "ticks_repaired",
    }
    batch = []
    count = 0
    for line_number, row in _read_rows(path, columns):
        values = []
        for column, value in zip(columns, row):
            if column in {"last_fetched", "last_date", "validated_on"}:
                if value:
                    try:
                        value = date.fromisoformat(value).isoformat()
                    except ValueError as exc:
                        raise ValueError(
                            f"Invalid {column} in {path.name} line {line_number}: {value!r}"
                        ) from exc
                else:
                    value = None
            elif column in numeric_columns:
                value = _as_float(value, column, line_number)
                if value is not None and column != "agree_pct" and not value.is_integer():
                    raise ValueError(
                        f"Invalid {column} in {path.name} line {line_number}"
                    )
                if value is not None and column != "agree_pct":
                    value = int(value)
            elif value == "":
                value = None
            values.append(value)
        batch.append(tuple(values))
        count += 1
        if len(batch) >= CHUNK_ROWS:
            conn.executemany(insert_sql, batch)
            batch.clear()
    if batch:
        conn.executemany(insert_sql, batch)
    return count


def import_cache(
    conn: sqlite3.Connection,
    input_dir: Path,
    replace: bool = False,
) -> dict:
    """Restore CSV chunks; optionally replace all currently cached records."""
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Archive manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"Unsupported archive format version: {manifest.get('format_version')!r}"
        )

    ohlcv = manifest.get("ohlcv", {})
    chunks = ohlcv.get("chunks", [])
    tables = manifest.get("tables", {})
    expected_files = [
        (_verified_file(input_dir, chunk), chunk["rows"], "ohlcv")
        for chunk in chunks
    ]
    for table, columns in (
        ("fetch_log", FETCH_LOG_COLUMNS),
        ("data_quality", QUALITY_COLUMNS),
    ):
        if table not in tables:
            raise ValueError(f"Archive manifest is missing table: {table}")
        entry = tables[table]
        expected_files.append((_verified_file(input_dir, entry), entry["rows"], table))

    conn.commit()
    conn.execute("BEGIN")
    try:
        if replace:
            conn.execute("DELETE FROM ohlcv")
            conn.execute("DELETE FROM fetch_log")
            conn.execute("DELETE FROM data_quality")

        imported = {"ohlcv": 0, "fetch_log": 0, "data_quality": 0}
        for path, expected_count, table in expected_files:
            if table == "ohlcv":
                count = _load_ohlcv(conn, path)
            else:
                columns = FETCH_LOG_COLUMNS if table == "fetch_log" else QUALITY_COLUMNS
                count = _load_metadata_table(conn, path, table, columns)
            if count != expected_count:
                raise ValueError(
                    f"Row count mismatch in {path.name}: expected {expected_count}, got {count}"
                )
            imported[table] += count

        if imported["ohlcv"] != ohlcv.get("rows"):
            raise ValueError(
                f"OHLCV total mismatch: expected {ohlcv.get('rows')}, "
                f"got {imported['ohlcv']}"
            )
        conn.commit()
        return imported
    except Exception:
        conn.rollback()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export or restore the market-data SQLite cache as CSV chunks."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export cache to CSV chunks.")
    export_parser.add_argument(
        "--output", type=Path, default=Path("data/cache_seed"),
        help="Export directory (default: data/cache_seed).",
    )
    export_parser.add_argument(
        "--symbols-per-chunk", type=int, default=25,
        help="Symbols per compressed OHLCV chunk (default: 25).",
    )

    import_parser = subparsers.add_parser("import", help="Import CSV chunks into cache.")
    import_parser.add_argument(
        "--input", type=Path, default=Path("data/cache_seed"),
        help="Export directory (default: data/cache_seed).",
    )
    import_parser.add_argument(
        "--replace", action="store_true",
        help="Clear existing cache tables before importing the archive.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        conn = get_connection()
        try:
            if args.command == "export":
                manifest = export_cache(conn, args.output, args.symbols_per_chunk)
                print(
                    f"Exported {manifest['ohlcv']['rows']:,} OHLCV rows for "
                    f"{manifest['ohlcv']['symbols']:,} symbols into "
                    f"{len(manifest['ohlcv']['chunks'])} chunks at {args.output}."
                )
            else:
                imported = import_cache(conn, args.input, replace=args.replace)
                print(
                    "Imported "
                    f"{imported['ohlcv']:,} OHLCV rows, "
                    f"{imported['fetch_log']:,} fetch-log rows, and "
                    f"{imported['data_quality']:,} quality rows."
                )
        finally:
            conn.close()
    except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

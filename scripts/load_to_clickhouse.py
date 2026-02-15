#!/usr/bin/env python3
"""
Load generated events data into ClickHouse.

Usage:
    python scripts/load_to_clickhouse.py --input output/run_YYYYMMDD_HHMMSS/events.jsonl.gz --run-id baseline
    python scripts/load_to_clickhouse.py --input output/run_YYYYMMDD_HHMMSS/events.parquet --run-id exp_fast_energy
    python scripts/load_to_clickhouse.py --delete-run baseline
"""

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Iterator

try:
    import clickhouse_connect
except ImportError:
    print("Error: clickhouse-connect not installed.")
    print("Run: pip install clickhouse-connect")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Load events into ClickHouse")
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Path to events file (jsonl.gz or parquet)"
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier (e.g.: baseline, exp_fast_energy). Required for loading and identifying data runs."
    )
    parser.add_argument(
        "--delete-run",
        help="Delete all data for the specified run_id and exit"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="ClickHouse host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8123,
        help="ClickHouse HTTP port (default: 8123)"
    )
    parser.add_argument(
        "--user",
        default="admin",
        help="ClickHouse user (default: admin)"
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="ClickHouse password"
    )
    parser.add_argument(
        "--database",
        default="game_analytics",
        help="Target database (default: game_analytics)"
    )
    parser.add_argument(
        "--table",
        default="events",
        help="Target table (default: events)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for inserts (default: 10000)"
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing data for this run_id before loading"
    )
    return parser.parse_args()


def read_jsonl_gz(filepath: Path, batch_size: int) -> Iterator[list[dict]]:
    """Read JSONL.GZ file in batches."""
    batch = []
    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        for line in f:
            event = json.loads(line)
            batch.append(flatten_event(event))
            if len(batch) >= batch_size:
                yield batch
                batch = []
    if batch:
        yield batch


def read_parquet(filepath: Path, batch_size: int) -> Iterator[list[dict]]:
    """Read Parquet file in batches."""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas not installed for parquet support.")
        print("Run: pip install pandas pyarrow")
        sys.exit(1)

    df = pd.read_parquet(filepath)
    for start in range(0, len(df), batch_size):
        batch_df = df.iloc[start:start + batch_size]
        batch = []
        for _, row in batch_df.iterrows():
            event = row.to_dict()
            batch.append(flatten_event(event))
        yield batch


from datetime import date, datetime


def to_string(value) -> str:
    """Convert any value to string safely."""
    if value is None:
        return ""
    if hasattr(value, 'isoformat'):  # date/datetime objects
        return value.isoformat()
    return str(value)


def to_date(value) -> date:
    """Convert value to date object for ClickHouse Date type."""
    if value is None:
        return date(1970, 1, 1)
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Parse YYYY-MM-DD format
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except:
            return date(1970, 1, 1)
    return date(1970, 1, 1)


def to_datetime(value) -> datetime:
    """Convert value to datetime object for ClickHouse DateTime type."""
    if value is None:
        return datetime(1970, 1, 1)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        # Handle ISO format with Z or +00:00
        try:
            ts = value.replace("Z", "+00:00")
            # Remove timezone for naive datetime (ClickHouse prefers naive)
            if "+" in ts:
                ts = ts.split("+")[0]
            return datetime.fromisoformat(ts)
        except:
            return datetime(1970, 1, 1)
    return datetime(1970, 1, 1)


def flatten_event(event: dict) -> dict:
    """Flatten nested event structure for ClickHouse."""
    device = event.get("device", {})
    user_props = event.get("user_properties", {})

    # Convert timestamp to datetime object
    timestamp = to_datetime(event.get("event_timestamp"))

    # Convert cohort_date to date object
    cohort_date = to_date(user_props.get("cohort_date"))

    return {
        "event_id": to_string(event.get("event_id", "")),
        "event_name": to_string(event.get("event_name", "")),
        "event_timestamp": timestamp,  # datetime object
        "user_id": to_string(event.get("user_id", "")),
        "session_id": to_string(event.get("session_id", "")),
        # Device
        "device_id": to_string(device.get("device_id", "")),
        "platform": to_string(device.get("platform", "")),
        "os_version": to_string(device.get("os_version", "")),
        "app_version": to_string(device.get("app_version", "")),
        "device_model": to_string(device.get("device_model", "")),
        "country": to_string(device.get("country", "")),
        "language": to_string(device.get("language", "")),
        # User properties
        "player_level": int(user_props.get("player_level", 0) or 0),
        "vip_level": int(user_props.get("vip_level", 0) or 0),
        "total_spent_usd": float(user_props.get("total_spent_usd", 0.0) or 0.0),
        "days_since_install": int(user_props.get("days_since_install", 0) or 0),
        "cohort_date": cohort_date,  # date object
        "current_chapter": int(user_props.get("current_chapter", 0) or 0),
        # JSON fields
        "ab_tests": json.dumps(event.get("ab_tests", {}) or {}),
        "event_properties": json.dumps(event.get("event_properties", {}) or {}),
    }


def _show_run_stats(client, database: str, table: str):
    """Show statistics for all runs in the table."""
    print(f"\n{'='*60}")
    print(f"Run statistics in {database}.{table}:")
    print(f"{'='*60}")
    result = client.query(
        f"SELECT run_id, count() as events, uniqExact(user_id) as users "
        f"FROM {database}.{table} "
        f"GROUP BY run_id "
        f"ORDER BY run_id"
    )
    if result.result_rows:
        print(f"{'Run ID':<30} {'Events':>12} {'Users':>10}")
        print(f"{'-'*30} {'-'*12} {'-'*10}")
        for row in result.result_rows:
            print(f"{row[0]:<30} {row[1]:>12,} {row[2]:>10,}")
    else:
        print("No data in table.")
    print()


def main():
    args = parse_args()

    # Handle --delete-run mode (does not require --input or --run-id)
    if args.delete_run:
        if not args.input:
            # --delete-run can work without --input, connect and delete
            pass
        # Will handle after connection
    else:
        # Loading mode: both --input and --run-id are required
        if not args.run_id:
            print("Error: --run-id is required when loading data.")
            print("Usage: python scripts/load_to_clickhouse.py --input <file> --run-id <name>")
            sys.exit(1)
        if not args.input:
            print("Error: --input is required when loading data.")
            print("Usage: python scripts/load_to_clickhouse.py --input <file> --run-id <name>")
            sys.exit(1)

    filepath = Path(args.input) if args.input else None

    if filepath and not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    # Connect to ClickHouse
    print(f"Connecting to ClickHouse at {args.host}:{args.port}...")
    client = clickhouse_connect.get_client(
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        database=args.database,
    )

    # Test connection
    try:
        result = client.query("SELECT 1")
        print("Connected successfully!")
    except Exception as e:
        print(f"Error connecting to ClickHouse: {e}")
        sys.exit(1)

    # Delete run if requested
    if args.delete_run:
        run_id = args.delete_run
        print(f"Deleting data for run_id='{run_id}'...")
        client.command(
            f"ALTER TABLE {args.database}.{args.table} DELETE WHERE run_id = '{run_id}'"
        )
        print(f"Delete command issued for run_id='{run_id}'.")
        # Show remaining runs
        _show_run_stats(client, args.database, args.table)
        return

    # Truncate if requested
    if args.truncate:
        print(f"Deleting existing data for run_id='{args.run_id}'...")
        client.command(
            f"ALTER TABLE {args.database}.{args.table} DELETE WHERE run_id = '{args.run_id}'"
        )
        print(f"Existing data for run_id='{args.run_id}' deleted.")

    # Determine file type and reader
    if filepath.suffix == ".gz" or str(filepath).endswith(".jsonl.gz"):
        reader = read_jsonl_gz(filepath, args.batch_size)
        print(f"Reading JSONL.GZ file: {filepath}")
    elif filepath.suffix == ".parquet":
        reader = read_parquet(filepath, args.batch_size)
        print(f"Reading Parquet file: {filepath}")
    else:
        print(f"Error: Unsupported file format: {filepath.suffix}")
        print("Supported formats: .jsonl.gz, .parquet")
        sys.exit(1)

    # Column names for insert
    columns = [
        "run_id",
        "event_id", "event_name", "event_timestamp",
        "user_id", "session_id",
        "device_id", "platform", "os_version", "app_version",
        "device_model", "country", "language",
        "player_level", "vip_level", "total_spent_usd",
        "days_since_install", "cohort_date", "current_chapter",
        "ab_tests", "event_properties",
    ]

    # Load data
    total_rows = 0
    batch_num = 0

    print("Loading data...")
    for batch in reader:
        batch_num += 1
        rows = [[args.run_id] + [row[col] for col in columns[1:]] for row in batch]

        try:
            client.insert(
                table=args.table,
                data=rows,
                column_names=columns,
            )
            total_rows += len(rows)
            print(f"  Batch {batch_num}: {len(rows)} rows (total: {total_rows})")
        except Exception as e:
            print(f"Error inserting batch {batch_num}: {e}")
            # Try to continue with next batch
            continue

    print(f"\nDone! Loaded {total_rows} events into {args.database}.{args.table}")

    # Show stats by run_id
    _show_run_stats(client, args.database, args.table)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Setup team databases and users in ClickHouse.

Creates isolated databases for each team with:
- Own events table (same schema as game_analytics.events including run_id)
- Team user with full access to their database
- Read-only access to shared game_analytics database

Usage:
    python scripts/setup_teams.py
    python scripts/setup_teams.py --teams 13 --password-prefix team_pass_
    python scripts/setup_teams.py --drop  # Remove all team databases and users
"""

import argparse
import csv
import sys
from pathlib import Path

try:
    import clickhouse_connect
except ImportError:
    print("Error: clickhouse-connect not installed.")
    print("Run: pip install clickhouse-connect")
    sys.exit(1)


EVENTS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS {database}.events
(
    run_id LowCardinality(String),
    event_id String,
    event_name LowCardinality(String),
    event_timestamp DateTime64(3),
    user_id String,
    session_id String,
    device_id String,
    platform LowCardinality(String),
    os_version LowCardinality(String),
    app_version LowCardinality(String),
    device_model LowCardinality(String),
    country LowCardinality(String),
    language LowCardinality(String),
    player_level UInt16,
    vip_level UInt8,
    total_spent_usd Float32,
    days_since_install UInt16,
    cohort_date Date,
    current_chapter UInt8,
    ab_tests String,
    event_properties String,
    event_date Date DEFAULT toDate(event_timestamp)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (run_id, event_name, user_id, event_timestamp)
SETTINGS index_granularity = 8192
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Setup team databases and users in ClickHouse"
    )
    parser.add_argument(
        "--teams", "-n",
        type=int,
        default=13,
        help="Number of teams (default: 13)"
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
        "--admin-user",
        default="admin",
        help="Admin user (default: admin)"
    )
    parser.add_argument(
        "--admin-password",
        default="admin123",
        help="Admin password (default: admin123)"
    )
    parser.add_argument(
        "--password-prefix",
        default="team_pass_",
        help="Prefix for team passwords (default: team_pass_)"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all team databases and users (cleanup)"
    )
    parser.add_argument(
        "--output",
        default="teams_credentials.csv",
        help="Output CSV file with credentials (default: teams_credentials.csv)"
    )
    return parser.parse_args()


def team_name(i: int) -> str:
    """Generate team name like team_01, team_02, ..."""
    return f"team_{i:02d}"


def drop_teams(client, num_teams: int):
    """Drop all team databases and users."""
    print("\nDropping team databases and users...")
    for i in range(1, num_teams + 1):
        name = team_name(i)
        try:
            client.command(f"DROP DATABASE IF EXISTS {name}")
            print(f"  Dropped database: {name}")
        except Exception as e:
            print(f"  Warning: Could not drop database {name}: {e}")

        try:
            client.command(f"DROP USER IF EXISTS {name}")
            print(f"  Dropped user: {name}")
        except Exception as e:
            print(f"  Warning: Could not drop user {name}: {e}")

    print("Cleanup complete!")


def setup_teams(client, num_teams: int, password_prefix: str, host: str, port: int) -> list[dict]:
    """Create team databases, tables, and users."""
    credentials = []

    print(f"\nSetting up {num_teams} teams...")
    print("=" * 60)

    for i in range(1, num_teams + 1):
        name = team_name(i)
        password = f"{password_prefix}{i:02d}"

        print(f"\n[{i}/{num_teams}] Setting up {name}...")

        # 1. Create database
        client.command(f"CREATE DATABASE IF NOT EXISTS {name}")
        print(f"  Created database: {name}")

        # 2. Create events table
        client.command(EVENTS_TABLE_SCHEMA.format(database=name))
        print(f"  Created table: {name}.events")

        # 3. Create user
        try:
            client.command(f"CREATE USER IF NOT EXISTS {name} IDENTIFIED BY '{password}'")
        except Exception:
            # User might exist, try to alter
            client.command(f"ALTER USER {name} IDENTIFIED BY '{password}'")
        print(f"  Created user: {name}")

        # 4. Grant full access to team database
        client.command(f"GRANT ALL ON {name}.* TO {name}")
        print(f"  Granted ALL on {name}.* to {name}")

        # 5. Grant read-only access to game_analytics
        client.command(f"GRANT SELECT ON game_analytics.* TO {name}")
        print(f"  Granted SELECT on game_analytics.* to {name}")

        credentials.append({
            "team": name,
            "database": name,
            "username": name,
            "password": password,
            "clickhouse_url": f"http://{host}:{port}",
        })

    return credentials


def save_credentials(credentials: list[dict], output_path: str):
    """Save credentials to CSV file."""
    filepath = Path(output_path)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["team", "database", "username", "password", "clickhouse_url"])
        writer.writeheader()
        writer.writerows(credentials)
    print(f"\nCredentials saved to: {filepath.absolute()}")


def print_credentials_table(credentials: list[dict]):
    """Print credentials as a formatted table."""
    print(f"\n{'='*80}")
    print("TEAM CREDENTIALS")
    print(f"{'='*80}")
    print(f"{'Team':<12} {'Database':<12} {'Username':<12} {'Password':<18} {'URL'}")
    print(f"{'-'*12} {'-'*12} {'-'*12} {'-'*18} {'-'*24}")
    for cred in credentials:
        print(
            f"{cred['team']:<12} "
            f"{cred['database']:<12} "
            f"{cred['username']:<12} "
            f"{cred['password']:<18} "
            f"{cred['clickhouse_url']}"
        )
    print(f"{'='*80}")
    print(f"\nAll teams also have READ-ONLY access to: game_analytics.*")
    print(f"Students can query: SELECT * FROM game_analytics.events")
    print(f"Students can write to their own database: INSERT INTO {credentials[0]['database']}.events ...")


def main():
    args = parse_args()

    # Connect to ClickHouse
    print(f"Connecting to ClickHouse at {args.host}:{args.port}...")
    client = clickhouse_connect.get_client(
        host=args.host,
        port=args.port,
        username=args.admin_user,
        password=args.admin_password,
    )

    # Test connection
    try:
        client.query("SELECT 1")
        print("Connected successfully!")
    except Exception as e:
        print(f"Error connecting to ClickHouse: {e}")
        sys.exit(1)

    if args.drop:
        drop_teams(client, args.teams)
        return

    # Setup teams
    credentials = setup_teams(
        client, args.teams, args.password_prefix,
        args.host, args.port
    )

    # Print and save credentials
    print_credentials_table(credentials)
    save_credentials(credentials, args.output)

    print(f"\nSetup complete! {args.teams} teams configured.")
    print(f"\nNext steps:")
    print(f"  1. Share credentials with teams (see {args.output})")
    print(f"  2. Teams can load data: python scripts/load_to_clickhouse.py \\")
    print(f"       --input <file> --run-id <name> \\")
    print(f"       --database <team_db> --user <team_user> --password <team_pass>")
    print(f"  3. Teams can query shared data: SELECT * FROM game_analytics.events")


if __name__ == "__main__":
    main()

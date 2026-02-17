#!/usr/bin/env python3
"""
Setup Superset team isolation for Game Analytics course.

Creates per-team database connections, roles, and users in Superset.
Each team gets:
- Their own ClickHouse database connection visible in SQL Lab
- Access to shared game_analytics database (read-only via ClickHouse)
- A custom role with SQL Lab permissions + access only to their databases
- A Superset user with Gamma + custom team role

This ensures teams see only their own databases/datasets in Superset,
while still having read-only access to shared game_analytics data.

Prerequisites:
    1. Superset and ClickHouse must be running (docker-compose up)
    2. ClickHouse teams must be created first (python scripts/setup_teams.py)
    3. Shared DB connection should exist (python scripts/setup_superset_dashboards.py)

Usage:
    python scripts/setup_superset_teams.py
    python scripts/setup_superset_teams.py --teams 15
    python scripts/setup_superset_teams.py --teams 15 --superset-password-prefix my_prefix_
    python scripts/setup_superset_teams.py --drop  # Remove all team configs from Superset

Requirements:
    pip install requests
"""

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests not installed.")
    print("Run: pip install requests")
    sys.exit(1)


# ============================================================
# Configuration (matches existing scripts)
# ============================================================

# Superset connection (same as setup_superset_dashboards.py)
SUPERSET_URL = "http://localhost:8088"
SUPERSET_ADMIN_USER = "admin"
SUPERSET_ADMIN_PASSWORD = "admin123"

# ClickHouse (Docker internal hostname, same as setup_superset_dashboards.py)
CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_PORT = 8123

# Shared database (created by setup_superset_dashboards.py)
SHARED_DB_NAME = "ClickHouse Game Analytics"
SHARED_DB_USER = "superset"
SHARED_DB_PASSWORD = "superset123"
SHARED_DB_DATABASE = "game_analytics"

# Docker container name (from docker-compose.yml)
SUPERSET_CONTAINER = "superset"


# ============================================================
# Superset REST API Client (reused from setup_superset_dashboards.py)
# ============================================================

class SupersetAPI:
    """Superset API client."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.access_token = None
        self.csrf_token = None
        self._login(username, password)

    def _login(self, username: str, password: str):
        """Login and get access token."""
        resp = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
        if resp.status_code == 200:
            self.csrf_token = resp.json().get("result")
            self.session.headers["X-CSRFToken"] = self.csrf_token

        login_data = {
            "username": username,
            "password": password,
            "provider": "db",
            "refresh": True,
        }
        resp = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json=login_data,
        )
        if resp.status_code != 200:
            raise Exception(f"Login failed: {resp.text}")

        data = resp.json()
        self.access_token = data.get("access_token")
        self.session.headers["Authorization"] = f"Bearer {self.access_token}"

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make API request."""
        url = f"{self.base_url}/api/v1{endpoint}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code >= 400:
            print(f"  API Error {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json() if resp.text else {}

    def get_databases(self) -> list:
        """Get list of database connections."""
        return self._request("GET", "/database/").get("result", [])

    def create_database(self, name: str, sqlalchemy_uri: str) -> Optional[int]:
        """Create database connection."""
        data = {
            "database_name": name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "expose_in_sqllab": True,
            "allow_run_async": True,
            "allow_ctas": False,
            "allow_cvas": False,
            "allow_dml": False,
        }
        result = self._request("POST", "/database/", json=data)
        return result.get("id")

    def delete_database(self, db_id: int) -> bool:
        """Delete database connection."""
        result = self._request("DELETE", f"/database/{db_id}")
        return result is not None


# ============================================================
# Helpers
# ============================================================

def team_name(i: int) -> str:
    """Generate team name like team_01, team_02, ..."""
    return f"team_{i:02d}"


def team_display_name(i: int) -> str:
    """Generate display name like 'Team 01'."""
    return f"Team {i:02d}"


def wait_for_superset(url: str, max_retries: int = 30):
    """Wait for Superset to be healthy."""
    print("Waiting for Superset to be ready...")
    for _ in range(max_retries):
        try:
            resp = requests.get(f"{url}/health", timeout=5)
            if resp.status_code == 200:
                print("  Superset is ready!")
                return True
        except Exception:
            pass
        time.sleep(2)
    print("  ERROR: Superset is not responding")
    return False


# ============================================================
# Phase 1: Database connections via REST API
# ============================================================

def ensure_database_connections(
    api: SupersetAPI,
    num_teams: int,
    ch_password_prefix: str,
) -> dict:
    """
    Create ClickHouse database connections in Superset for each team.
    Returns dict: {"shared": db_id, "team_01": db_id, ...}
    """
    existing = {db["database_name"]: db["id"] for db in api.get_databases()}
    db_ids = {}

    # 1. Ensure shared game_analytics connection exists
    if SHARED_DB_NAME in existing:
        db_ids["shared"] = existing[SHARED_DB_NAME]
        print(f"  [shared] Already exists (id={db_ids['shared']})")
    else:
        uri = (
            f"clickhousedb://{SHARED_DB_USER}:{SHARED_DB_PASSWORD}"
            f"@{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{SHARED_DB_DATABASE}"
        )
        db_id = api.create_database(SHARED_DB_NAME, uri)
        if db_id:
            db_ids["shared"] = db_id
            print(f"  [shared] Created (id={db_id})")
        else:
            print("  [shared] FAILED to create!")
            sys.exit(1)

    # 2. Create per-team database connections
    for i in range(1, num_teams + 1):
        name = team_name(i)
        display = team_display_name(i)

        if display in existing:
            db_ids[name] = existing[display]
            print(f"  [{name}] Already exists (id={db_ids[name]})")
            continue

        password = f"{ch_password_prefix}{i:02d}"
        uri = (
            f"clickhousedb://{name}:{password}"
            f"@{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{name}"
        )
        db_id = api.create_database(display, uri)
        if db_id:
            db_ids[name] = db_id
            print(f"  [{name}] Created '{display}' (id={db_id})")
        else:
            print(f"  [{name}] FAILED to create '{display}'!")

    return db_ids


# ============================================================
# Phase 2: Roles & Users via docker exec + FAB SecurityManager
# ============================================================

def generate_setup_script(
    num_teams: int,
    db_ids: dict,
    superset_password_prefix: str,
) -> str:
    """
    Generate Python script to run inside the Superset container.
    Creates roles with SQL Lab + database access, and users with Gamma + team role.
    """
    shared_db_id = db_ids["shared"]

    teams_config = []
    for i in range(1, num_teams + 1):
        name = team_name(i)
        display = team_display_name(i)
        db_id = db_ids.get(name)
        if db_id is None:
            continue

        teams_config.append({
            "team_name": name,
            "role_name": f"{name}_role",
            "display_name": display,
            "db_id": db_id,
            "db_display_name": display,
            "shared_db_id": shared_db_id,
            "shared_db_name": SHARED_DB_NAME,
            "username": name,
            "password": f"{superset_password_prefix}{i:02d}",
            "email": f"{name}@course.local",
        })

    teams_json = json.dumps(teams_config, ensure_ascii=False)

    # The script that runs INSIDE the superset container
    script = f'''
import sys
import json

# Try different import paths for Superset versions
try:
    from superset.app import create_app
except ImportError:
    from superset import create_app

app = create_app()

with app.app_context():
    from superset.extensions import db as sdb
    sm = app.appbuilder.sm
    session = sdb.session

    teams = json.loads("""{teams_json}""")

    # Find Gamma role (base for all students)
    gamma_role = sm.find_role("Gamma")
    if not gamma_role:
        print("ERROR: Gamma role not found!")
        sys.exit(1)
    print(f"Found Gamma role (id={{gamma_role.id}})")

    # Permissions needed for SQL Lab access
    SQLLAB_PERMS = [
        ("menu_access", "SQL Lab"),
        ("menu_access", "SQL Editor"),
        ("can_read", "Query"),
        ("can_write", "Query"),
        ("can_read", "SavedQuery"),
        ("can_write", "SavedQuery"),
        ("can_sqllab", "Superset"),
        ("can_sql_json", "Superset"),
        ("can_csv", "Superset"),
        ("can_read", "Database"),
    ]

    for team in teams:
        role_name = team["role_name"]
        print(f"\\n--- Setting up {{team['team_name']}} ---")

        # 1. Create or find role
        role = sm.find_role(role_name)
        if not role:
            role = sm.add_role(role_name)
            print(f"  Created role: {{role_name}}")
        else:
            print(f"  Role exists: {{role_name}}")

        # 2. Add SQL Lab permissions
        for perm_name, view_name in SQLLAB_PERMS:
            pv = sm.find_permission_view_menu(perm_name, view_name)
            if pv:
                sm.add_permission_role(role, pv)
            else:
                print(f"  WARN: permission '{{perm_name}}' on '{{view_name}}' not found, skipping")

        # 3. Add database access for team's own DB
        team_db_perm = f"[{{team['db_display_name']}}](id:{{team['db_id']}})"
        pv = sm.find_permission_view_menu("database_access", team_db_perm)
        if pv:
            sm.add_permission_role(role, pv)
            print(f"  Granted database_access on {{team_db_perm}}")
        else:
            print(f"  WARN: database_access '{{team_db_perm}}' not found")

        # 4. Add database access for shared game_analytics DB
        shared_perm = f"[{{team['shared_db_name']}}](id:{{team['shared_db_id']}})"
        pv = sm.find_permission_view_menu("database_access", shared_perm)
        if pv:
            sm.add_permission_role(role, pv)
            print(f"  Granted database_access on {{shared_perm}}")
        else:
            print(f"  WARN: database_access '{{shared_perm}}' not found")

        # 5. Create or update Superset user
        user = sm.find_user(username=team["username"])
        if user:
            user.roles = [gamma_role, role]
            session.commit()
            print(f"  User exists, updated roles: {{team['username']}}")
        else:
            user = sm.add_user(
                username=team["username"],
                first_name=team["display_name"],
                last_name="Student",
                email=team["email"],
                role=gamma_role,
                password=team["password"],
            )
            if user:
                user.roles = [gamma_role, role]
                session.commit()
                print(f"  Created user: {{team['username']}}")
            else:
                print(f"  FAILED to create user: {{team['username']}}")

    session.commit()
    print("\\n=== All teams configured successfully! ===")
'''
    return script


def generate_drop_script(num_teams: int) -> str:
    """Generate Python script to remove team users and roles from Superset."""
    team_names = json.dumps([team_name(i) for i in range(1, num_teams + 1)])

    script = f'''
import sys
import json

try:
    from superset.app import create_app
except ImportError:
    from superset import create_app

app = create_app()

with app.app_context():
    from superset.extensions import db as sdb
    sm = app.appbuilder.sm
    session = sdb.session

    teams = json.loads("""{team_names}""")

    for name in teams:
        # Delete user
        user = sm.find_user(username=name)
        if user:
            session.delete(user)
            print(f"  Deleted user: {{name}}")
        else:
            print(f"  User not found: {{name}}")

        # Delete role
        role = sm.find_role(f"{{name}}_role")
        if role:
            session.delete(role)
            print(f"  Deleted role: {{name}}_role")
        else:
            print(f"  Role not found: {{name}}_role")

    session.commit()
    print("\\nSuperset users and roles cleanup complete!")
'''
    return script


def run_in_container(script: str) -> bool:
    """Execute a Python script inside the Superset Docker container."""
    result = subprocess.run(
        ["docker", "exec", "-i", SUPERSET_CONTAINER, "python", "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        # Filter out common warnings
        stderr_lines = [
            line for line in result.stderr.splitlines()
            if "WARNING" not in line and "DeprecationWarning" not in line
        ]
        if stderr_lines:
            print("STDERR:", "\n".join(stderr_lines))
    return result.returncode == 0


# ============================================================
# Credentials output
# ============================================================

def save_credentials(credentials: list[dict], output_path: str):
    """Save credentials to CSV file."""
    filepath = Path(output_path)
    fieldnames = [
        "team", "superset_username", "superset_password",
        "superset_url", "clickhouse_database",
        "clickhouse_username", "clickhouse_password",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(credentials)
    print(f"\nCredentials saved to: {filepath.absolute()}")


def print_credentials_table(credentials: list[dict]):
    """Print credentials as a formatted table."""
    print(f"\n{'='*90}")
    print("SUPERSET TEAM CREDENTIALS")
    print(f"{'='*90}")
    print(
        f"{'Team':<10} {'Superset User':<16} {'Superset Pass':<20} "
        f"{'CH Database':<14} {'CH User':<10} {'CH Pass':<16}"
    )
    print(
        f"{'-'*10} {'-'*16} {'-'*20} "
        f"{'-'*14} {'-'*10} {'-'*16}"
    )
    for c in credentials:
        print(
            f"{c['team']:<10} "
            f"{c['superset_username']:<16} "
            f"{c['superset_password']:<20} "
            f"{c['clickhouse_database']:<14} "
            f"{c['clickhouse_username']:<10} "
            f"{c['clickhouse_password']:<16}"
        )
    print(f"{'='*90}")


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Setup Superset team isolation for Game Analytics course"
    )
    parser.add_argument(
        "--teams", "-n",
        type=int,
        default=15,
        help="Number of teams (default: 15)",
    )
    parser.add_argument(
        "--clickhouse-password-prefix",
        default="team_pass_",
        help="ClickHouse team password prefix (default: team_pass_)",
    )
    parser.add_argument(
        "--superset-password-prefix",
        default="superset_team_",
        help="Superset user password prefix (default: superset_team_)",
    )
    parser.add_argument(
        "--superset-url",
        default=SUPERSET_URL,
        help=f"Superset URL (default: {SUPERSET_URL})",
    )
    parser.add_argument(
        "--superset-user",
        default=SUPERSET_ADMIN_USER,
        help=f"Superset admin username (default: {SUPERSET_ADMIN_USER})",
    )
    parser.add_argument(
        "--superset-password",
        default=SUPERSET_ADMIN_PASSWORD,
        help=f"Superset admin password (default: {SUPERSET_ADMIN_PASSWORD})",
    )
    parser.add_argument(
        "--container",
        default=SUPERSET_CONTAINER,
        help=f"Superset Docker container name (default: {SUPERSET_CONTAINER})",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Remove all team users, roles, and database connections from Superset",
    )
    parser.add_argument(
        "--output",
        default="superset_teams_credentials.csv",
        help="Output CSV file with credentials (default: superset_teams_credentials.csv)",
    )
    return parser.parse_args()


# ============================================================
# Main
# ============================================================

def main():
    args = parse_args()

    global SUPERSET_CONTAINER
    SUPERSET_CONTAINER = args.container

    # --drop mode
    if args.drop:
        print("=" * 60)
        print("Removing team configurations from Superset")
        print("=" * 60)

        if not wait_for_superset(args.superset_url):
            sys.exit(1)

        # Delete database connections via REST API
        print("\nDeleting team database connections...")
        try:
            api = SupersetAPI(args.superset_url, args.superset_user, args.superset_password)
            databases = api.get_databases()
            for i in range(1, args.teams + 1):
                display = team_display_name(i)
                for db in databases:
                    if db.get("database_name") == display:
                        api.delete_database(db["id"])
                        print(f"  Deleted connection: {display}")
                        break
                else:
                    print(f"  Connection not found: {display}")
        except Exception as e:
            print(f"  Warning: Could not delete database connections: {e}")

        # Delete users and roles via docker exec
        print("\nDeleting team users and roles...")
        script = generate_drop_script(args.teams)
        run_in_container(script)

        print("\nCleanup complete!")
        return

    # --setup mode (default)
    print("=" * 60)
    print("Setting up Superset team isolation")
    print(f"Teams: {args.teams}")
    print("=" * 60)

    if not wait_for_superset(args.superset_url):
        sys.exit(1)

    # Phase 1: Database connections via REST API
    print("\n--- Phase 1: Database connections ---")
    try:
        api = SupersetAPI(args.superset_url, args.superset_user, args.superset_password)
        print("  Logged into Superset API")
    except Exception as e:
        print(f"ERROR: Could not connect to Superset: {e}")
        sys.exit(1)

    db_ids = ensure_database_connections(
        api, args.teams, args.clickhouse_password_prefix,
    )

    if "shared" not in db_ids:
        print("ERROR: Shared database connection not found/created!")
        sys.exit(1)

    created_count = sum(1 for k in db_ids if k.startswith("team_"))
    print(f"\n  Database connections ready: {created_count} teams + 1 shared")

    # Small delay to let Superset register permissions for new databases
    print("\n  Waiting for Superset to register permissions...")
    time.sleep(3)

    # Phase 2: Roles and users via docker exec
    print("\n--- Phase 2: Roles and users ---")
    script = generate_setup_script(
        args.teams, db_ids, args.superset_password_prefix,
    )
    success = run_in_container(script)

    if not success:
        print("\nERROR: Failed to create roles/users inside container!")
        print("Check that the Superset container is running:")
        print(f"  docker ps | grep {SUPERSET_CONTAINER}")
        sys.exit(1)

    # Build and save credentials
    credentials = []
    for i in range(1, args.teams + 1):
        name = team_name(i)
        credentials.append({
            "team": name,
            "superset_username": name,
            "superset_password": f"{args.superset_password_prefix}{i:02d}",
            "superset_url": args.superset_url,
            "clickhouse_database": name,
            "clickhouse_username": name,
            "clickhouse_password": f"{args.clickhouse_password_prefix}{i:02d}",
        })

    print_credentials_table(credentials)
    save_credentials(credentials, args.output)

    print(f"\n{'='*60}")
    print(f"Setup complete! {args.teams} teams configured.")
    print(f"{'='*60}")
    print(f"""
What each team gets:
  - Superset login: team_XX / {args.superset_password_prefix}XX
  - SQL Lab with access to:
    * Their own database (Team XX) — full access
    * Shared database (ClickHouse Game Analytics) — read-only
  - Isolated view: cannot see other teams' datasets/queries

Next steps:
  1. Share credentials with teams (see {args.output})
  2. Students login at {args.superset_url}
  3. Each team selects their database in SQL Lab dropdown
  4. Shared game_analytics data is accessible read-only

To remove all team configs:
  python scripts/setup_superset_teams.py --drop --teams {args.teams}
""")


if __name__ == "__main__":
    main()

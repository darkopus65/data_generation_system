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

Everything runs via `docker exec` inside the Superset container using
the FAB SecurityManager API — no REST API needed.

Prerequisites:
    1. Superset and ClickHouse must be running (docker-compose up)
    2. ClickHouse teams must be created first (python scripts/setup_teams.py)
    3. Shared DB connection should exist (python scripts/setup_superset_dashboards.py)

Usage:
    python scripts/setup_superset_teams.py
    python scripts/setup_superset_teams.py --teams 18
    python scripts/setup_superset_teams.py --teams 18 --superset-password-prefix my_prefix_
    python scripts/setup_superset_teams.py --drop  # Remove all team configs from Superset
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


# ============================================================
# Configuration (matches existing scripts)
# ============================================================

# ClickHouse (Docker internal hostname, same as setup_superset_dashboards.py)
CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_PORT = 8123

# Shared database name in Superset (created by setup_superset_dashboards.py)
SHARED_DB_NAME = "ClickHouse Game Analytics"
SHARED_DB_USER = "superset"
SHARED_DB_PASSWORD = "superset123"
SHARED_DB_DATABASE = "game_analytics"

# Docker container name (from docker-compose.yml)
SUPERSET_CONTAINER = "superset"

# Default Superset URL (for credentials output only, not used for API)
SUPERSET_URL = "http://localhost:8088"


# ============================================================
# Helpers
# ============================================================

def team_name(i: int) -> str:
    """Generate team name like team_01, team_02, ..."""
    return f"team_{i:02d}"


def team_display_name(i: int) -> str:
    """Generate display name like 'Team 01'."""
    return f"Team {i:02d}"


def run_in_container(script: str, timeout: int = 180) -> bool:
    """Execute a Python script inside the Superset Docker container via stdin."""
    result = subprocess.run(
        ["docker", "exec", "-i", SUPERSET_CONTAINER, "python"],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        # Filter out common noisy warnings
        stderr_lines = [
            line for line in result.stderr.splitlines()
            if not any(w in line for w in [
                "WARNING", "DeprecationWarning", "UserWarning",
                "SAWarning", "RemovedIn", "pkg_resources",
            ])
        ]
        if stderr_lines:
            print("STDERR:", "\n".join(stderr_lines))
    return result.returncode == 0


# ============================================================
# Setup script (runs inside Superset container)
# ============================================================

def generate_setup_script(
    num_teams: int,
    ch_password_prefix: str,
    superset_password_prefix: str,
) -> str:
    """
    Generate Python script to run inside the Superset container.
    Creates database connections, roles, and users — all via SQLAlchemy + FAB.
    """
    teams_config = []
    for i in range(1, num_teams + 1):
        name = team_name(i)
        display = team_display_name(i)
        teams_config.append({
            "team_name": name,
            "role_name": f"{name}_role",
            "display_name": display,
            "ch_username": name,
            "ch_password": f"{ch_password_prefix}{i:02d}",
            "ch_database": name,
            "superset_username": name,
            "superset_password": f"{superset_password_prefix}{i:02d}",
            "email": f"{name}@course.local",
        })

    teams_json = json.dumps(teams_config, ensure_ascii=False)

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
    from superset.models.core import Database as DatabaseModel
    session = sdb.session
    sm = app.appbuilder.sm

    teams = json.loads("""{teams_json}""")

    CLICKHOUSE_HOST = "{CLICKHOUSE_HOST}"
    CLICKHOUSE_PORT = {CLICKHOUSE_PORT}
    SHARED_DB_NAME = "{SHARED_DB_NAME}"
    SHARED_DB_USER = "{SHARED_DB_USER}"
    SHARED_DB_PASSWORD = "{SHARED_DB_PASSWORD}"
    SHARED_DB_DATABASE = "{SHARED_DB_DATABASE}"

    # ---- Phase 1: Database connections ----
    print("=== Phase 1: Database connections ===")

    # Get existing connections
    existing_dbs = {{d.database_name: d for d in session.query(DatabaseModel).all()}}
    print(f"  Found {{len(existing_dbs)}} existing connections")

    # Ensure shared game_analytics connection
    shared_db = None
    if SHARED_DB_NAME in existing_dbs:
        shared_db = existing_dbs[SHARED_DB_NAME]
        print(f"  [shared] Already exists (id={{shared_db.id}})")
    else:
        # Look for any game_analytics connection
        for name, db_obj in existing_dbs.items():
            if "game_analytics" in name.lower() or "game analytics" in name.lower():
                shared_db = db_obj
                print(f"  [shared] Found as '{{name}}' (id={{shared_db.id}})")
                break
        if not shared_db:
            # Create it
            shared_db = DatabaseModel(
                database_name=SHARED_DB_NAME,
                sqlalchemy_uri=f"clickhousedb://{{SHARED_DB_USER}}:{{SHARED_DB_PASSWORD}}@{{CLICKHOUSE_HOST}}:{{CLICKHOUSE_PORT}}/{{SHARED_DB_DATABASE}}",
                expose_in_sqllab=True,
                allow_run_async=True,
                allow_ctas=False,
                allow_cvas=False,
                allow_dml=False,
            )
            session.add(shared_db)
            session.flush()
            print(f"  [shared] Created (id={{shared_db.id}})")

    # Create per-team database connections
    team_dbs = {{}}
    for team in teams:
        display = team["display_name"]
        if display in existing_dbs:
            team_dbs[team["team_name"]] = existing_dbs[display]
            print(f"  [{{team['team_name']}}] Already exists (id={{existing_dbs[display].id}})")
            continue

        db_obj = DatabaseModel(
            database_name=display,
            sqlalchemy_uri=f"clickhousedb://{{team['ch_username']}}:{{team['ch_password']}}@{{CLICKHOUSE_HOST}}:{{CLICKHOUSE_PORT}}/{{team['ch_database']}}",
            expose_in_sqllab=True,
            allow_run_async=True,
            allow_ctas=False,
            allow_cvas=False,
            allow_dml=False,
        )
        session.add(db_obj)
        session.flush()  # Get the id
        team_dbs[team["team_name"]] = db_obj
        print(f"  [{{team['team_name']}}] Created '{{display}}' (id={{db_obj.id}})")

    session.commit()
    print(f"  Database connections ready: {{len(team_dbs)}} teams + 1 shared")

    # Refresh permissions so database_access entries are created
    print("\\n  Syncing permissions...")
    sm.sync_role_definitions()

    # ---- Phase 2: Roles and users ----
    print("\\n=== Phase 2: Roles and users ===")

    gamma_role = sm.find_role("Gamma")
    if not gamma_role:
        print("ERROR: Gamma role not found!")
        sys.exit(1)
    print(f"  Found Gamma role (id={{gamma_role.id}})")

    # Discover all database_access permissions
    from flask_appbuilder.security.sqla.models import PermissionView, Permission, ViewMenu
    all_db_access = {{}}
    perm_obj = session.query(Permission).filter_by(name="database_access").first()
    if perm_obj:
        pvs = session.query(PermissionView).filter_by(permission_id=perm_obj.id).all()
        for pv in pvs:
            all_db_access[pv.view_menu.name] = pv
    print(f"  Found {{len(all_db_access)}} database_access permissions")
    for name in sorted(all_db_access.keys()):
        print(f"    {{name}}")

    # SQL Lab permissions (exact names from this Superset 3.1.0 instance)
    SQLLAB_PERMS = [
        # Menu visibility
        ("menu_access", "SQL Lab"),
        ("menu_access", "SQL Editor"),
        ("menu_access", "Query Search"),
        ("menu_access", "Saved Queries"),
        # SQL Lab core
        ("can_read", "SQLLab"),
        ("can_execute_sql_query", "SQLLab"),
        ("can_get_results", "SQLLab"),
        ("can_estimate_query_cost", "SQLLab"),
        ("can_export_csv", "SQLLab"),
        ("can_format_sql", "SQLLab"),
        ("can_my_queries", "SqlLab"),
        ("can_sqllab", "Superset"),
        ("can_sqllab_history", "Superset"),
        # TabStateView — required for SQL Lab tabs to work
        ("can_activate", "TabStateView"),
        ("can_get", "TabStateView"),
        ("can_post", "TabStateView"),
        ("can_put", "TabStateView"),
        ("can_delete", "TabStateView"),
        ("can_migrate_query", "TabStateView"),
        ("can_delete_query", "TabStateView"),
        # TableSchemaView — for schema browser in SQL Lab
        ("can_delete", "TableSchemaView"),
        ("can_expanded", "TableSchemaView"),
        ("can_post", "TableSchemaView"),
        # Queries
        ("can_read", "Query"),
        ("can_read", "SavedQuery"),
        ("can_write", "SavedQuery"),
        ("can_list", "SavedQuery"),
        ("can_export", "SavedQuery"),
        # Database visibility
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
        added = 0
        for perm_name, view_name in SQLLAB_PERMS:
            pv = sm.find_permission_view_menu(perm_name, view_name)
            if pv:
                sm.add_permission_role(role, pv)
                added += 1
            else:
                print(f"  WARN: '{{perm_name}}' on '{{view_name}}' not found")
        print(f"  Added {{added}}/{{len(SQLLAB_PERMS)}} SQL Lab permissions")

        # 3. Add database_access for team's own DB
        team_db = team_dbs.get(team["team_name"])
        if team_db:
            # Find the matching permission by checking all db_access perms
            found = False
            for perm_view_name, pv in all_db_access.items():
                if f"(id:{{team_db.id}})" in perm_view_name:
                    sm.add_permission_role(role, pv)
                    print(f"  Granted: database_access on {{perm_view_name}}")
                    found = True
                    break
            if not found:
                print(f"  WARN: No database_access permission found for id={{team_db.id}}")

        # 4. Add database_access for shared DB
        if shared_db:
            found = False
            for perm_view_name, pv in all_db_access.items():
                if f"(id:{{shared_db.id}})" in perm_view_name:
                    sm.add_permission_role(role, pv)
                    print(f"  Granted: database_access on {{perm_view_name}}")
                    found = True
                    break
            if not found:
                print(f"  WARN: No database_access permission found for shared db id={{shared_db.id}}")

        # 5. Create or update user
        user = sm.find_user(username=team["superset_username"])
        if user:
            user.roles = [gamma_role, role]
            session.commit()
            print(f"  User exists, updated roles: {{team['superset_username']}}")
        else:
            user = sm.add_user(
                username=team["superset_username"],
                first_name=team["display_name"],
                last_name="Student",
                email=team["email"],
                role=gamma_role,
                password=team["superset_password"],
            )
            if user:
                user.roles = [gamma_role, role]
                session.commit()
                print(f"  Created user: {{team['superset_username']}}")
            else:
                print(f"  FAILED to create user: {{team['superset_username']}}")

    session.commit()
    print("\\n=== All teams configured successfully! ===")
'''
    return script


def generate_drop_script(num_teams: int) -> str:
    """Generate Python script to remove team users, roles, and DB connections."""
    teams = []
    for i in range(1, num_teams + 1):
        teams.append({
            "name": team_name(i),
            "display": team_display_name(i),
        })
    teams_json = json.dumps(teams)

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
    from superset.models.core import Database as DatabaseModel
    session = sdb.session
    sm = app.appbuilder.sm

    teams = json.loads("""{teams_json}""")

    for team in teams:
        name = team["name"]
        display = team["display"]

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

        # Delete database connection
        db_obj = session.query(DatabaseModel).filter_by(database_name=display).first()
        if db_obj:
            session.delete(db_obj)
            print(f"  Deleted database connection: {{display}}")
        else:
            print(f"  DB connection not found: {{display}}")

    session.commit()
    print("\\nCleanup complete!")
'''
    return script


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
        default=18,
        help="Number of teams (default: 18)",
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
        help=f"Superset URL for credentials file (default: {SUPERSET_URL})",
    )
    parser.add_argument(
        "--container",
        default=SUPERSET_CONTAINER,
        help=f"Superset Docker container name (default: {SUPERSET_CONTAINER})",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Remove all team users, roles, and database connections",
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

        script = generate_drop_script(args.teams)
        success = run_in_container(script)
        if not success:
            print("\nERROR: Cleanup failed!")
            sys.exit(1)
        return

    # --setup mode (default)
    print("=" * 60)
    print("Setting up Superset team isolation")
    print(f"Teams: {args.teams}")
    print("=" * 60)

    script = generate_setup_script(
        args.teams,
        args.clickhouse_password_prefix,
        args.superset_password_prefix,
    )
    success = run_in_container(script)

    if not success:
        print("\nERROR: Setup failed!")
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

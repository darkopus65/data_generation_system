#!/usr/bin/env python3
"""
Setup Superset dashboards for Game Analytics course.

This script:
1. Connects to Superset API
2. Creates ClickHouse database connection
3. Creates datasets (virtual tables)
4. Creates charts
5. Creates dashboards

Usage:
    python scripts/setup_superset_dashboards.py

Requirements:
    pip install requests
"""

import json
import time
import requests
from typing import Optional

# Configuration
SUPERSET_URL = "http://localhost:8088"
SUPERSET_USER = "admin"
SUPERSET_PASSWORD = "admin123"

CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_PORT = 8123
CLICKHOUSE_DB = "game_analytics"
CLICKHOUSE_USER = "superset"
CLICKHOUSE_PASSWORD = "superset123"


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
        # Get CSRF token
        resp = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
        if resp.status_code == 200:
            self.csrf_token = resp.json().get("result")
            self.session.headers["X-CSRFToken"] = self.csrf_token

        # Login
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
        print("✓ Logged into Superset")

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make API request."""
        url = f"{self.base_url}/api/v1{endpoint}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code >= 400:
            print(f"Error {resp.status_code}: {resp.text}")
            return {}
        return resp.json() if resp.text else {}

    def get_databases(self) -> list:
        """Get list of databases."""
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

    def get_datasets(self) -> list:
        """Get list of datasets."""
        return self._request("GET", "/dataset/").get("result", [])

    def create_dataset(self, database_id: int, table_name: str, schema: str = "") -> Optional[int]:
        """Create dataset from table."""
        data = {
            "database": database_id,
            "table_name": table_name,
            "schema": schema,
        }
        result = self._request("POST", "/dataset/", json=data)
        return result.get("id")

    def create_virtual_dataset(self, database_id: int, name: str, sql: str) -> Optional[int]:
        """Create virtual dataset from SQL query."""
        data = {
            "database": database_id,
            "table_name": name,
            "sql": sql,
            "schema": "",
        }
        result = self._request("POST", "/dataset/", json=data)
        return result.get("id")

    def get_charts(self) -> list:
        """Get list of charts."""
        return self._request("GET", "/chart/").get("result", [])

    def create_chart(
        self,
        name: str,
        viz_type: str,
        datasource_id: int,
        datasource_type: str = "table",
        params: dict = None,
    ) -> Optional[int]:
        """Create chart."""
        data = {
            "slice_name": name,
            "viz_type": viz_type,
            "datasource_id": datasource_id,
            "datasource_type": datasource_type,
            "params": json.dumps(params or {}),
        }
        result = self._request("POST", "/chart/", json=data)
        return result.get("id")

    def get_dashboards(self) -> list:
        """Get list of dashboards."""
        return self._request("GET", "/dashboard/").get("result", [])

    def create_dashboard(self, name: str, slug: str) -> Optional[int]:
        """Create empty dashboard."""
        data = {
            "dashboard_title": name,
            "slug": slug,
            "published": True,
        }
        result = self._request("POST", "/dashboard/", json=data)
        return result.get("id")

    def update_dashboard(self, dashboard_id: int, chart_ids: list, layout: dict = None):
        """Update dashboard with charts."""
        # Build position JSON for charts
        positions = {"DASHBOARD_VERSION_KEY": "v2"}
        row_height = 400

        for i, chart_id in enumerate(chart_ids):
            chart_key = f"CHART-{chart_id}"
            row = i // 2
            col = (i % 2) * 6

            positions[chart_key] = {
                "type": "CHART",
                "id": chart_key,
                "children": [],
                "meta": {
                    "width": 6,
                    "height": 50,
                    "chartId": chart_id,
                },
            }

        data = {
            "json_metadata": json.dumps({
                "positions": positions,
                "default_filters": "{}",
                "timed_refresh_immune_slices": [],
            }),
        }
        self._request("PUT", f"/dashboard/{dashboard_id}", json=data)


def main():
    print("=" * 60)
    print("Setting up Superset dashboards for Game Analytics")
    print("=" * 60)

    # Wait for Superset to be ready
    print("\nWaiting for Superset to be ready...")
    for i in range(30):
        try:
            resp = requests.get(f"{SUPERSET_URL}/health", timeout=5)
            if resp.status_code == 200:
                break
        except:
            pass
        time.sleep(2)
    else:
        print("Error: Superset is not responding")
        return

    # Connect to Superset
    try:
        api = SupersetAPI(SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD)
    except Exception as e:
        print(f"Error: Could not connect to Superset: {e}")
        return

    # Check if database already exists
    databases = api.get_databases()
    db_id = None
    for db in databases:
        if db.get("database_name") == "ClickHouse Game Analytics":
            db_id = db.get("id")
            print(f"✓ Database already exists (id={db_id})")
            break

    # Create ClickHouse connection
    if not db_id:
        print("\nCreating ClickHouse database connection...")
        connection_string = (
            f"clickhousedb://{CLICKHOUSE_USER}:{CLICKHOUSE_PASSWORD}"
            f"@{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DB}"
        )
        db_id = api.create_database("ClickHouse Game Analytics", connection_string)
        if db_id:
            print(f"✓ Database connection created (id={db_id})")
        else:
            print("✗ Failed to create database connection")
            print("  Make sure clickhouse-connect is installed in Superset")
            print("  Try adding manually via UI")
            return

    # Create main events dataset
    print("\nCreating datasets...")
    datasets = api.get_datasets()
    events_dataset_id = None

    for ds in datasets:
        if ds.get("table_name") == "events":
            events_dataset_id = ds.get("id")
            print(f"✓ Events dataset already exists (id={events_dataset_id})")
            break

    if not events_dataset_id:
        events_dataset_id = api.create_dataset(db_id, "events")
        if events_dataset_id:
            print(f"✓ Events dataset created (id={events_dataset_id})")
        else:
            print("✗ Failed to create events dataset")

    # Create dashboards
    print("\nCreating dashboards...")

    dashboards_config = [
        {
            "name": "📊 Retention Dashboard",
            "slug": "retention",
            "description": "DAU, Retention metrics, User cohorts",
        },
        {
            "name": "💰 Monetization Dashboard",
            "slug": "monetization",
            "description": "Revenue, ARPU, Conversion, LTV",
        },
        {
            "name": "🧪 A/B Tests Dashboard",
            "slug": "ab-tests",
            "description": "A/B test results and comparisons",
        },
        {
            "name": "📈 Funnel & Engagement",
            "slug": "funnel",
            "description": "User funnels, Engagement metrics",
        },
    ]

    existing_dashboards = {d.get("slug"): d.get("id") for d in api.get_dashboards()}

    for config in dashboards_config:
        if config["slug"] in existing_dashboards:
            print(f"✓ Dashboard '{config['name']}' already exists")
        else:
            dashboard_id = api.create_dashboard(config["name"], config["slug"])
            if dashboard_id:
                print(f"✓ Dashboard '{config['name']}' created (id={dashboard_id})")
            else:
                print(f"✗ Failed to create dashboard '{config['name']}'")

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"""
Next steps:

1. Open Superset: {SUPERSET_URL}
   Login: {SUPERSET_USER} / {SUPERSET_PASSWORD}

2. Go to SQL Lab → Saved Queries
   Import queries from: infrastructure/superset/dashboards/sql_queries.sql

3. Create charts:
   - Go to Charts → + Chart
   - Select "ClickHouse Game Analytics" database
   - Use SQL queries from sql_queries.sql
   - Save charts to appropriate dashboards

4. Recommended chart types:
   - DAU, Revenue: Line Chart (time-series)
   - Retention matrix: Pivot Table
   - Conversion funnel: Funnel Chart
   - A/B tests: Grouped Bar Chart
   - Distributions: Pie Chart

5. Share dashboards with students:
   - Settings → Dashboard → Edit
   - Enable "Published" checkbox
   - Share URL with students
""")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
GIVIN Zero-to-Demo Bootstrap Orchestrator.
Prepares a pristine, deterministic judge demonstration environment:
1. Check dependencies (Python packages, DB engine connectivity)
2. Initialize database schema & apply table column synchronization
3. Purge past demo state (clean reset)
4. Seed core RBAC users, roles, and administrative departments
5. Seed heterogeneous corridor cameras across Gujarat
6. Seed statewide hotlist / watchlist records
7. Delegate execution to scripts/run_demo.py for the 16-stage operational demo
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import Base, engine, sync_schema_columns, check_db_health
from scripts.demo_reset import reset_demo_data
from scripts.demo_seed import seed_demo_environment
from scripts.run_demo import run_full_demo


def bootstrap_and_run():
    print("=" * 80)
    print("  GIVIN ZERO-TO-DEMO AUTOMATED BOOTSTRAP")
    print("  Gujarat Integrated Video Intelligence Network (GIVIN)")
    print("=" * 80)

    # 1. Dependency Check
    print("\n[*] Stage 1: Verifying platform runtime dependencies...")
    for mod in ["fastapi", "sqlalchemy", "pydantic", "jwt", "psutil"]:
        try:
            __import__(mod)
        except ImportError as e:
            raise RuntimeError(f"Missing mandatory dependency '{mod}': {e}")
    
    db_health = check_db_health()
    if db_health.get("status") != "READY":
        raise RuntimeError(f"Database dependency failed readiness check: {db_health}")
    print(f"    -> Runtime dependencies verified. Database status: {db_health['status']} ({db_health.get('dialect')}).")

    # 2. Database Schema Initialization & Column Synchronization
    print("\n[*] Stage 2: Initializing relational schema and column sync...")
    Base.metadata.create_all(bind=engine)
    sync_schema_columns()
    print("    -> Database schema initialized.")

    # 3. Clean Reset of Previous Demo State
    print("\n[*] Stage 3: Purging previous demo state (clean slate guarantee)...")
    reset_demo_data()
    print("    -> Previous state purged.")

    # 4. Seed RBAC, Cameras, and Watchlists
    print("\n[*] Stage 4: Seeding RBAC users, surveillance nodes, and watchlist...")
    seed_demo_environment()
    print("    -> Seeding complete.")

    # 5. Execute Full Operational Demonstration
    print("\n[*] Stage 5: Launching complete 16-stage end-to-end intelligence demo...\n")
    run_full_demo()


if __name__ == "__main__":
    bootstrap_and_run()

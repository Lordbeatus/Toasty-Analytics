#!/usr/bin/env python3
"""
Database migration script for splitting monolithic database into microservice databases

Usage:
    python migrate_databases.py [--verify]

Options:
    --verify    Only verify migration without performing it
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.database_splitter import (
    DatabaseSplitter,
    generate_migration_docker_compose,
)

# Database URLs
MONOLITH_URL = os.getenv(
    "MONOLITH_DB_URL", "postgresql://toasty:toasty_pass@localhost:5432/toastyanalytics"
)
SERVICE_DB_PATTERN = "postgresql://toasty:toasty_pass@localhost:{port}/{service}_db"

# Port mapping for services
SERVICE_PORTS = {
    "user-service": 5433,
    "grading-service": 5434,
    "meta-learning-service": 5435,
    "analytics-service": 5436,
}


def main():
    verify_only = "--verify" in sys.argv

    print("=" * 60)
    print("ToastyAnalytics Database Migration Tool")
    print("=" * 60)

    # Create splitter
    splitter = DatabaseSplitter(MONOLITH_URL)

    try:
        splitter.connect_monolith()
    except Exception as e:
        print(f"\n❌ Failed to connect to monolith database: {e}")
        print("\nMake sure the database is running and credentials are correct.")
        print("You can start the databases with:\n")
        print("  cd deployment/docker")
        print("  docker-compose -f docker-compose.split-db.yml up -d")
        return 1

    # Setup service databases
    base_pattern = "postgresql://toasty:toasty_pass@localhost/{service}_db"
    splitter.setup_service_databases(base_pattern)

    if verify_only:
        print("\n📊 Verifying migration...")
        print("-" * 60)

        try:
            results = splitter.verify_migration()

            all_match = True
            for service, tables in results.items():
                print(f"\n{service}:")
                for table, counts in tables.items():
                    status = "✅" if counts["match"] else "❌"
                    if not counts["match"]:
                        all_match = False
                    print(
                        f"  {status} {table}: {counts['service']}/{counts['monolith']} rows"
                    )

            if all_match:
                print("\n✅ All tables match! Migration successful.")
                return 0
            else:
                print("\n❌ Some tables don't match. Review migration.")
                return 1

        except Exception as e:
            print(f"\n❌ Verification failed: {e}")
            return 1
    else:
        print("\n🚀 Starting migration...")
        print("-" * 60)
        print("This will:")
        print("  1. Connect to monolithic database")
        print("  2. Create tables in service databases")
        print("  3. Copy data to service-specific databases")
        print("\n⚠️  Make sure you have backups before proceeding!")

        response = input("\nContinue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Migration cancelled.")
            return 0

        try:
            splitter.migrate_all()
            print("\n✅ Migration complete! Run with --verify to check results.")
            return 0
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())

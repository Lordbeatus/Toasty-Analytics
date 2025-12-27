"""
Database Migration Utilities for Microservices

Provides tools for splitting the monolithic database into service-specific databases.
Supports data migration, schema replication, and cross-service queries.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import MetaData, Table, create_engine, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


class ServiceDatabase:
    """Represents a database for a specific microservice"""

    def __init__(self, service_name: str, db_url: str, tables: List[str]):
        """
        Initialize service database.

        Args:
            service_name: Name of the microservice
            db_url: Database connection URL
            tables: List of table names owned by this service
        """
        self.service_name = service_name
        self.db_url = db_url
        self.tables = tables
        self.engine: Optional[Engine] = None
        self.metadata: Optional[MetaData] = None
        self.session_maker: Optional[sessionmaker] = None

    def connect(self):
        """Establish database connection"""
        self.engine = create_engine(self.db_url, echo=False)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
        logger.info(f"Connected to {self.service_name} database")

    def get_session(self) -> Session:
        """Get a new database session"""
        if not self.session_maker:
            self.connect()
        if not self.session_maker:
            raise RuntimeError("Failed to create session maker")
        return self.session_maker()


class DatabaseSplitter:
    """
    Manages the split of monolithic database into microservice databases.

    Strategy:
    1. Create separate databases for each microservice
    2. Migrate relevant tables to each database
    3. Set up foreign key relationships within service boundaries
    4. Implement API calls for cross-service data access
    """

    # Define table ownership for each microservice
    SERVICE_TABLE_MAPPING = {
        "grading-service": ["grading_history", "grading_dimensions", "grading_results"],
        "meta-learning-service": [
            "learning_strategies",
            "user_feedback",
            "pattern_analysis",
            "collective_learning",
        ],
        "analytics-service": ["user_statistics", "aggregate_metrics", "trend_analysis"],
        "user-service": [  # New service for user management
            "users",
            "agents",
            "api_keys",
        ],
    }

    def __init__(self, monolith_url: str):
        """
        Initialize database splitter.

        Args:
            monolith_url: Connection URL for monolithic database
        """
        self.monolith_url = monolith_url
        self.monolith_engine: Optional[Engine] = None
        self.monolith_metadata: Optional[MetaData] = None
        self.service_databases: Dict[str, ServiceDatabase] = {}

    def connect_monolith(self):
        """Connect to monolithic database"""
        self.monolith_engine = create_engine(self.monolith_url, echo=False)
        self.monolith_metadata = MetaData()
        self.monolith_metadata.reflect(bind=self.monolith_engine)
        logger.info("Connected to monolithic database")

    def setup_service_databases(self, base_url_pattern: str):
        """
        Set up separate databases for each microservice.

        Args:
            base_url_pattern: URL pattern with {service} placeholder
                              Example: "postgresql://user:pass@localhost/{service}_db"
        """
        for service_name, tables in self.SERVICE_TABLE_MAPPING.items():
            # Replace {service} with actual service name
            db_url = base_url_pattern.format(service=service_name.replace("-", "_"))

            # Create service database
            service_db = ServiceDatabase(
                service_name=service_name, db_url=db_url, tables=tables
            )

            self.service_databases[service_name] = service_db
            logger.info(f"Configured database for {service_name}: {len(tables)} tables")

    def migrate_table(
        self, table_name: str, source_session: Session, target_session: Session
    ) -> int:
        """
        Migrate data from monolith table to service database.

        Args:
            table_name: Name of table to migrate
            source_session: Session for source database
            target_session: Session for target database

        Returns:
            Number of rows migrated
        """
        # Get table from monolith metadata
        if not self.monolith_metadata:
            raise RuntimeError("Monolith metadata not initialized")
        source_table = self.monolith_metadata.tables[table_name]

        # Read all data from source
        result = source_session.execute(select(source_table))
        rows = result.fetchall()

        if not rows:
            logger.info(f"No data to migrate for table: {table_name}")
            return 0

        # Get target table (should already exist with same schema)
        target_table = Table(table_name, MetaData(), autoload_with=target_session.bind)

        # Convert rows to dicts
        row_dicts = [dict(row._mapping) for row in rows]

        # Insert into target
        target_session.execute(insert(target_table), row_dicts)
        target_session.commit()

        logger.info(f"Migrated {len(rows)} rows for table: {table_name}")
        return len(rows)

    def migrate_all(self):
        """
        Migrate all tables to their respective service databases.
        """
        if not self.monolith_engine:
            self.connect_monolith()

        # Connect all service databases
        for service_db in self.service_databases.values():
            service_db.connect()

        # Create sessions
        monolith_session = Session(self.monolith_engine)

        total_migrated = 0

        try:
            # Migrate each service's tables
            for service_name, service_db in self.service_databases.items():
                service_session = service_db.get_session()

                logger.info(f"\nMigrating tables for {service_name}...")

                for table_name in service_db.tables:
                    try:
                        count = self.migrate_table(
                            table_name, monolith_session, service_session
                        )
                        total_migrated += count
                    except Exception as e:
                        logger.error(f"Failed to migrate {table_name}: {e}")

                service_session.close()

            logger.info(
                f"\n✅ Migration complete! Migrated {total_migrated} total rows"
            )

        finally:
            monolith_session.close()

    def verify_migration(self) -> Dict[str, Dict[str, int]]:
        """
        Verify migration by comparing row counts.

        Returns:
            Dict mapping service -> table -> row count
        """
        results = {}

        monolith_session = Session(self.monolith_engine)

        try:
            for service_name, service_db in self.service_databases.items():
                service_session = service_db.get_session()
                service_results = {}

                for table_name in service_db.tables:
                    # Count in monolith
                    if not self.monolith_metadata:
                        continue
                    monolith_table = self.monolith_metadata.tables[table_name]
                    monolith_count = monolith_session.execute(
                        select(monolith_table).count()
                    ).scalar()

                    # Count in service database
                    service_table = Table(
                        table_name, MetaData(), autoload_with=service_session.bind
                    )
                    service_count = service_session.execute(
                        select(service_table).count()
                    ).scalar()

                    service_results[table_name] = {
                        "monolith": monolith_count,
                        "service": service_count,
                        "match": monolith_count == service_count,
                    }

                results[service_name] = service_results
                service_session.close()

        finally:
            monolith_session.close()

        return results


def generate_migration_docker_compose() -> str:
    """
    Generate docker-compose.yml for split databases.

    Returns:
        YAML content for docker-compose.yml
    """
    return """version: '3.8'

services:
  # User Service Database
  user-db:
    image: postgres:15
    environment:
      POSTGRES_DB: user_service_db
      POSTGRES_USER: toasty
      POSTGRES_PASSWORD: toasty_pass
    ports:
      - "5433:5432"
    volumes:
      - user_db_data:/var/lib/postgresql/data
  
  # Grading Service Database
  grading-db:
    image: postgres:15
    environment:
      POSTGRES_DB: grading_service_db
      POSTGRES_USER: toasty
      POSTGRES_PASSWORD: toasty_pass
    ports:
      - "5434:5432"
    volumes:
      - grading_db_data:/var/lib/postgresql/data
  
  # Meta-Learning Service Database
  meta-learning-db:
    image: postgres:15
    environment:
      POSTGRES_DB: meta_learning_service_db
      POSTGRES_USER: toasty
      POSTGRES_PASSWORD: toasty_pass
    ports:
      - "5435:5432"
    volumes:
      - meta_learning_db_data:/var/lib/postgresql/data
  
  # Analytics Service Database
  analytics-db:
    image: postgres:15
    environment:
      POSTGRES_DB: analytics_service_db
      POSTGRES_USER: toasty
      POSTGRES_PASSWORD: toasty_pass
    ports:
      - "5436:5432"
    volumes:
      - analytics_db_data:/var/lib/postgresql/data

volumes:
  user_db_data:
  grading_db_data:
  meta_learning_db_data:
  analytics_db_data:
"""


def generate_migration_script() -> str:
    """
    Generate Python script to run migration.

    Returns:
        Python code for migration script
    """
    return """#!/usr/bin/env python3
\"\"\"
Database migration script

Usage:
    python migrate_databases.py [--verify]

Options:
    --verify    Only verify migration without performing it
\"\"\"

import sys
from src.database.database_splitter import DatabaseSplitter, generate_migration_docker_compose

# Database URLs
MONOLITH_URL = "postgresql://toasty:toasty_pass@localhost:5432/toastyanalytics"
SERVICE_DB_PATTERN = "postgresql://toasty:toasty_pass@localhost:{port}/{service}_db"

# Port mapping for services
SERVICE_PORTS = {
    "user-service": 5433,
    "grading-service": 5434,
    "meta-learning-service": 5435,
    "analytics-service": 5436
}


def main():
    verify_only = "--verify" in sys.argv
    
    # Create splitter
    splitter = DatabaseSplitter(MONOLITH_URL)
    splitter.connect_monolith()
    
    # Setup service databases
    for service, port in SERVICE_PORTS.items():
        url = SERVICE_DB_PATTERN.format(
            port=port,
            service=service.replace("-", "_")
        )
        splitter.setup_service_databases(url)
    
    if verify_only:
        print("Verifying migration...")
        results = splitter.verify_migration()
        
        for service, tables in results.items():
            print(f"\\n{service}:")
            for table, counts in tables.items():
                status = "✅" if counts["match"] else "❌"
                print(f"  {status} {table}: {counts['service']}/{counts['monolith']}")
    else:
        print("Starting migration...")
        splitter.migrate_all()
        print("\\nMigration complete! Run with --verify to check results.")


if __name__ == "__main__":
    main()
"""


# Example usage
if __name__ == "__main__":
    # Generate docker-compose for split databases
    docker_compose = generate_migration_docker_compose()
    print("Docker Compose for split databases:")
    print(docker_compose)

    # Example migration
    splitter = DatabaseSplitter("postgresql://user:pass@localhost/toastyanalytics")
    splitter.setup_service_databases("postgresql://user:pass@localhost/{service}_db")
    # splitter.migrate_all()  # Uncomment to run migration

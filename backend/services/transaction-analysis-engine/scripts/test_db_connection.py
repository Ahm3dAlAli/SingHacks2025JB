#!/usr/bin/env python3
"""
Database Connectivity Test Script for TAE
Tests PostgreSQL connection and validates schema setup
"""

import os
import sys
from typing import Dict, List
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message: str):
    print(f"{GREEN}✓{RESET} {message}")

def print_error(message: str):
    print(f"{RED}✗{RESET} {message}")

def print_info(message: str):
    print(f"{BLUE}ℹ{RESET} {message}")

def print_warning(message: str):
    print(f"{YELLOW}⚠{RESET} {message}")

def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'aml_monitoring'),
        'user': os.getenv('POSTGRES_USER', 'tae_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'tae_password_change_me')
    }

def test_connection() -> psycopg2.extensions.connection:
    """Test database connection"""
    print_info("Testing database connection...")

    config = get_db_config()
    print(f"  Host: {config['host']}:{config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")

    try:
        conn = psycopg2.connect(**config)
        print_success("Database connection successful!")
        return conn
    except psycopg2.Error as e:
        print_error(f"Database connection failed: {e}")
        sys.exit(1)

def test_tables(conn: psycopg2.extensions.connection) -> List[str]:
    """Check if all required tables exist"""
    print_info("Checking database tables...")

    required_tables = [
        'transactions',
        'risk_assessments',
        'agent_execution_logs',
        'audit_trail',
        'regulatory_rules'
    ]

    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)

    existing_tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    print(f"  Found {len(existing_tables)} tables")

    missing_tables = []
    for table in required_tables:
        if table in existing_tables:
            print_success(f"Table '{table}' exists")
        else:
            print_error(f"Table '{table}' is missing!")
            missing_tables.append(table)

    return missing_tables

def test_seed_data(conn: psycopg2.extensions.connection):
    """Check if seed data was loaded"""
    print_info("Checking seed data...")

    cursor = conn.cursor()

    # Check regulatory_rules
    cursor.execute("SELECT COUNT(*) FROM regulatory_rules;")
    rule_count = cursor.fetchone()[0]

    if rule_count >= 15:
        print_success(f"Found {rule_count} regulatory rules (expected 15)")
    else:
        print_warning(f"Only found {rule_count} regulatory rules (expected 15)")

    # Count by jurisdiction
    cursor.execute("""
        SELECT jurisdiction, COUNT(*)
        FROM regulatory_rules
        GROUP BY jurisdiction
        ORDER BY jurisdiction;
    """)

    print("  Breakdown by jurisdiction:")
    for jurisdiction, count in cursor.fetchall():
        print(f"    - {jurisdiction}: {count} rules")

    cursor.close()

def test_indexes(conn: psycopg2.extensions.connection):
    """Check if indexes are created"""
    print_info("Checking database indexes...")

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            schemaname,
            tablename,
            indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """)

    indexes = cursor.fetchall()
    index_count = len(indexes)

    if index_count > 0:
        print_success(f"Found {index_count} indexes")

        # Group by table
        table_indexes = {}
        for schema, table, index in indexes:
            if table not in table_indexes:
                table_indexes[table] = []
            table_indexes[table].append(index)

        for table, idx_list in table_indexes.items():
            print(f"  {table}: {len(idx_list)} indexes")
    else:
        print_warning("No indexes found")

    cursor.close()

def test_schema_details(conn: psycopg2.extensions.connection):
    """Get detailed schema information"""
    print_info("Database schema validation...")

    cursor = conn.cursor()

    # Check transactions table columns
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'transactions'
        ORDER BY ordinal_position;
    """)

    columns = cursor.fetchall()
    print_success(f"'transactions' table has {len(columns)} columns")

    cursor.close()

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("TAE Database Connectivity Test")
    print("="*60 + "\n")

    # Test connection
    conn = test_connection()
    print()

    # Test tables
    missing_tables = test_tables(conn)
    print()

    if missing_tables:
        print_error(f"Schema incomplete! Missing tables: {', '.join(missing_tables)}")
        conn.close()
        sys.exit(1)

    # Test seed data
    test_seed_data(conn)
    print()

    # Test indexes
    test_indexes(conn)
    print()

    # Schema details
    test_schema_details(conn)
    print()

    # Close connection
    conn.close()

    print("="*60)
    print_success("All database tests passed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

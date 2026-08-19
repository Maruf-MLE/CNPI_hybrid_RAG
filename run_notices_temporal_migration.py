"""
Run Notices Table Migration
============================

Adds temporal_analysis column to the notices table.

Usage:
    cd G:\CNPI_Hybrid_RAG
    python run_notices_temporal_migration.py
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("  SQL Migration: Add temporal_analysis to Notices Table")
print("=" * 70)
print()

# Read SQL file
sql_file = Path(__file__).resolve().parent / "Cnpi_RAG" / "database" / "add_notices_temporal_column.sql"

if not sql_file.exists():
    print(f"❌ SQL file not found: {sql_file}")
    sys.exit(1)

print(f"Reading SQL file: {sql_file.name}")
with open(sql_file, "r", encoding="utf-8") as f:
    sql_script = f.read()

print("✅ SQL script loaded")
print()

# Connect to database
print("Connecting to database...")
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432"),
    )
    print(f"✅ Connected to {os.getenv('DB_NAME')} on {os.getenv('DB_HOST')}")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

print()
print("Running migration on NOTICES table...")
print("-" * 70)

try:
    cursor = conn.cursor()
    cursor.execute(sql_script)
    conn.commit()
    
    # Print all notices from the migration
    print()
    for notice in conn.notices:
        print(f"  {notice.strip()}")
    
    cursor.close()
    conn.close()
    
    print()
    print("-" * 70)
    print("✅ Migration completed successfully!")
    print()
    print("The following changes were made to NOTICES table:")
    print("  • Added column: temporal_analysis JSONB NULL")
    print("  • Created index: idx_notices_temporal_analysis (GIN)")
    print("  • Created index: idx_notices_temporal_notice_date")
    print("  • Created index: idx_notices_temporal_type")
    print("  • Created index: idx_notices_temporal_expiration")
    
except Exception as e:
    conn.rollback()
    conn.close()
    print(f"❌ Migration failed: {e}")
    sys.exit(1)

print()
print("=" * 70)

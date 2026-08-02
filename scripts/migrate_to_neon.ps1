# ============================================================
# CNPI RAG - Neon Database Migration Script
# ============================================================
# Migrates local PostgreSQL database to Neon (or any remote PostgreSQL)
#
# Usage:
#   1. Edit the NEON_CONNECTION_STRING below
#   2. Run:  powershell -ExecutionPolicy Bypass -File scripts\migrate_to_neon.ps1
# ============================================================

# === CONFIG: Replace with your Neon connection string ===
$NEON_CONNECTION_STRING = "postgresql://neondb_owner:npg_rg71GYeouDqI@ep-royal-wildflower-azq6xooz.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# === Local DB config (from .env) ===
$LOCAL_HOST     = "localhost"
$LOCAL_DB       = "cnpi_rag_db"
$LOCAL_USER     = "postgres"
$LOCAL_PASSWORD = "admin8899"

$DUMP_FILE = "$env:TEMP\kilo\cnpi_rag_dump.sql"

# ------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CNPI RAG -> Neon Database Migration" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Dump local database
Write-Host "[1/3] Dumping local database..." -ForegroundColor Yellow
$env:PGPASSWORD = $LOCAL_PASSWORD
pg_dump -h $LOCAL_HOST -U $LOCAL_USER -d $LOCAL_DB --schema=public --no-owner --no-privileges --no-comments -F p -f $DUMP_FILE

if (-not (Test-Path $DUMP_FILE)) {
    Write-Host "ERROR: Dump failed!" -ForegroundColor Red
    exit 1
}
$sizeKB = [math]::Round((Get-Item $DUMP_FILE).Length / 1KB, 2)
Write-Host "  -> Dump created: $DUMP_FILE ($sizeKB KB)" -ForegroundColor Green

# Step 2: Enable extensions on Neon
Write-Host ""
Write-Host "[2/3] Enabling pgvector + pg_trgm on Neon..." -ForegroundColor Yellow
psql $NEON_CONNECTION_STRING -c "CREATE EXTENSION IF NOT EXISTS vector;" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: Could not auto-enable extensions." -ForegroundColor Yellow
    Write-Host "  Please run manually in Neon SQL Editor:" -ForegroundColor Yellow
    Write-Host "    CREATE EXTENSION IF NOT EXISTS vector;" -ForegroundColor White
    Write-Host "    CREATE EXTENSION IF NOT EXISTS pg_trgm;" -ForegroundColor White
}

# Step 3: Restore dump to Neon
Write-Host ""
Write-Host "[3/3] Restoring data to Neon..." -ForegroundColor Yellow
psql $NEON_CONNECTION_STRING -f $DUMP_FILE

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  MIGRATION COMPLETE!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify with:" -ForegroundColor Cyan
    Write-Host "  psql `"$NEON_CONNECTION_STRING`" -c 'SELECT COUNT(*) FROM departments;'" -ForegroundColor White
    Write-Host "  psql `"$NEON_CONNECTION_STRING`" -c 'SELECT COUNT(*) FROM people;'" -ForegroundColor White
    Write-Host "  psql `"$NEON_CONNECTION_STRING`" -c 'SELECT COUNT(*) FROM documents;'" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "ERROR: Restore failed. Check errors above." -ForegroundColor Red
}
Write-Host ""

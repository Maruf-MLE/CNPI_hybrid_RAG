################################################################################
# CNPI Hybrid RAG — Keep-Alive Cron Job (PowerShell)
# ====================================================
# Purpose : Ping the Render backend every 14 minutes so the free-tier
#           instance never spins down (Render sleeps after 15 min idle).
#
# How to install (Windows Task Scheduler — one-time setup):
#   1. Open PowerShell as Administrator.
#   2. Run:  schtasks /create /tn "CNPI-KeepAlive" /tr "powershell -NonInteractive -ExecutionPolicy Bypass -File \"G:\CNPI_Hybrid_RAG\scripts\keep_alive.ps1\"" /sc MINUTE /mo 14 /ru SYSTEM
#   3. Verify: schtasks /query /tn "CNPI-KeepAlive"
#
# To remove the task:
#   schtasks /delete /tn "CNPI-KeepAlive" /f
#
# Log file: G:\CNPI_Hybrid_RAG\logs\keep_alive.log  (auto-created)
################################################################################

param(
    [string]$PingUrl    = "https://cnpi-hybrid-rag-1.onrender.com/api/ping/",
    [string]$LogFile    = "G:\CNPI_Hybrid_RAG\logs\keep_alive.log",
    [int]   $TimeoutSec = 30,
    [int]   $MaxLogKB   = 512   # rotate log when larger than this
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
$logDir = Split-Path $LogFile
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

# Rotate log when it exceeds MaxLogKB
if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length / 1KB) -gt $MaxLogKB) {
    Rename-Item $LogFile "$LogFile.old" -Force -ErrorAction SilentlyContinue
}

$timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# ---------------------------------------------------------------------------
# Ping
# ---------------------------------------------------------------------------
try {
    $response = Invoke-WebRequest `
        -Uri        $PingUrl `
        -Method     GET `
        -TimeoutSec $TimeoutSec `
        -UseBasicParsing `
        -ErrorAction Stop

    $status = $response.StatusCode
    Add-Content $LogFile "[$timestamp] OK  HTTP $status  $PingUrl"
    Write-Host   "[$timestamp] OK  HTTP $status"
}
catch {
    $errMsg = $_.Exception.Message
    Add-Content $LogFile "[$timestamp] ERR $errMsg  $PingUrl"
    Write-Host   "[$timestamp] ERR $errMsg"
    exit 1
}

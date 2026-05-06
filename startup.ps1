# ============================================================================
# File: startup.ps1
# One-click launcher: FastAPI backend (KnowledgeBase) + static frontend
#       (FavoriteAgent-frontend-pockety) in separate PowerShell processes.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File ".\startup.ps1"
#
# What this script does:
# 1) Changes to the directory where this script lives (repo root).
# 2) Picks free ports if 8000 / 5500 are busy (backend / static server).
# 3) Starts uvicorn (app.main:app) and python -m http.server for the frontend.
# 4) Waits until /health and home.html respond.
# 5) Opens the default browser on the frontend URL.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$msg) {
  Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-Ok([string]$msg) {
  Write-Host "[OK]   $msg" -ForegroundColor Green
}

function Write-WarnMsg([string]$msg) {
  Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

function Resolve-PythonCmd {
  if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
  if (Get-Command py -ErrorAction SilentlyContinue) { return "py -3" }
  throw "Python command not found (python/py). Please install Python 3 first."
}

function Test-PortInUse([int]$Port) {
  $listener = $null
  try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    $listener.Start()
    return $false
  } catch {
    return $true
  } finally {
    if ($listener) {
      try { $listener.Stop() } catch {}
    }
  }
}

function Get-FreePort([int]$PreferredPort, [int]$MaxScan = 50) {
  for ($i = 0; $i -lt $MaxScan; $i++) {
    $candidate = $PreferredPort + $i
    if (-not (Test-PortInUse -Port $candidate)) {
      if ($candidate -ne $PreferredPort) {
        Write-WarnMsg "Port $PreferredPort is occupied. Switched to $candidate."
      }
      return $candidate
    }
  }
  throw "No free port found in range [$PreferredPort .. $($PreferredPort + $MaxScan - 1)]."
}

function Wait-HttpReady([string]$Url, [int]$TimeoutSeconds = 90) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        return $true
      }
    } catch {}
    Start-Sleep -Milliseconds 800
  }
  return $false
}

try {
  # Auto cd to project directory (script location)
  $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  Set-Location $ScriptDir
  Write-Info "Working directory: $ScriptDir"

  $pythonCmd = Resolve-PythonCmd
  Write-Info "Python command: $pythonCmd"

  $backendPort = Get-FreePort -PreferredPort 8000
  $frontendPort = Get-FreePort -PreferredPort 5500

  $backendCmd = "$pythonCmd -m uvicorn app.main:app --host 0.0.0.0 --port $backendPort"
  $frontendCmd = "$pythonCmd -m http.server $frontendPort --bind 0.0.0.0 --directory `"$ScriptDir\FavoriteAgent-frontend-pockety`""

  Write-Info "Starting backend: $backendCmd"
  $backendProc = Start-Process -FilePath "powershell" `
    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd `
    -WorkingDirectory $ScriptDir `
    -PassThru

  Write-Info "Starting frontend: $frontendCmd"
  $frontendProc = Start-Process -FilePath "powershell" `
    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd `
    -WorkingDirectory $ScriptDir `
    -PassThru

  $backendHealthUrl = "http://127.0.0.1:$backendPort/health"
  $frontendPageUrl = "http://127.0.0.1:$frontendPort/home.html"

  Write-Info "Waiting backend readiness: $backendHealthUrl"
  $backendReady = Wait-HttpReady -Url $backendHealthUrl -TimeoutSeconds 120

  Write-Info "Waiting frontend readiness: $frontendPageUrl"
  $frontendReady = Wait-HttpReady -Url $frontendPageUrl -TimeoutSeconds 120

  if (-not $backendReady) {
    throw "Backend startup timeout. Verify dependencies (pip install -r requirements.txt), .env, and that port $backendPort is free."
  }
  if (-not $frontendReady) {
    throw "Frontend startup timeout. Verify FavoriteAgent-frontend-pockety exists and port $frontendPort is free."
  }

  Write-Ok "Backend ready: $backendHealthUrl"
  Write-Ok "Frontend ready: $frontendPageUrl"
  Start-Process $frontendPageUrl
  Write-Ok "Default browser opened."
  Write-Host ""
  Write-Host "Background process PID: backend=$($backendProc.Id), frontend=$($frontendProc.Id)"
} catch {
  Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

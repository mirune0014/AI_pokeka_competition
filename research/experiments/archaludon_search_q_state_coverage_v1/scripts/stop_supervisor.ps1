$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$status = Join-Path $repo '_local_generated\archaludon_search_q_state_coverage_v1\supervisor_status.json'
if (-not (Test-Path -LiteralPath $status)) { Write-Output 'status file not found'; exit 0 }
$value = Get-Content -LiteralPath $status -Raw | ConvertFrom-Json
foreach($pidValue in @($value.worker_pids)) { if($pidValue){ Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue } }

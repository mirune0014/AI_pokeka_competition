$ErrorActionPreference = 'Stop'
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = (git -C $scriptDirectory rev-parse --show-toplevel).Trim()
if (-not $repo) { Write-Output 'repository root not found'; exit 1 }
$status = Join-Path $repo '_local_generated\archaludon_search_q_state_coverage_v1\supervisor_status.json'
if (-not (Test-Path -LiteralPath $status)) { Write-Output 'status file not found'; exit 1 }
$value = Get-Content -LiteralPath $status -Raw | ConvertFrom-Json
[pscustomobject]@{ stage=$value.current_stage; pid=($value.worker_pids -join ','); alive='managed externally'; completed_shards=($value.completed_shards -join ','); error=$value.error; updated=$value.updated_at } | Format-List

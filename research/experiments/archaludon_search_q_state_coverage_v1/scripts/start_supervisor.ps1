$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$repo = Split-Path -Parent (Split-Path -Parent $root)
$python = Join-Path $repo '.venv-ptcg\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python).Source }
$output = Join-Path $repo '_local_generated\archaludon_search_q_state_coverage_v1'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$process = Start-Process -FilePath $python -WorkingDirectory $repo -ArgumentList @('-m','research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.cli','supervise') -RedirectStandardOutput (Join-Path $output 'supervisor.stdout.log') -RedirectStandardError (Join-Path $output 'supervisor.stderr.log') -PassThru
$process.Id

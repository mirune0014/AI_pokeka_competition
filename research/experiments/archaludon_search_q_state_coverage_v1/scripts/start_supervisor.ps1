param(
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (git -C $scriptDirectory rev-parse --show-toplevel).Trim()
if (-not $repoRoot) { throw 'repository root could not be resolved' }

$python = Join-Path $repoRoot '.venv-ptcg\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw "missing Python environment: $python" }

$existingProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and
    $_.CommandLine -match 'archaludon_search_q_state_coverage_v1.*supervise'
})
if ($existingProcesses.Count -ne 0) {
    throw 'an existing state coverage supervisor or worker process remains'
}

$outputRoot = Join-Path $repoRoot '_local_generated\archaludon_search_q_state_coverage_v1'
$launcherLogRoot = Join-Path $repoRoot '_local_generated\archaludon_search_q_state_coverage_v1_launcher_logs'
New-Item -ItemType Directory -Path $launcherLogRoot -Force | Out-Null

$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$stdoutPath = Join-Path $launcherLogRoot "supervisor_$($timestamp).stdout.log"
$stderrPath = Join-Path $launcherLogRoot "supervisor_$($timestamp).stderr.log"
$arguments = @(
    '-m',
    'research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.cli',
    'supervise'
)
if ($Resume) {
    $arguments += "--resume"
}

$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $repoRoot -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru

$launchMetadata = [ordered]@{
    schema_version = 'archaludon-state-coverage-launch-v1'
    launched_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    pid = $process.Id
    output_root = $outputRoot
    stdout_path = $stdoutPath
    stderr_path = $stderrPath
}
$latestLaunchPath = Join-Path $launcherLogRoot 'latest_launch.json'
$launchMetadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $latestLaunchPath -Encoding utf8

Start-Sleep -Seconds 3
$process.Refresh()
if ($process.HasExited) {
    $stderrText = ''
    if (Test-Path -LiteralPath $stderrPath) {
        $stderrText = Get-Content -LiteralPath $stderrPath -Raw
    }
    throw (
        "supervisor exited during bootstrap; " +
        "exit_code=$($process.ExitCode); " +
        "stderr=$stderrPath; " +
        $stderrText
    )
}

[pscustomobject]@{
    PID = $process.Id
    OutputRoot = $outputRoot
    Stdout = $stdoutPath
    Stderr = $stderrPath
    LatestLaunch = $latestLaunchPath
} | Format-List

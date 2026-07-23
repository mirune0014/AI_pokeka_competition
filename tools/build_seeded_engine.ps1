param(
    [string]$SourceDir = "external\ptcg_engine\ptcgProgram 22",
    [string]$TemplateDir = "submission_archaludon",
    [string]$OutputDir = "analysis_outputs\rl_policy_value\seeded_engine"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$source = [IO.Path]::GetFullPath((Join-Path $repoRoot $SourceDir))
$template = [IO.Path]::GetFullPath((Join-Path $repoRoot $TemplateDir))
$output = [IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$cgOutput = Join-Path $output "cg"

$zig = Get-Command zig -ErrorAction SilentlyContinue
if (-not $zig) {
    $zigPath = Get-ChildItem `
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\zig.zig_*\zig-*\zig.exe" `
        -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $zigPath) {
        throw "zig was not found. Install zig.zig with winget first."
    }
    $zig = $zigPath
}

New-Item -ItemType Directory -Force -Path $cgOutput | Out-Null
Copy-Item -Path (Join-Path $template "cg\*") -Destination $cgOutput -Recurse -Force

Push-Location $source
try {
    & $zig c++ -target x86_64-windows-gnu -std=c++20 -O2 -shared `
        -Wno-nullability-completeness Export.cpp -o (Join-Path $cgOutput "cg.dll")
    if ($LASTEXITCODE -ne 0) {
        throw "Seeded engine build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Output (Join-Path $cgOutput "cg.dll")

param(
    [switch]$NoClean
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
Set-Location $repoRoot
$ptcgVenv = Join-Path $repoRoot '.venv-ptcg'
$reqFile = Join-Path $repoRoot 'infrastructure\ptcg-venv-requirements.txt'
$ptcgPython = Join-Path $ptcgVenv 'Scripts\python.exe'
$venvBuilder = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3.11 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($LASTEXITCODE -eq 0) {
            $venvBuilder = @{ cmd = 'py'; args = @('-3.11') }
        }
    } catch {
        # Fallback to default python command
    }
}

if (-not $venvBuilder) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $version = (& $pythonCommand.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if ($version -eq '3.11') {
            $venvBuilder = @{ cmd = $pythonCommand.Source; args = @() }
        }
    }
}

if (-not $venvBuilder) {
    throw "Python 3.11 not found. Install Python 3.11 and rerun this script."
}

if (!$NoClean -and (Test-Path $ptcgVenv)) {
    Remove-Item -Recurse -Force $ptcgVenv
}

if ($venvBuilder.args.Count -gt 0) {
    & $venvBuilder.cmd $venvBuilder.args -m venv $ptcgVenv
} else {
    & $venvBuilder.cmd -m venv $ptcgVenv
}
& $ptcgPython -m pip install --upgrade pip
& $ptcgPython -m pip install -r $reqFile --extra-index-url https://download.pytorch.org/whl/cu128

param(
    [string]$Destination = ""
)

$ErrorActionPreference = "Stop"
$extensionRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Resolve-Path (Join-Path $extensionRoot "..\..")
$manifest = Get-Content -LiteralPath (Join-Path $extensionRoot "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $Destination) {
    $Destination = Join-Path $repositoryRoot ("_local_generated\deliverables\ptcg-japanese-visualizer-extension-v" + $manifest.version + ".zip")
}

$destinationPath = [System.IO.Path]::GetFullPath($Destination)
$destinationDirectory = Split-Path -Parent $destinationPath
New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ptcg-ja-extension-" + [guid]::NewGuid().ToString("N"))
$stagingExtension = Join-Path $stagingRoot "ptcg-japanese-visualizer-extension"
New-Item -ItemType Directory -Force -Path $stagingExtension | Out-Null

try {
    $included = @(
        "manifest.json",
        "rules.json",
        "translations.js",
        "core.js",
        "main.js",
        "README.md",
        "assets",
        "scripts",
        "tests"
    )
    foreach ($item in $included) {
        Copy-Item -LiteralPath (Join-Path $extensionRoot $item) -Destination $stagingExtension -Recurse
    }

    if (Test-Path -LiteralPath $destinationPath) {
        Remove-Item -LiteralPath $destinationPath
    }
    Compress-Archive -Path $stagingExtension -DestinationPath $destinationPath -CompressionLevel Optimal
    Get-Item -LiteralPath $destinationPath | Select-Object FullName, Length
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

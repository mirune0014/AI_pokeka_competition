param(
    [string]$SourceRoot = "",
    [string]$Destination = "C:\ptcg\bc0_handoff.zip"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
if (-not $SourceRoot) {
    $SourceRoot = Join-Path $RepoRoot "analysis_outputs\archaludon_complete_action_bc_teacher_2000_20260802"
}
$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)
$Destination = [IO.Path]::GetFullPath($Destination)
$StagingBase = [IO.Path]::GetFullPath("C:\ptcg")
$StagingRoot = Join-Path $StagingBase "pack_$PID"
if (-not $StagingRoot.StartsWith($StagingBase + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe staging path: $StagingRoot"
}
if (Test-Path -LiteralPath $Destination) {
    throw "Handoff ZIP already exists: $Destination"
}
if (Test-Path -LiteralPath $StagingRoot) {
    throw "Staging path already exists: $StagingRoot"
}

$Inputs = @(
    [pscustomobject]@{ Source = (Join-Path $SourceRoot "dataset\complete_action_bc_dataset.pt"); Name = "base.pt"; Expected = "" },
    [pscustomobject]@{ Source = (Join-Path $SourceRoot "bc\checkpoints\complete_bc_seed2026080211.pt"); Name = "a11.pt"; Expected = "52A9C8E80E6F2C717320058A3DA6DC44AAFD2AFB784B149D6629DC5356F38F24" },
    [pscustomobject]@{ Source = (Join-Path $SourceRoot "bc\checkpoints\complete_bc_seed2026080212.pt"); Name = "a12.pt"; Expected = "2AA80CF49421A14F389A2B67FD19DD751B52F3F679BBC27E573ACC8ACC28BA6D" },
    [pscustomobject]@{ Source = (Join-Path $SourceRoot "bc\checkpoints\complete_bc_seed2026080213.pt"); Name = "a13.pt"; Expected = "F27AE4866794E00864E15F6A057855880514C9CC46B1404F5680F041E6D8EDF6" }
)
foreach ($Input in $Inputs) {
    if (-not (Test-Path -LiteralPath $Input.Source -PathType Leaf)) {
        throw "Required handoff input is missing: $($Input.Source)"
    }
    if ($Input.Expected) {
        $Actual = (Get-FileHash -LiteralPath $Input.Source -Algorithm SHA256).Hash.ToUpperInvariant()
        if ($Actual -ne $Input.Expected) {
            throw "Checkpoint hash mismatch: $($Input.Source)"
        }
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
New-Item -ItemType Directory -Path $StagingRoot | Out-Null
try {
    $ManifestFiles = @()
    foreach ($Input in $Inputs) {
        $Target = Join-Path $StagingRoot $Input.Name
        Copy-Item -LiteralPath $Input.Source -Destination $Target
        $Item = Get-Item -LiteralPath $Target
        $ManifestFiles += [ordered]@{
            name = $Input.Name
            bytes = $Item.Length
            sha256 = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToUpperInvariant()
        }
    }
    $Manifest = [ordered]@{
        schema_version = "complete-action-bc-minimal-handoff-v1"
        files = $ManifestFiles
    }
    $ManifestPath = Join-Path $StagingRoot "manifest.json"
    $Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ManifestPath -Encoding utf8
    $ArchiveInputs = Get-ChildItem -LiteralPath $StagingRoot -File | Select-Object -ExpandProperty FullName
    Compress-Archive -LiteralPath $ArchiveInputs -DestinationPath $Destination -CompressionLevel Optimal
}
finally {
    if (Test-Path -LiteralPath $StagingRoot) {
        $ResolvedStage = (Resolve-Path -LiteralPath $StagingRoot).Path
        if (-not $ResolvedStage.StartsWith($StagingBase + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unsafe staging path: $ResolvedStage"
        }
        Remove-Item -LiteralPath $ResolvedStage -Recurse -Force
    }
}

$Archive = Get-Item -LiteralPath $Destination
Write-Host "Handoff ZIP: $($Archive.FullName)"
Write-Host "Bytes: $($Archive.Length)"
Write-Host "SHA256: $((Get-FileHash -LiteralPath $Archive.FullName -Algorithm SHA256).Hash.ToUpperInvariant())"

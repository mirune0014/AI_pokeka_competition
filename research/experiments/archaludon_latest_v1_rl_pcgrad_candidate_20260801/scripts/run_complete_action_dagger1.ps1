param(
    [ValidateSet("collect", "merge", "train", "evaluate", "all")]
    [string]$Stage = "all",
    [ValidateSet("cpu", "cuda")]
    [string]$TrainingDevice = "cuda",
    [string]$InputRoot = "C:\ptcg\bc0",
    [string]$WorkRoot = "C:\ptcg\d1"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Python = Join-Path $RepoRoot ".venv-ptcg\Scripts\python.exe"
$InitialCheckpoint = Join-Path $RepoRoot "_local_generated\analysis_outputs\archaludon_latest_v1_rl_phase1_iteration_004_temperature065_checkpoint_deterministic_20260731\initial_zero_temperature065.pt"
$Population = Join-Path $ProjectDir "specs\phase1_iteration_002_population.json"
$ExperimentSpec = Join-Path $ProjectDir "specs\complete_action_bc_dagger1_v1_20260802.json"
$BaselineResult = Join-Path $ProjectDir "BC_ACTOR_MINIMAL_RESULT.json"

$InputRoot = [IO.Path]::GetFullPath($InputRoot)
$WorkRoot = [IO.Path]::GetFullPath($WorkRoot)
foreach ($ShortRoot in @($InputRoot, $WorkRoot)) {
    if ($ShortRoot.Length -gt 80) {
        throw "DAgger roots must stay at or below 80 characters to avoid legacy Windows path failures: $ShortRoot"
    }
}
if ($InputRoot -eq $WorkRoot) {
    throw "InputRoot and WorkRoot must differ"
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python runtime not found: $Python"
}
if (-not (Test-Path -LiteralPath $InitialCheckpoint -PathType Leaf)) {
    throw "iteration004 checkpoint not found: $InitialCheckpoint"
}
New-Item -ItemType Directory -Force -Path $WorkRoot | Out-Null

$BaseDataset = Join-Path $InputRoot "base.pt"
$CollectionRoot = Join-Path $WorkRoot "c"
$MergedDataset = Join-Path $WorkRoot "data.pt"
$MergedReport = Join-Path $WorkRoot "data.json"
$TrainingRoot = Join-Path $WorkRoot "t"
$EvaluationRoot = Join-Path $WorkRoot "e"
$Actors = @(
    [pscustomobject]@{ Id = "a11"; File = "a11.pt"; Sha256 = "52A9C8E80E6F2C717320058A3DA6DC44AAFD2AFB784B149D6629DC5356F38F24" },
    [pscustomobject]@{ Id = "a12"; File = "a12.pt"; Sha256 = "2AA80CF49421A14F389A2B67FD19DD751B52F3F679BBC27E573ACC8ACC28BA6D" },
    [pscustomobject]@{ Id = "a13"; File = "a13.pt"; Sha256 = "F27AE4866794E00864E15F6A057855880514C9CC46B1404F5680F041E6D8EDF6" }
)

$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:CUBLAS_WORKSPACE_CONFIG = ":4096:8"

function Invoke-PythonStep {
    param([string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python step failed with exit code $LASTEXITCODE"
    }
}

function Require-File {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label not found: $Path"
    }
}

Push-Location $ProjectDir
try {
    if ($Stage -in @("collect", "all")) {
        foreach ($Actor in $Actors) {
            $Checkpoint = Join-Path $InputRoot $Actor.File
            $Part = Join-Path $CollectionRoot "$($Actor.Id).pt"
            $Report = Join-Path $CollectionRoot "$($Actor.Id).json"
            Require-File $Checkpoint "BC actor checkpoint"
            $ActualHash = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash.ToUpperInvariant()
            if ($ActualHash -ne $Actor.Sha256) {
                throw "BC actor checkpoint hash mismatch for $($Actor.Id)"
            }
            if ((Test-Path -LiteralPath $Part) -and (Test-Path -LiteralPath $Report)) {
                Write-Host "Skipping completed DAgger collection $($Actor.Id)"
                continue
            }
            if ((Test-Path -LiteralPath $Part) -or (Test-Path -LiteralPath $Report)) {
                throw "Partial DAgger collection output exists for $($Actor.Id)"
            }
            Invoke-PythonStep @(
                "-B", "-m", "archaludon_rl.collect_complete_bc_dagger",
                "--checkpoint", $Checkpoint,
                "--expected-checkpoint-sha256", $Actor.Sha256,
                "--actor-id", $Actor.Id,
                "--opponent-population", $Population,
                "--output", $Part,
                "--report", $Report,
                "--seed-base", "731400000",
                "--episodes-per-seat", "20",
                "--max-steps", "1000",
                "--progress-every", "10"
            )
        }
    }

    if ($Stage -in @("merge", "all")) {
        Require-File $BaseDataset "base compact dataset"
        $Parts = @($Actors | ForEach-Object { Join-Path $CollectionRoot "$($_.Id).pt" })
        foreach ($Part in $Parts) {
            Require-File $Part "DAgger compact addition"
        }
        if ((Test-Path -LiteralPath $MergedDataset) -and (Test-Path -LiteralPath $MergedReport)) {
            Write-Host "Skipping completed DAgger dataset merge"
        }
        elseif ((Test-Path -LiteralPath $MergedDataset) -or (Test-Path -LiteralPath $MergedReport)) {
            throw "Partial merged DAgger dataset output exists"
        }
        else {
            $MergeArguments = @(
                "-B", "-m", "archaludon_rl.merge_complete_bc_datasets",
                "--base", $BaseDataset
            )
            foreach ($Part in $Parts) {
                $MergeArguments += @("--addition", $Part)
            }
            $MergeArguments += @("--output", $MergedDataset, "--report", $MergedReport)
            Invoke-PythonStep $MergeArguments
        }
    }

    if ($Stage -in @("train", "all")) {
        Require-File $MergedDataset "merged DAgger dataset"
        foreach ($Seed in @(2026080211, 2026080212, 2026080213)) {
            $Checkpoint = Join-Path $TrainingRoot "checkpoints\dagger1_seed$Seed.pt"
            $Report = Join-Path $TrainingRoot "training\dagger1_seed$Seed.json"
            if ((Test-Path -LiteralPath $Checkpoint) -and (Test-Path -LiteralPath $Report)) {
                Write-Host "Skipping completed DAgger training seed $Seed"
                continue
            }
            if ((Test-Path -LiteralPath $Checkpoint) -or (Test-Path -LiteralPath $Report)) {
                throw "Partial DAgger training output exists for seed $Seed"
            }
            Invoke-PythonStep @(
                "-B", "-m", "archaludon_rl.train_complete_bc",
                "--dataset", $MergedDataset,
                "--input-checkpoint", $InitialCheckpoint,
                "--output-checkpoint", $Checkpoint,
                "--report", $Report,
                "--seed", "$Seed",
                "--epochs", "20",
                "--batch-size", "256",
                "--learning-rate", "0.001",
                "--gradient-clip", "1.0",
                "--device", $TrainingDevice
            )
        }
    }

    if ($Stage -in @("evaluate", "all")) {
        $Summary = Join-Path $EvaluationRoot "evaluation_summary.json"
        if (Test-Path -LiteralPath $Summary -PathType Leaf) {
            Write-Host "Skipping completed DAgger fixed evaluation"
        }
        elseif (Test-Path -LiteralPath $EvaluationRoot) {
            throw "Partial DAgger evaluation output exists: $EvaluationRoot"
        }
        else {
            Invoke-PythonStep @(
                "-B", "-m", "archaludon_rl.evaluate_bc",
                "--spec", $ExperimentSpec,
                "--training-root", $TrainingRoot,
                "--baseline-result", $BaselineResult,
                "--output-dir", $EvaluationRoot,
                "--workers", "4"
            )
        }
    }
}
finally {
    Pop-Location
}

Write-Host "DAgger round-one work root: $WorkRoot"

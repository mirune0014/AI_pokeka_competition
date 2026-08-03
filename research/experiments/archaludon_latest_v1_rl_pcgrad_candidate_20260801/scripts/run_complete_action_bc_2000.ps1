param(
    [ValidateSet("collect", "dataset", "train", "evaluate", "all")]
    [string]$Stage = "all",
    [ValidateSet("cpu", "cuda")]
    [string]$TrainingDevice = "cuda"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Python = Join-Path $RepoRoot ".venv-rl\Scripts\python.exe"
$InitialCheckpoint = Join-Path $RepoRoot "_local_generated\analysis_outputs\archaludon_latest_v1_rl_phase1_iteration_004_temperature065_checkpoint_deterministic_20260731\initial_zero_temperature065.pt"
$Population = Join-Path $ProjectDir "specs\phase1_iteration_002_population.json"
$ExperimentSpec = Join-Path $ProjectDir "specs\complete_action_bc_2000_v1_20260802.json"
$BaselineResult = Join-Path $ProjectDir "BC_ACTOR_MINIMAL_RESULT.json"
$OutputRoot = Join-Path $RepoRoot "_local_generated\analysis_outputs\archaludon_complete_action_bc_teacher_2000_20260802"
$RolloutDir = Join-Path $OutputRoot "rollouts"
$DatasetDir = Join-Path $OutputRoot "dataset"
$Dataset = Join-Path $DatasetDir "complete_action_bc_dataset.pt"
$DatasetReport = Join-Path $DatasetDir "build_report.json"
$TrainingRoot = Join-Path $OutputRoot "bc"
$EvaluationDir = Join-Path $OutputRoot "fixed_evaluation"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python runtime not found: $Python"
}

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

Push-Location $ProjectDir
try {
    if ($Stage -in @("collect", "all")) {
        if (Test-Path -LiteralPath $RolloutDir) {
            throw "Rollout output already exists; use the next stage explicitly or move the incomplete output: $RolloutDir"
        }
        Invoke-PythonStep @(
            "-B", "-m", "archaludon_rl.collect_rollouts",
            "--checkpoint", $InitialCheckpoint,
            "--opponent-population", $Population,
            "--output-dir", $RolloutDir,
            "--run-id", "complete-action-bc-teacher-2000-20260802",
            "--seed-base", "731300000",
            "--episodes-per-seat", "125",
            "--seat", "both",
            "--max-steps", "1000",
            "--progress-every", "25",
            "--device", "cpu",
            "--collection-mode", "deployment",
            "--preflight-require-zero-residuals"
        )
    }

    if ($Stage -in @("dataset", "all")) {
        if (-not (Test-Path -LiteralPath (Join-Path $RolloutDir "run_manifest.json") -PathType Leaf)) {
            throw "Complete rollout manifest not found: $RolloutDir"
        }
        Invoke-PythonStep @(
            "-B", "-m", "archaludon_rl.build_complete_bc_dataset",
            "--episodes-dir", (Join-Path $RolloutDir "episodes"),
            "--output", $Dataset,
            "--report", $DatasetReport,
            "--validation-seed-base", "731300000",
            "--validation-seed-modulus", "5",
            "--validation-seed-residue", "0",
            "--expected-episodes", "2000",
            "--expected-episodes-per-cell", "125",
            "--maximum-candidates", "4096",
            "--require-teacher-trajectory"
        )
    }

    if ($Stage -in @("train", "all")) {
        if (-not (Test-Path -LiteralPath $Dataset -PathType Leaf)) {
            throw "Compact BC dataset not found: $Dataset"
        }
        foreach ($Seed in @(2026080211, 2026080212, 2026080213)) {
            $Checkpoint = Join-Path $TrainingRoot "checkpoints\complete_bc_seed$Seed.pt"
            $Report = Join-Path $TrainingRoot "training\complete_bc_seed$Seed.json"
            if ((Test-Path -LiteralPath $Checkpoint) -and (Test-Path -LiteralPath $Report)) {
                Write-Host "Skipping completed training seed $Seed"
                continue
            }
            if ((Test-Path -LiteralPath $Checkpoint) -or (Test-Path -LiteralPath $Report)) {
                throw "Partial training output exists for seed $Seed"
            }
            Invoke-PythonStep @(
                "-B", "-m", "archaludon_rl.train_complete_bc",
                "--dataset", $Dataset,
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
        Invoke-PythonStep @(
            "-B", "-m", "archaludon_rl.evaluate_bc",
            "--spec", $ExperimentSpec,
            "--training-root", $TrainingRoot,
            "--baseline-result", $BaselineResult,
            "--output-dir", $EvaluationDir,
            "--workers", "4"
        )
    }
}
finally {
    Pop-Location
}

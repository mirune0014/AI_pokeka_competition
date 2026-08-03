param(
    [string]$RawRoot = "C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\evaluations\archaludon_search_aware_active_terminal_before_nonterminal_boss_v1\fixed760_raw_20260730_r1",
    [string]$Output = "C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\root_verification\archaludon_search_aware_fixed760_20260730\ROOT_RECOMPUTATION.json"
)

$ErrorActionPreference = "Stop"

$expected = [ordered]@{
    historical_silver = [ordered]@{ games = 200; games_per_seat = 100; seed_base = 271828182 }
    arch_peak = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
    arch_shumpei = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
    alakazam_capbloo_gold = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
    marnie_kazuki_live = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
    mega_lucario_public = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
    kang_crustle = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
    cynthia_v23 = [ordered]@{ games = 80; games_per_seat = 40; seed_base = 271958313 }
}

$rows = [System.Collections.Generic.List[object]]::new()
$reports = [System.Collections.Generic.List[object]]::new()
$manifests = [System.Collections.Generic.List[object]]::new()

foreach ($panel in $expected.Keys) {
    $panelDir = Join-Path $RawRoot $panel
    $csv = Join-Path $panelDir "paired_results.csv"
    $reportPath = Join-Path $panelDir "report.json"
    $manifestPath = Join-Path $panelDir "manifest.jsonl"
    if (-not (Test-Path -LiteralPath $csv)) { throw "missing paired results: $csv" }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "missing report: $reportPath" }
    if (-not (Test-Path -LiteralPath $manifestPath)) { throw "missing manifest: $manifestPath" }

    $panelRows = @(Import-Csv -LiteralPath $csv)
    foreach ($row in $panelRows) {
        $seat = [int]$row.seat
        $baselineResult = [int]$row.baseline_result
        $candidateResult = [int]$row.candidate_result
        $rows.Add([pscustomobject]@{
            panel = $panel
            opponent = [string]$row.opponent
            seat = $seat
            game = [int]$row.game
            seed = [int64]$row.seed
            seed_base = [int64]$row.seed_base
            baseline_result = $baselineResult
            candidate_result = $candidateResult
            baseline_win = [int]$row.baseline_win
            candidate_win = [int]$row.candidate_win
            recomputed_baseline_win = [int]($baselineResult -eq $seat)
            recomputed_candidate_win = [int]($candidateResult -eq $seat)
            baseline_steps = [int]$row.baseline_steps
            candidate_steps = [int]$row.candidate_steps
        })
    }

    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    $reports.Add([pscustomobject]@{
        panel = $panel
        valid = [bool]$report.valid
        invalid_reasons = @($report.invalid_reasons)
        duplicate_mismatch_count = [int]$report.duplicate_mismatch_count
        baseline_wins = [int]$report.aggregates.baseline_wins
        candidate_wins = [int]$report.aggregates.candidate_wins
        games = [int]$report.aggregates.games
    })

    foreach ($line in Get-Content -LiteralPath $manifestPath) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $entry = $line | ConvertFrom-Json
            $manifests.Add([pscustomobject]@{
                panel = $panel
                role = [string]$entry.role
                seat = [int]$entry.seat
                exit_code = [int]$entry.exit_code
            })
        }
    }
}

$rowArray = @($rows)
$keys = @($rowArray | ForEach-Object { "$($_.panel)|$($_.opponent)|$($_.seat)|$($_.seed)" })
$uniqueKeys = @($keys | Sort-Object -Unique)
$duplicateKeys = @($keys | Group-Object | Where-Object Count -ne 1 | ForEach-Object Name)

$scheduleErrors = [System.Collections.Generic.List[string]]::new()
foreach ($panel in $expected.Keys) {
    $spec = $expected[$panel]
    $panelRows = @($rowArray | Where-Object panel -eq $panel)
    if ($panelRows.Count -ne [int]$spec.games) {
        $scheduleErrors.Add("$panel row count $($panelRows.Count) != $($spec.games)")
    }
    foreach ($seat in 0, 1) {
        $seatRows = @($panelRows | Where-Object seat -eq $seat | Sort-Object seed)
        if ($seatRows.Count -ne [int]$spec.games_per_seat) {
            $scheduleErrors.Add("$panel seat $seat count $($seatRows.Count) != $($spec.games_per_seat)")
            continue
        }
        $actualSeeds = @($seatRows | ForEach-Object seed)
        $expectedSeeds = @(0..([int]$spec.games_per_seat - 1) | ForEach-Object { [int64]$spec.seed_base + $_ })
        if ((Compare-Object $actualSeeds $expectedSeeds).Count -ne 0) {
            $scheduleErrors.Add("$panel seat $seat seed schedule mismatch")
        }
    }
}

$winRecomputeMismatches = @(
    $rowArray | Where-Object {
        $_.baseline_win -ne $_.recomputed_baseline_win -or
        $_.candidate_win -ne $_.recomputed_candidate_win
    }
)
$nonbinaryResults = @(
    $rowArray | Where-Object {
        $_.baseline_result -notin 0, 1 -or
        $_.candidate_result -notin 0, 1 -or
        $_.baseline_win -notin 0, 1 -or
        $_.candidate_win -notin 0, 1
    }
)
$maxStepRows = @(
    $rowArray | Where-Object {
        $_.baseline_steps -ge 1000 -or $_.candidate_steps -ge 1000
    }
)
$gains = @($rowArray | Where-Object { $_.baseline_win -eq 0 -and $_.candidate_win -eq 1 })
$regressions = @($rowArray | Where-Object { $_.baseline_win -eq 1 -and $_.candidate_win -eq 0 })

$byPanel = @(
    $rowArray | Group-Object panel | Sort-Object Name | ForEach-Object {
        [ordered]@{
            panel = $_.Name
            games = $_.Count
            baseline_wins = [int](($_.Group | Measure-Object baseline_win -Sum).Sum)
            candidate_wins = [int](($_.Group | Measure-Object candidate_win -Sum).Sum)
            gains = @($_.Group | Where-Object { $_.baseline_win -eq 0 -and $_.candidate_win -eq 1 }).Count
            regressions = @($_.Group | Where-Object { $_.baseline_win -eq 1 -and $_.candidate_win -eq 0 }).Count
        }
    }
)
$bySeat = @(
    $rowArray | Group-Object seat | Sort-Object Name | ForEach-Object {
        [ordered]@{
            seat = [int]$_.Name
            games = $_.Count
            baseline_wins = [int](($_.Group | Measure-Object baseline_win -Sum).Sum)
            candidate_wins = [int](($_.Group | Measure-Object candidate_win -Sum).Sum)
            gains = @($_.Group | Where-Object { $_.baseline_win -eq 0 -and $_.candidate_win -eq 1 }).Count
            regressions = @($_.Group | Where-Object { $_.baseline_win -eq 1 -and $_.candidate_win -eq 0 }).Count
        }
    }
)
$byOpponentSeat = @(
    $rowArray | Group-Object panel, opponent, seat | Sort-Object Name | ForEach-Object {
        $first = $_.Group[0]
        [ordered]@{
            panel = $first.panel
            opponent = $first.opponent
            seat = $first.seat
            games = $_.Count
            baseline_wins = [int](($_.Group | Measure-Object baseline_win -Sum).Sum)
            candidate_wins = [int](($_.Group | Measure-Object candidate_win -Sum).Sum)
            gains = @($_.Group | Where-Object { $_.baseline_win -eq 0 -and $_.candidate_win -eq 1 }).Count
            regressions = @($_.Group | Where-Object { $_.baseline_win -eq 1 -and $_.candidate_win -eq 0 }).Count
        }
    }
)

$historical = @($rowArray | Where-Object panel -eq "historical_silver")
$adjacent = @($rowArray | Where-Object panel -ne "historical_silver")
$kc = @($rowArray | Where-Object panel -eq "kang_crustle")

$outputObject = [ordered]@{
    input = [ordered]@{
        raw_root = $RawRoot
        csv_count = $expected.Count
        checked_runner_wrapper_sha256 = "9DCD5949CA5E251A1EA2B8978AEAE44ED76637EDE636D52E4FB02BDE7D8C745F"
        checked_runner_core_sha256 = "5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000"
    }
    schedule = [ordered]@{
        rows = $rowArray.Count
        unique_keys = $uniqueKeys.Count
        duplicate_keys = $duplicateKeys
        errors = @($scheduleErrors)
    }
    integrity = [ordered]@{
        win_recompute_mismatches = $winRecomputeMismatches.Count
        nonbinary_rows = $nonbinaryResults.Count
        max_step_rows = $maxStepRows.Count
        manifest_entries = $manifests.Count
        nonzero_manifest_exits = @($manifests | Where-Object exit_code -ne 0).Count
        invalid_reports = @($reports | Where-Object { -not $_.valid }).Count
        duplicate_mismatch_total = [int](($reports | Measure-Object duplicate_mismatch_count -Sum).Sum)
        report_invalid_reasons = @($reports | ForEach-Object invalid_reasons)
    }
    totals = [ordered]@{
        games = $rowArray.Count
        baseline_wins = [int](($rowArray | Measure-Object baseline_win -Sum).Sum)
        candidate_wins = [int](($rowArray | Measure-Object candidate_win -Sum).Sum)
        gains = $gains.Count
        regressions = $regressions.Count
        historical_games = $historical.Count
        historical_baseline_wins = [int](($historical | Measure-Object baseline_win -Sum).Sum)
        historical_candidate_wins = [int](($historical | Measure-Object candidate_win -Sum).Sum)
        adjacent_games = $adjacent.Count
        adjacent_baseline_wins = [int](($adjacent | Measure-Object baseline_win -Sum).Sum)
        adjacent_candidate_wins = [int](($adjacent | Measure-Object candidate_win -Sum).Sum)
        kang_crustle_baseline_wins = [int](($kc | Measure-Object baseline_win -Sum).Sum)
        kang_crustle_candidate_wins = [int](($kc | Measure-Object candidate_win -Sum).Sum)
    }
    by_panel = $byPanel
    by_seat = $bySeat
    by_opponent_seat = $byOpponentSeat
    changed_outcome_keys = @(
        @($gains + $regressions) | Sort-Object panel, opponent, seat, seed | ForEach-Object {
            [ordered]@{
                panel = $_.panel
                opponent = $_.opponent
                seat = $_.seat
                seed = $_.seed
                baseline_win = $_.baseline_win
                candidate_win = $_.candidate_win
                baseline_steps = $_.baseline_steps
                candidate_steps = $_.candidate_steps
            }
        }
    )
}

$parent = Split-Path -Parent $Output
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
}
$json = $outputObject | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($Output, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
$json


import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const workspace = path.resolve(process.argv[2] ?? process.cwd());
const staged = path.join(workspace, "alakazam_staged_20260729");
const standardSeeds = [
  202608500,
  202608510,
  202608520,
  202608530,
  202608540,
];
const megaSeeds = [
  202609500,
  202609510,
  202609520,
  202609530,
  202609540,
];
const suiteSpecs = [
  {
    label: "trace_a_retry1",
    root: path.join(
      workspace,
      "metrics",
      "formal_v4_c3_public_survival_bench0_fix5_trace_a_retry1",
    ),
    opponents: ["marnie", "cynthia", "alakazam_mirror"],
    seeds: standardSeeds,
  },
  {
    label: "trace_b",
    root: path.join(
      staged,
      "metrics",
      "formal_v4_c3_public_survival_bench0_fix5_trace_b",
    ),
    opponents: [
      "rocket_mewtwo_spidops_proxy",
      "kangaskhan_crustle",
    ],
    seeds: standardSeeds,
  },
  {
    label: "trace_c",
    root: path.join(
      workspace,
      "metrics",
      "formal_v4_c3_public_survival_bench0_fix5_trace_c",
    ),
    opponents: ["historical_silver", "direct_frozen"],
    seeds: standardSeeds,
  },
  {
    label: "mega_reach",
    root: path.join(
      workspace,
      "metrics",
      "formal_v4_c3_public_survival_bench0_fix5_megalucario_reach1",
    ),
    opponents: [
      "mega_lucario_aib4",
      "mega_lucario_fujiborozoukin",
    ],
    seeds: megaSeeds,
  },
];
const collectorSummaryPath = path.join(
  staged,
  "metrics",
  "formal_v4_c3_public_survival_bench0_fix5_union_audit",
  "c3_mechanical_summary.json",
);
const outputPath = path.join(
  staged,
  "evaluations",
  "v4_c3_public_survival_bench0_fix5_combined_attempt1",
  "root_independent_metric_audit.json",
);
const expected = {
  candidateClosure:
    "5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134",
  launcher:
    "bcc98229b23c86fc5eb248d3f1e254337008ff4e85bd85224b3b3d6f570f1eea",
  commonModule:
    "78a0be6e87368939d7fce590e1aa65b5dffa228de224ffb53aa42c8de1ef295b",
  battleRunner:
    "e1aba0151cdaee425b858511aa760ce5c5647d555ddefbd69d7319c29c5b773b",
  emptySha:
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  gamesPerBlock: 10,
  maxSteps: 1000,
  watchdog: 180,
};

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex")
    .toUpperCase();
}

function jsonLines(file) {
  return fs
    .readFileSync(file, "utf8")
    .split(/\r?\n/u)
    .filter((line) => line.trim() !== "")
    .map((line, index) => {
      try {
        const value = JSON.parse(line);
        if (!value || typeof value !== "object" || Array.isArray(value)) {
          throw new Error("row is not an object");
        }
        return value;
      } catch (error) {
        throw new Error(`${file}:${index + 1}: ${error.message}`);
      }
    });
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((name) => `${JSON.stringify(name)}:${canonical(value[name])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function same(left, right) {
  return canonical(left) === canonical(right);
}

function blockKey(opponent, seat, seedBase) {
  return JSON.stringify([opponent, seat, seedBase]);
}

function gameKey(label, opponent, seat, seedBase, game, seed) {
  return JSON.stringify([
    label,
    opponent,
    seat,
    seedBase,
    game,
    seed,
  ]);
}

const suiteResults = [];
const globalGameKeys = new Map();
let totalBlocks = 0;
let totalGames = 0;
let globalFaultCount = 0;

for (const spec of suiteSpecs) {
  const manifestPath = path.join(spec.root, "suite_manifest.json");
  const ledgerPath = path.join(spec.root, "block_ledger.jsonl");
  const executionPath = path.join(
    spec.root,
    "suite_execution_summary.json",
  );
  for (const file of [manifestPath, ledgerPath, executionPath]) {
    if (!fs.existsSync(file)) throw new Error(`Missing metric input: ${file}`);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const ledger = jsonLines(ledgerPath);
  const execution = JSON.parse(fs.readFileSync(executionPath, "utf8"));
  const expectedBlockKeys = new Set();
  for (const opponent of spec.opponents) {
    for (const seat of [0, 1]) {
      for (const seedBase of spec.seeds) {
        expectedBlockKeys.add(blockKey(opponent, seat, seedBase));
      }
    }
  }
  const actualBlockCounts = new Map();
  const faults = {
    manifest: 0,
    missing_block: 0,
    unexpected_block: 0,
    duplicate_block: 0,
    incomplete_block: 0,
    nonzero_exit: 0,
    timeout: 0,
    stderr_nonempty: 0,
    summary_status: 0,
    missing_summary: 0,
    summary_hash: 0,
    summary_rows: 0,
    missing_game: 0,
    unexpected_game: 0,
    duplicate_game: 0,
    not_started: 0,
    hit_max_steps: 0,
    action_errors: 0,
    invalid_result: 0,
    seed_formula: 0,
    missing_trace: 0,
    empty_trace: 0,
    execution_summary: 0,
  };
  faults.manifest += manifest.schema_version !== "alakazam-staged-metrics-v1";
  faults.manifest += manifest.launcher_sha256 !== expected.launcher;
  faults.manifest +=
    manifest.common_module_sha256 !== expected.commonModule;
  faults.manifest +=
    manifest.run_local_battle_sha256 !== expected.battleRunner;
  faults.manifest += manifest.games_per_block !== expected.gamesPerBlock;
  faults.manifest += manifest.max_steps !== expected.maxSteps;
  faults.manifest += manifest.watchdog_seconds !== expected.watchdog;
  faults.manifest += !same(manifest.seats, [0, 1]);
  faults.manifest += !same(manifest.seed_bases, spec.seeds);
  faults.manifest += !same(
    manifest.opponents.map((row) => row.name),
    spec.opponents,
  );
  faults.manifest +=
    manifest.versions.length !== 1 ||
    manifest.versions[0].name !== "candidate";

  for (const row of ledger) {
    const key = blockKey(row.opponent, row.seat, row.seed_base);
    actualBlockCounts.set(key, (actualBlockCounts.get(key) ?? 0) + 1);
    faults.incomplete_block += row.block_complete !== true;
    faults.nonzero_exit += row.return_code !== 0;
    faults.timeout += row.timed_out !== false;
    faults.stderr_nonempty +=
      String(row.stderr_sha256).toLowerCase() !== expected.emptySha;
    const status = row.summary_status;
    faults.summary_status +=
      !status ||
      status.rows !== expected.gamesPerBlock ||
      status.expected_rows !== expected.gamesPerBlock ||
      status.complete_game_index_set !== true ||
      !Array.isArray(status.parse_errors) ||
      status.parse_errors.length !== 0;
    const summaryPath = row.summary;
    if (typeof summaryPath !== "string" || !fs.existsSync(summaryPath)) {
      faults.missing_summary += 1;
      continue;
    }
    faults.summary_hash +=
      sha256File(summaryPath) !== String(row.summary_sha256).toUpperCase();
    const gameRows = jsonLines(summaryPath);
    faults.summary_rows += gameRows.length !== expected.gamesPerBlock;
    const expectedGameKeys = new Set(
      Array.from({ length: expected.gamesPerBlock }, (_, game) =>
        gameKey(
          spec.label,
          row.opponent,
          row.seat,
          row.seed_base,
          game,
          row.seed_base + game,
        ),
      ),
    );
    const blockGameCounts = new Map();
    for (const gameRow of gameRows) {
      const key = gameKey(
        spec.label,
        row.opponent,
        row.seat,
        row.seed_base,
        gameRow.game,
        gameRow.seed,
      );
      blockGameCounts.set(key, (blockGameCounts.get(key) ?? 0) + 1);
      globalGameKeys.set(key, (globalGameKeys.get(key) ?? 0) + 1);
      faults.not_started += gameRow.started !== true;
      faults.hit_max_steps += gameRow.hit_max_steps !== false;
      faults.action_errors += gameRow.action_errors !== 0;
      faults.invalid_result +=
        gameRow.result !== 0 && gameRow.result !== 1;
      faults.seed_formula +=
        gameRow.seed !== row.seed_base + gameRow.game;
      if (
        typeof gameRow.trace !== "string" ||
        !fs.existsSync(gameRow.trace)
      ) {
        faults.missing_trace += 1;
      } else {
        faults.empty_trace += fs.statSync(gameRow.trace).size === 0;
      }
    }
    faults.missing_game += [...expectedGameKeys].filter(
      (key) => !blockGameCounts.has(key),
    ).length;
    faults.unexpected_game += [...blockGameCounts.keys()].filter(
      (key) => !expectedGameKeys.has(key),
    ).length;
    faults.duplicate_game += [...blockGameCounts.values()].filter(
      (count) => count !== 1,
    ).length;
    totalGames += gameRows.length;
  }
  faults.missing_block += [...expectedBlockKeys].filter(
    (key) => !actualBlockCounts.has(key),
  ).length;
  faults.unexpected_block += [...actualBlockCounts.keys()].filter(
    (key) => !expectedBlockKeys.has(key),
  ).length;
  faults.duplicate_block += [...actualBlockCounts.values()].filter(
    (count) => count !== 1,
  ).length;
  faults.execution_summary +=
    execution.schema_version !== "alakazam-staged-metrics-v1" ||
    execution.all_blocks_complete !== true ||
    execution.blocks !== expectedBlockKeys.size ||
    execution.complete_blocks !== expectedBlockKeys.size ||
    execution.failed_or_partial_blocks !== 0;
  const faultCount = Object.values(faults).reduce(
    (total, count) => total + Number(count),
    0,
  );
  globalFaultCount += faultCount;
  totalBlocks += ledger.length;
  suiteResults.push({
    label: spec.label,
    root: spec.root,
    expected_blocks: expectedBlockKeys.size,
    ledger_rows: ledger.length,
    games: ledger.length * expected.gamesPerBlock,
    manifest_sha256: sha256File(manifestPath),
    ledger_sha256: sha256File(ledgerPath),
    execution_summary_sha256: sha256File(executionPath),
    faults,
    fault_count: faultCount,
    integrity_gate: faultCount === 0 ? "PASS" : "FAIL",
  });
}

const globalDuplicateGames = [...globalGameKeys.values()].filter(
  (count) => count !== 1,
).length;
globalFaultCount += globalDuplicateGames;

if (!fs.existsSync(collectorSummaryPath)) {
  throw new Error(`Missing union collector summary: ${collectorSummaryPath}`);
}
const collector = JSON.parse(
  fs.readFileSync(collectorSummaryPath, "utf8"),
);
const collectorFaults = {
  schema:
    collector.schema_version !== "c3-raw-sidecar-mechanism-v4" ? 1 : 0,
  closure:
    collector.candidate_closure_sha256 !== expected.candidateClosure
      ? 1
      : 0,
  suite_count:
    collector.input_suite_count !== suiteSpecs.length ? 1 : 0,
  sidecar_count: collector.input_file_count !== 900 ? 1 : 0,
  callback_pair:
    collector.callback_start_count !== collector.callback_end_count ? 1 : 0,
  integrity: collector.integrity_gate !== "PASS" ? 1 : 0,
  duplicate: collector.duplicate_callback_key_count,
  unmatched_start: collector.unmatched_callback_start_count,
  unmatched_end: collector.unmatched_callback_end_count,
  missing_trace: collector.missing_or_wrong_trace_count,
  closure_mismatch: collector.closure_mismatch_count,
  unsupported_action: collector.unsupported_action_change_count,
  transaction: collector.transaction_fault_count,
  metric_exception: collector.metric_exception_count,
  wrapper_exception: collector.wrapper_exception_count,
  structural_invalid: collector.structural_invalid_count,
  decision_conflict: collector.decision_conflict_count,
  state_conflict: collector.state_evidence_conflict_count,
  identity_invalid: collector.identity_invalid_count,
  pairless_sidecar: collector.sidecar_without_local_pair_count,
};
const collectorFaultCount = Object.values(collectorFaults).reduce(
  (total, count) => total + Number(count),
  0,
);
globalFaultCount += collectorFaultCount;

const result = {
  schema_version: "v4-c3-fix5-root-metric-audit-v1",
  suites: suiteResults,
  schedule: {
    blocks: totalBlocks,
    expected_blocks: 90,
    games: totalGames,
    expected_games: 900,
    unique_game_keys: globalGameKeys.size,
    duplicate_game_keys: globalDuplicateGames,
  },
  collector: {
    path: collectorSummaryPath,
    sha256: sha256File(collectorSummaryPath),
    faults: collectorFaults,
    fault_count: collectorFaultCount,
    integrity_gate: collector.integrity_gate,
    reach_gate: collector.reach_gate,
    overall_gate: collector.overall_gate,
    supported_threat_count: collector.supported_threat_count,
    promotion_removal_context_count:
      collector.promotion_removal_context_count,
    continuity_counts: collector.continuity_counts,
    reach_guard_class_counts: collector.reach_guard_class_counts,
    reach_seats: collector.reach_seats,
    reach_opponents: collector.reach_opponents,
  },
  gates: {
    raw_integrity:
      globalFaultCount === 0 &&
      totalBlocks === 90 &&
      totalGames === 900 &&
      globalGameKeys.size === 900
        ? "PASS"
        : "FAIL",
    reach: collector.reach_gate,
    overall:
      globalFaultCount === 0 &&
      totalBlocks === 90 &&
      totalGames === 900 &&
      globalGameKeys.size === 900 &&
      collector.reach_gate === "PASS"
        ? "PASS"
        : globalFaultCount === 0
          ? "INSUFFICIENT_EVIDENCE"
          : "FAIL",
  },
};

fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(
  JSON.stringify({
    output: outputPath,
    blocks: totalBlocks,
    games: totalGames,
    raw_integrity: result.gates.raw_integrity,
    reach: result.gates.reach,
    supported_threat_count: collector.supported_threat_count,
  }),
);

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const workspace = path.resolve(process.argv[2] ?? process.cwd());
const combinedDir = path.join(
  workspace,
  "alakazam_staged_20260729",
  "evaluations",
  "v4_c3_public_survival_bench0_fix5_combined_attempt1",
);
const csvPath = path.join(combinedDir, "combined_paired_results.csv");
const validationPath = path.join(combinedDir, "validation_report.json");
const runnerReportPath = path.join(
  combinedDir,
  "root_combined_runner_report.json",
);
const outputPath = path.join(
  combinedDir,
  "root_independent_paired_audit.json",
);

const opponents = [
  "marnie",
  "cynthia",
  "alakazam_mirror",
  "rocket_mewtwo_spidops_proxy",
  "kangaskhan_crustle",
  "historical_silver",
  "direct_frozen",
];
const seedBases = [
  202608500,
  202608510,
  202608520,
  202608530,
  202608540,
];
const seats = [0, 1];
const games = Array.from({ length: 10 }, (_, index) => index);
const adjacentOpponents = opponents.filter(
  (opponent) => opponent !== "historical_silver",
);
const expectedHeader = [
  "seed_base",
  "opponent",
  "seat",
  "game",
  "seed",
  "baseline_result",
  "candidate_result",
  "baseline_win",
  "candidate_win",
  "baseline_steps",
  "candidate_steps",
];
const oneSidedT95Df49 = 1.6765508926168537;

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex")
    .toUpperCase();
}

function strictInteger(value, label) {
  if (!/^-?\d+$/u.test(value)) {
    throw new Error(`${label}: expected integer, got ${JSON.stringify(value)}`);
  }
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error(`${label}: unsafe integer ${value}`);
  }
  return parsed;
}

function parseCsv(file) {
  const lines = fs
    .readFileSync(file, "utf8")
    .replace(/^\uFEFF/u, "")
    .trimEnd()
    .split(/\r?\n/u);
  const header = lines.shift().split(",");
  if (JSON.stringify(header) !== JSON.stringify(expectedHeader)) {
    throw new Error(`Unexpected CSV header: ${JSON.stringify(header)}`);
  }
  return lines.map((line, index) => {
    const values = line.split(",");
    if (values.length !== header.length) {
      throw new Error(`CSV row ${index + 2}: wrong column count`);
    }
    const raw = Object.fromEntries(
      header.map((name, column) => [name, values[column]]),
    );
    const row = { opponent: raw.opponent };
    for (const name of header.filter((name) => name !== "opponent")) {
      row[name] = strictInteger(raw[name], `CSV row ${index + 2} ${name}`);
    }
    return row;
  });
}

function key(parts) {
  return JSON.stringify(parts);
}

function sum(rows, field) {
  return rows.reduce((total, row) => total + row[field], 0);
}

function summarize(rows) {
  const baselineWins = sum(rows, "baseline_win");
  const candidateWins = sum(rows, "candidate_win");
  return {
    games: rows.length,
    baseline_wins: baselineWins,
    candidate_wins: candidateWins,
    delta: candidateWins - baselineWins,
  };
}

function byValues(rows, fields) {
  const groups = new Map();
  for (const row of rows) {
    const groupKey = key(fields.map((field) => row[field]));
    if (!groups.has(groupKey)) groups.set(groupKey, []);
    groups.get(groupKey).push(row);
  }
  return Object.fromEntries(
    [...groups.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([groupKey, groupRows]) => [
        groupKey,
        summarize(groupRows),
      ]),
  );
}

function seedClusterLowerBound(rows) {
  const clusters = new Map();
  for (const row of rows) {
    if (!clusters.has(row.seed)) clusters.set(row.seed, []);
    clusters.get(row.seed).push(row.candidate_win - row.baseline_win);
  }
  const values = [...clusters.values()].map(
    (cluster) =>
      cluster.reduce((total, value) => total + value, 0) / cluster.length,
  );
  const mean =
    values.reduce((total, value) => total + value, 0) / values.length;
  const variance =
    values.reduce(
      (total, value) => total + (value - mean) ** 2,
      0,
    ) /
    (values.length - 1);
  const standardDeviation = Math.sqrt(variance);
  const lowerBound =
    mean -
    (oneSidedT95Df49 * standardDeviation) / Math.sqrt(values.length);
  return {
    clusters: values.length,
    mean,
    standard_deviation: standardDeviation,
    lower_bound: lowerBound,
    lower_bound_pp: lowerBound * 100,
    critical_value: oneSidedT95Df49,
  };
}

const rows = parseCsv(csvPath);
const validation = JSON.parse(fs.readFileSync(validationPath, "utf8"));
const runnerReport = JSON.parse(fs.readFileSync(runnerReportPath, "utf8"));

const expectedKeys = new Set();
for (const seedBase of seedBases) {
  for (const opponent of opponents) {
    for (const seat of seats) {
      for (const game of games) {
        expectedKeys.add(
          key([opponent, seat, seedBase, game, seedBase + game]),
        );
      }
    }
  }
}

const actualCounts = new Map();
const rowFaults = {
  unknown_opponent: 0,
  unknown_seed_base: 0,
  invalid_seat: 0,
  invalid_game: 0,
  seed_formula: 0,
  invalid_result: 0,
  invalid_win_flag: 0,
  baseline_result_to_win: 0,
  candidate_result_to_win: 0,
  invalid_steps: 0,
};
for (const row of rows) {
  const rowKey = key([
    row.opponent,
    row.seat,
    row.seed_base,
    row.game,
    row.seed,
  ]);
  actualCounts.set(rowKey, (actualCounts.get(rowKey) ?? 0) + 1);
  rowFaults.unknown_opponent += !opponents.includes(row.opponent);
  rowFaults.unknown_seed_base += !seedBases.includes(row.seed_base);
  rowFaults.invalid_seat += !seats.includes(row.seat);
  rowFaults.invalid_game += !games.includes(row.game);
  rowFaults.seed_formula += row.seed !== row.seed_base + row.game;
  rowFaults.invalid_result +=
    !seats.includes(row.baseline_result) ||
    !seats.includes(row.candidate_result);
  rowFaults.invalid_win_flag +=
    !seats.includes(row.baseline_win) ||
    !seats.includes(row.candidate_win);
  rowFaults.baseline_result_to_win +=
    row.baseline_win !== Number(row.baseline_result === row.seat);
  rowFaults.candidate_result_to_win +=
    row.candidate_win !== Number(row.candidate_result === row.seat);
  rowFaults.invalid_steps +=
    row.baseline_steps <= 0 || row.candidate_steps <= 0;
}

const missingKeys = [...expectedKeys].filter(
  (rowKey) => !actualCounts.has(rowKey),
);
const unexpectedKeys = [...actualCounts.keys()].filter(
  (rowKey) => !expectedKeys.has(rowKey),
);
const duplicateKeys = [...actualCounts.entries()].filter(
  ([, count]) => count !== 1,
);

const overall = summarize(rows);
const paired = {
  gain: rows.filter(
    (row) => row.candidate_win === 1 && row.baseline_win === 0,
  ).length,
  loss: rows.filter(
    (row) => row.candidate_win === 0 && row.baseline_win === 1,
  ).length,
  tie: rows.filter(
    (row) => row.candidate_win === row.baseline_win,
  ).length,
};
const byOpponent = byValues(rows, ["opponent"]);
const bySeat = byValues(rows, ["seat"]);
const bySeedBase = byValues(rows, ["seed_base"]);
const byOpponentSeat = byValues(rows, ["opponent", "seat"]);
const byOpponentSeedBase = byValues(rows, [
  "opponent",
  "seed_base",
]);
const silverRows = rows.filter(
  (row) => row.opponent === "historical_silver",
);
const adjacentRows = rows.filter((row) =>
  adjacentOpponents.includes(row.opponent),
);
const silver = summarize(silverRows);
const adjacent = summarize(adjacentRows);
const silverSeat = byValues(silverRows, ["seat"]);
const silverBlocks = byValues(silverRows, ["seed_base"]);
const positiveSilverBlocks = Object.values(silverBlocks).filter(
  (block) => block.delta > 0,
).length;
const lowerBounds = {
  overall: seedClusterLowerBound(rows),
  adjacent: seedClusterLowerBound(adjacentRows),
  historical_silver: seedClusterLowerBound(silverRows),
};

const schedulePass =
  rows.length === 700 &&
  actualCounts.size === 700 &&
  missingKeys.length === 0 &&
  unexpectedKeys.length === 0 &&
  duplicateKeys.length === 0 &&
  Object.values(rowFaults).every((count) => count === 0);
const checkedValidationPass =
  validation.valid === true &&
  Array.isArray(validation.errors) &&
  validation.errors.length === 0;
const checkedRunnerAggregate = runnerReport.aggregates ?? null;
const runnerAggregateMatch =
  checkedRunnerAggregate !== null &&
  checkedRunnerAggregate.baseline_wins === overall.baseline_wins &&
  checkedRunnerAggregate.candidate_wins === overall.candidate_wins &&
  checkedRunnerAggregate.delta_wins === overall.delta &&
  checkedRunnerAggregate.games === overall.games;
const rawIntegrityPass =
  schedulePass && checkedValidationPass && runnerAggregateMatch;

const gateDetails = {
  candidate_absolute_floor: overall.candidate_wins >= 452,
  overall_positive: overall.delta > 0,
  historical_silver_delta: silver.delta >= 3,
  historical_silver_both_seats: Object.values(silverSeat).every(
    (row) => row.delta >= 0,
  ),
  historical_silver_positive_blocks: positiveSilverBlocks >= 2,
  adjacent_delta: adjacent.delta >= -2,
  every_opponent: Object.values(byOpponent).every(
    (row) => row.delta >= -2,
  ),
  every_opponent_seat: Object.values(byOpponentSeat).every(
    (row) => row.delta >= -2,
  ),
  overall_lower_bound:
    lowerBounds.overall.lower_bound_pp >= -1,
  adjacent_lower_bound:
    lowerBounds.adjacent.lower_bound_pp >= -1,
  historical_silver_lower_bound:
    lowerBounds.historical_silver.lower_bound_pp >= -3,
  raw_integrity: rawIntegrityPass,
};

const result = {
  schema_version: "v4-c3-fix5-root-paired-audit-v1",
  inputs: {
    csv: csvPath,
    csv_sha256: sha256File(csvPath),
    validation: validationPath,
    validation_sha256: sha256File(validationPath),
    runner_report: runnerReportPath,
    runner_report_sha256: sha256File(runnerReportPath),
  },
  schedule: {
    rows: rows.length,
    expected_rows: expectedKeys.size,
    unique_keys: actualCounts.size,
    missing_keys: missingKeys.length,
    unexpected_keys: unexpectedKeys.length,
    duplicate_keys: duplicateKeys.length,
    row_faults: rowFaults,
    checked_validation_pass: checkedValidationPass,
    checked_validation_errors: validation.errors,
    runner_aggregate_match: runnerAggregateMatch,
  },
  overall,
  paired,
  by_opponent: byOpponent,
  by_seat: bySeat,
  by_seed_base: bySeedBase,
  by_opponent_seat: byOpponentSeat,
  by_opponent_seed_base: byOpponentSeedBase,
  adjacent,
  historical_silver: {
    ...silver,
    by_seat: silverSeat,
    by_seed_base: silverBlocks,
    positive_seed_blocks: positiveSilverBlocks,
  },
  lower_bounds: lowerBounds,
  gates: {
    details: gateDetails,
    numerical:
      Object.entries(gateDetails)
        .filter(([name]) => name !== "raw_integrity")
        .every(([, passed]) => passed)
        ? "PASS"
        : "FAIL",
    raw_integrity: rawIntegrityPass ? "PASS" : "FAIL",
  },
  checked_runner_aggregate: checkedRunnerAggregate,
};

fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(
  JSON.stringify({
    output: outputPath,
    overall,
    paired,
    numerical_gate: result.gates.numerical,
    raw_integrity: result.gates.raw_integrity,
  }),
);

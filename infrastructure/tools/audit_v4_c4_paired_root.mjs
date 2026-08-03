import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const workspace = path.resolve(process.argv[2] ?? process.cwd());
const combinedDir = path.join(
  workspace,
  "alakazam_staged_20260729",
  "evaluations",
  "v4_c4_wall_shadow_fix6_combined_attempt2",
);
const csvPath = path.join(combinedDir, "combined_paired_results.csv");
const manifestPath = path.join(combinedDir, "combined_manifest.jsonl");
const validationPath = path.join(combinedDir, "validation_report.json");
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
const roles = ["baseline_a", "baseline_b", "candidate"];
const games = Array.from({ length: 10 }, (_, index) => index);
const csvHeader = [
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

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex")
    .toUpperCase();
}

function strictInt(value, label) {
  if (!/^-?\d+$/u.test(value)) throw new Error(`${label}: ${value}`);
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) throw new Error(`${label}: unsafe`);
  return parsed;
}

function lines(file) {
  return fs
    .readFileSync(file, "utf8")
    .replace(/^\uFEFF/u, "")
    .trimEnd()
    .split(/\r?\n/u);
}

function parseCsv(file) {
  const input = lines(file);
  const header = input.shift().split(",");
  if (JSON.stringify(header) !== JSON.stringify(csvHeader)) {
    throw new Error(`unexpected CSV header ${JSON.stringify(header)}`);
  }
  return input.map((line, index) => {
    const fields = line.split(",");
    if (fields.length !== header.length) {
      throw new Error(`CSV row ${index + 2}: column count`);
    }
    const raw = Object.fromEntries(
      header.map((name, column) => [name, fields[column]]),
    );
    const row = { opponent: raw.opponent };
    for (const name of header.filter((name) => name !== "opponent")) {
      row[name] = strictInt(raw[name], `row ${index + 2} ${name}`);
    }
    return row;
  });
}

function key(values) {
  return JSON.stringify(values);
}

function summaryPath(command) {
  const index = command.indexOf("--summary");
  if (index < 0 || index + 1 >= command.length) {
    throw new Error("manifest command missing --summary");
  }
  return path.resolve(command[index + 1]);
}

const rows = parseCsv(csvPath);
const manifests = lines(manifestPath).map((line) => JSON.parse(line));
const validation = JSON.parse(fs.readFileSync(validationPath, "utf8"));

const expectedPaired = new Set();
for (const seedBase of seedBases) {
  for (const opponent of opponents) {
    for (const seat of seats) {
      for (const game of games) {
        expectedPaired.add(
          key([seedBase, opponent, seat, game, seedBase + game]),
        );
      }
    }
  }
}
const actualPaired = new Map();
const rowFaults = {
  unknown_opponent: 0,
  unknown_seed_base: 0,
  invalid_seat: 0,
  invalid_game: 0,
  seed_formula: 0,
  invalid_result: 0,
  invalid_win: 0,
  result_win_relation: 0,
  invalid_steps: 0,
  result_mismatch: 0,
  win_mismatch: 0,
  step_mismatch: 0,
};
for (const row of rows) {
  const rowKey = key([
    row.seed_base,
    row.opponent,
    row.seat,
    row.game,
    row.seed,
  ]);
  actualPaired.set(rowKey, (actualPaired.get(rowKey) ?? 0) + 1);
  rowFaults.unknown_opponent += !opponents.includes(row.opponent);
  rowFaults.unknown_seed_base += !seedBases.includes(row.seed_base);
  rowFaults.invalid_seat += !seats.includes(row.seat);
  rowFaults.invalid_game += !games.includes(row.game);
  rowFaults.seed_formula += row.seed !== row.seed_base + row.game;
  rowFaults.invalid_result +=
    !seats.includes(row.baseline_result) ||
    !seats.includes(row.candidate_result);
  rowFaults.invalid_win +=
    !seats.includes(row.baseline_win) ||
    !seats.includes(row.candidate_win);
  rowFaults.result_win_relation +=
    row.baseline_win !== Number(row.baseline_result === row.seat) ||
    row.candidate_win !== Number(row.candidate_result === row.seat);
  rowFaults.invalid_steps +=
    row.baseline_steps <= 0 ||
    row.candidate_steps <= 0 ||
    row.baseline_steps > 1000 ||
    row.candidate_steps > 1000;
  rowFaults.result_mismatch +=
    row.baseline_result !== row.candidate_result;
  rowFaults.win_mismatch += row.baseline_win !== row.candidate_win;
  rowFaults.step_mismatch += row.baseline_steps !== row.candidate_steps;
}

const expectedManifest = new Set();
for (const seedBase of seedBases) {
  for (const opponent of opponents) {
    for (const seat of seats) {
      for (const role of roles) {
        expectedManifest.add(key([seedBase, opponent, seat, role]));
      }
    }
  }
}
const actualManifest = new Map();
const summaryRows = new Map();
const manifestFaults = {
  exit_code: 0,
  command_shape: 0,
  missing_summary: 0,
  summary_row_count: 0,
  summary_started: 0,
  summary_seed: 0,
  summary_action_errors: 0,
  summary_max_steps: 0,
  summary_result: 0,
  summary_steps: 0,
};
for (const record of manifests) {
  const manifestKey = key([
    record.seed_base,
    record.opponent,
    record.seat,
    record.role,
  ]);
  actualManifest.set(
    manifestKey,
    (actualManifest.get(manifestKey) ?? 0) + 1,
  );
  manifestFaults.exit_code += record.exit_code !== 0;
  manifestFaults.command_shape +=
    !Array.isArray(record.command) || !roles.includes(record.role);
  const file = summaryPath(record.command);
  if (!fs.existsSync(file)) {
    manifestFaults.missing_summary += 1;
    continue;
  }
  const values = lines(file).map((line) => JSON.parse(line));
  manifestFaults.summary_row_count += values.length !== 10;
  for (const value of values) {
    manifestFaults.summary_started += value.started !== true;
    manifestFaults.summary_seed +=
      value.seed !== record.seed_base + value.game;
    manifestFaults.summary_action_errors += value.action_errors !== 0;
    manifestFaults.summary_max_steps += value.hit_max_steps !== false;
    manifestFaults.summary_result += !seats.includes(value.result);
    manifestFaults.summary_steps +=
      !Number.isInteger(value.steps) ||
      value.steps <= 0 ||
      value.steps > 1000;
    summaryRows.set(
      key([
        record.seed_base,
        record.opponent,
        record.seat,
        record.role,
        value.game,
      ]),
      value,
    );
  }
}

let duplicateBaselineMismatches = 0;
let csvSummaryMismatches = 0;
for (const row of rows) {
  const baseKey = [
    row.seed_base,
    row.opponent,
    row.seat,
  ];
  const baselineA = summaryRows.get(
    key([...baseKey, "baseline_a", row.game]),
  );
  const baselineB = summaryRows.get(
    key([...baseKey, "baseline_b", row.game]),
  );
  const candidate = summaryRows.get(
    key([...baseKey, "candidate", row.game]),
  );
  if (!baselineA || !baselineB || !candidate) {
    csvSummaryMismatches += 1;
    continue;
  }
  duplicateBaselineMismatches +=
    baselineA.result !== baselineB.result ||
    baselineA.steps !== baselineB.steps;
  csvSummaryMismatches +=
    baselineA.result !== row.baseline_result ||
    baselineA.steps !== row.baseline_steps ||
    candidate.result !== row.candidate_result ||
    candidate.steps !== row.candidate_steps;
}

const missingPaired = [...expectedPaired].filter(
  (value) => !actualPaired.has(value),
).length;
const unexpectedPaired = [...actualPaired.keys()].filter(
  (value) => !expectedPaired.has(value),
).length;
const duplicatePaired = [...actualPaired.values()].filter(
  (count) => count !== 1,
).length;
const missingManifest = [...expectedManifest].filter(
  (value) => !actualManifest.has(value),
).length;
const unexpectedManifest = [...actualManifest.keys()].filter(
  (value) => !expectedManifest.has(value),
).length;
const duplicateManifest = [...actualManifest.values()].filter(
  (count) => count !== 1,
).length;

const baselineWins = rows.reduce(
  (total, row) => total + row.baseline_win,
  0,
);
const candidateWins = rows.reduce(
  (total, row) => total + row.candidate_win,
  0,
);
const gains = rows.filter(
  (row) => row.candidate_win > row.baseline_win,
).length;
const losses = rows.filter(
  (row) => row.candidate_win < row.baseline_win,
).length;
const ties = rows.length - gains - losses;
const pass =
  rows.length === 700 &&
  actualPaired.size === 700 &&
  missingPaired === 0 &&
  unexpectedPaired === 0 &&
  duplicatePaired === 0 &&
  manifests.length === 210 &&
  actualManifest.size === 210 &&
  summaryRows.size === 2100 &&
  missingManifest === 0 &&
  unexpectedManifest === 0 &&
  duplicateManifest === 0 &&
  Object.values(rowFaults).every((value) => value === 0) &&
  Object.values(manifestFaults).every((value) => value === 0) &&
  duplicateBaselineMismatches === 0 &&
  csvSummaryMismatches === 0 &&
  validation.valid === true &&
  Array.isArray(validation.errors) &&
  validation.errors.length === 0;

const result = {
  schema_version: "v4-c4-root-paired-audit-v1",
  inputs: {
    paired_csv: csvPath,
    paired_csv_sha256: sha256File(csvPath),
    manifest: manifestPath,
    manifest_sha256: sha256File(manifestPath),
    validation: validationPath,
    validation_sha256: sha256File(validationPath),
  },
  schedule: {
    paired_rows: rows.length,
    paired_unique_keys: actualPaired.size,
    paired_missing: missingPaired,
    paired_unexpected: unexpectedPaired,
    paired_duplicates: duplicatePaired,
    manifest_rows: manifests.length,
    manifest_unique_keys: actualManifest.size,
    manifest_missing: missingManifest,
    manifest_unexpected: unexpectedManifest,
    manifest_duplicates: duplicateManifest,
    summary_rows: summaryRows.size,
  },
  faults: {
    rows: rowFaults,
    manifests: manifestFaults,
    duplicate_baseline_mismatches: duplicateBaselineMismatches,
    csv_summary_mismatches: csvSummaryMismatches,
  },
  results: {
    games: rows.length,
    baseline_wins: baselineWins,
    candidate_wins: candidateWins,
    delta: candidateWins - baselineWins,
    gain: gains,
    loss: losses,
    tie: ties,
  },
  checked_validation: {
    valid: validation.valid,
    errors: validation.errors,
  },
  verdict: pass ? "PASS" : "FAIL",
};

fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ output: outputPath, ...result.results, verdict: result.verdict }));

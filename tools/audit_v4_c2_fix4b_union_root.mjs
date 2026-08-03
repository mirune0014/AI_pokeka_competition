import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const workspace = path.resolve(
  process.argv[2] ?? process.cwd(),
);
const staged = path.join(workspace, "alakazam_staged_20260729");
const suiteRoots = [
  path.join(
    staged,
    "metrics",
    "formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_a",
  ),
  path.join(
    staged,
    "metrics",
    "formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_b",
  ),
  path.join(
    staged,
    "metrics",
    "formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_c_retry2",
  ),
];

const expected = {
  candidateClosure:
    "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157",
  parentClosure:
    "DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47",
  ruleVersion: "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
  opponents: [
    "alakazam_mirror",
    "cynthia",
    "direct_frozen",
    "historical_silver",
    "kangaskhan_crustle",
    "marnie",
    "rocket_mewtwo_spidops_proxy",
  ],
  seats: [0, 1],
  seedBases: [202608500, 202608510, 202608520, 202608530, 202608540],
  games: Array.from({ length: 10 }, (_, index) => index),
  aggregateHashes: [
    {
      ledger:
        "A441F1FB39B4E112D1B9CFFC40891C4B44F011F37C44058A0363637EFF7C1411",
      rows:
        "A465F0CD8A88A3EF7EBA54887EDEE3CC9AAAEF4EA969BF5CC4CF281A062D9324",
    },
    {
      ledger:
        "AA4D57ABE9992A579E787384B4E75292E69AE3D603E4B5B90A30CE01D1DAA2FD",
      rows:
        "92291A086B63FD99345384EE451E9C3C41648C33324B6C460E2C842DBC164522",
    },
    {
      ledger:
        "5B8EDE9B8178E5CEAF3EBDA2C21DA7BD2917C878C251059623903EA737E81B44",
      rows:
        "252AD8DEA259B16745C9150DEC5ADC11A0A1A9CD34D29B894ED71DEC84D878A2",
    },
  ],
};

function sha256File(file) {
  const hash = crypto.createHash("sha256");
  const fd = fs.openSync(file, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    while (true) {
      const bytes = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (bytes === 0) break;
      hash.update(buffer.subarray(0, bytes));
    }
  } finally {
    fs.closeSync(fd);
  }
  return hash.digest("hex").toUpperCase();
}

function jsonLines(file) {
  return fs
    .readFileSync(file, "utf8")
    .split(/\r?\n/u)
    .filter((line) => line.trim() !== "")
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`${file}:${index + 1}: ${error.message}`);
      }
    });
}

function deepSort(value) {
  if (Array.isArray(value)) return value.map(deepSort);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, deepSort(value[key])]),
    );
  }
  return value;
}

function canonical(value) {
  return JSON.stringify(deepSort(value));
}

function deepEqual(left, right) {
  return canonical(left) === canonical(right);
}

function increment(map, key, amount = 1) {
  map.set(key, (map.get(key) ?? 0) + amount);
}

function listFilesRecursive(root, predicate) {
  const result = [];
  const pending = [root];
  while (pending.length > 0) {
    const current = pending.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const resolved = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(resolved);
      else if (entry.isFile() && predicate(resolved)) result.push(resolved);
    }
  }
  return result.sort();
}

function candidateClosure(candidateRoot) {
  const members = fs
    .readdirSync(candidateRoot, { withFileTypes: true })
    .filter(
      (entry) =>
        entry.isFile() &&
        entry.name.endsWith(".py") &&
        !entry.name.startsWith("test"),
    )
    .map((entry) => path.join(candidateRoot, entry.name));
  members.push(
    path.join(candidateRoot, "runtime", "main.py"),
    path.join(candidateRoot, "deck.csv"),
  );
  const rows = members.map((file) => {
    const relative = path
      .relative(candidateRoot, file)
      .split(path.sep)
      .join("/");
    return `${relative}\0${sha256File(file)}\0${fs.statSync(file).size}\n`;
  });
  return crypto
    .createHash("sha256")
    .update(rows.sort().join(""), "utf8")
    .digest("hex")
    .toUpperCase();
}

const ledgerRows = [];
const gameRows = [];
const aggregateHashChecks = [];
const suiteManifestChecks = [];
const shardGameKeySets = [];
const allSidecars = [];

for (let shardIndex = 0; shardIndex < suiteRoots.length; shardIndex += 1) {
  const suiteRoot = suiteRoots[shardIndex];
  const ledgerFile = path.join(suiteRoot, "block_ledger.jsonl");
  const rowsFile = path.join(suiteRoot, "c2_shadow_rows.jsonl");
  const manifest = JSON.parse(
    fs.readFileSync(path.join(suiteRoot, "suite_manifest.json"), "utf8"),
  );
  const expectedHashes = expected.aggregateHashes[shardIndex];
  aggregateHashChecks.push({
    shard: shardIndex,
    ledgerActual: sha256File(ledgerFile),
    ledgerExpected: expectedHashes.ledger,
    ledgerMatches: sha256File(ledgerFile) === expectedHashes.ledger,
    rowsActual: sha256File(rowsFile),
    rowsExpected: expectedHashes.rows,
    rowsMatches: sha256File(rowsFile) === expectedHashes.rows,
  });
  suiteManifestChecks.push({
    shard: shardIndex,
    versionNames: manifest.versions?.map((row) => row.name).sort(),
    candidateTargets: manifest.versions?.map((row) =>
      path.resolve(row.target),
    ),
    opponents: manifest.opponents?.map((row) => row.name).sort(),
    seats: manifest.seats,
    seedBases: manifest.seed_bases,
    gamesPerBlock: manifest.games_per_block,
    maxSteps: manifest.max_steps,
    watchdogSeconds: manifest.watchdog_seconds,
  });

  for (const row of jsonLines(ledgerFile)) {
    ledgerRows.push({ shard: shardIndex, suiteRoot, ...row });
  }

  const summaryFiles = listFilesRecursive(
    path.join(suiteRoot, "runs", "c2"),
    (file) => path.basename(file) === "summary.jsonl",
  );
  const shardGameKeys = new Set();
  for (const summaryFile of summaryFiles) {
    const relative = path.relative(suiteRoot, summaryFile);
    const match = relative.match(
      /^runs[\\/]c2[\\/](.+?)[\\/]seed_(\d+)[\\/]seat_(\d+)[\\/]summary\.jsonl$/u,
    );
    if (!match) throw new Error(`Unexpected summary path: ${summaryFile}`);
    const [, opponent, seedBaseText, seatText] = match;
    const seedBase = Number(seedBaseText);
    const seat = Number(seatText);
    for (const row of jsonLines(summaryFile)) {
      const key = canonical([
        opponent,
        seat,
        seedBase,
        row.game,
        row.seed,
      ]);
      increment(
        new Map(),
        key,
      );
      shardGameKeys.add(key);
      gameRows.push({
        shard: shardIndex,
        opponent,
        seat,
        seedBase,
        summaryFile,
        ...row,
      });
    }
  }
  shardGameKeySets.push(shardGameKeys);

  const sidecars = listFilesRecursive(
    path.join(suiteRoot, "runs", "c2"),
    (file) =>
      path.basename(path.dirname(file)) === "sidecars" &&
      /^game_\d{4}\.jsonl$/u.test(path.basename(file)),
  );
  allSidecars.push(
    ...sidecars.map((file) => ({ shard: shardIndex, suiteRoot, file })),
  );
}

const expectedGameKeys = new Set();
for (const opponent of expected.opponents) {
  for (const seat of expected.seats) {
    for (const seedBase of expected.seedBases) {
      for (const game of expected.games) {
        expectedGameKeys.add(
          canonical([opponent, seat, seedBase, game, seedBase + game]),
        );
      }
    }
  }
}

const actualGameKeyCounts = new Map();
for (const row of gameRows) {
  increment(
    actualGameKeyCounts,
    canonical([
      row.opponent,
      row.seat,
      row.seedBase,
      row.game,
      row.seed,
    ]),
  );
}
const actualGameKeys = new Set(actualGameKeyCounts.keys());
const missingGameKeys = [...expectedGameKeys].filter(
  (key) => !actualGameKeys.has(key),
);
const unexpectedGameKeys = [...actualGameKeys].filter(
  (key) => !expectedGameKeys.has(key),
);
const duplicateGameKeys = [...actualGameKeyCounts.entries()].filter(
  ([, count]) => count !== 1,
);
let crossShardGameKeyOverlap = 0;
for (let left = 0; left < shardGameKeySets.length; left += 1) {
  for (let right = left + 1; right < shardGameKeySets.length; right += 1) {
    for (const key of shardGameKeySets[left]) {
      if (shardGameKeySets[right].has(key)) crossShardGameKeyOverlap += 1;
    }
  }
}

const ledgerScheduleKeys = new Map();
for (const row of ledgerRows) {
  increment(
    ledgerScheduleKeys,
    canonical([row.opponent, row.seat, row.seed_base]),
  );
}
const expectedBlockKeys = new Set();
for (const opponent of expected.opponents) {
  for (const seat of expected.seats) {
    for (const seedBase of expected.seedBases) {
      expectedBlockKeys.add(canonical([opponent, seat, seedBase]));
    }
  }
}

const gameFaults = {
  notStarted: 0,
  hitMaxSteps: 0,
  actionErrors: 0,
  invalidResult: 0,
  seedMismatch: 0,
  missingTrace: 0,
  emptyTrace: 0,
};
for (const row of gameRows) {
  if (row.started !== true) gameFaults.notStarted += 1;
  if (row.hit_max_steps !== false) gameFaults.hitMaxSteps += 1;
  if (row.action_errors !== 0) gameFaults.actionErrors += 1;
  // The checked local runner records the winning player index (0 or 1).
  if (row.result !== 0 && row.result !== 1) gameFaults.invalidResult += 1;
  if (row.seed !== row.seedBase + row.game) gameFaults.seedMismatch += 1;
  if (typeof row.trace !== "string" || !fs.existsSync(row.trace)) {
    gameFaults.missingTrace += 1;
  } else if (fs.statSync(row.trace).size === 0) {
    gameFaults.emptyTrace += 1;
  }
}

const callbackStarts = new Map();
const callbackEnds = new Map();
const fingerprintCallbacks = new Map();
const fingerprintClasses = new Map();
const fingerprintPayloads = new Map();
const callbackOpponents = new Set();
const callbackSeats = new Set();
const callbackFaults = {
  malformedPath: 0,
  malformedJsonObject: 0,
  duplicateStartKeys: 0,
  duplicateEndKeys: 0,
  unmatchedStarts: 0,
  unmatchedEnds: 0,
  wrapperExceptions: 0,
  structuralInvalid: 0,
  missingOrWrongTrace: 0,
  actionIdentity: 0,
  metricExceptions: 0,
  wrongCandidateClosure: 0,
  wrongParentClosure: 0,
  emptySidecars: 0,
};
const routeClasses = [
  "CERTIFIED",
  "POSSIBLE",
  "IMPOSSIBLE",
  "UNKNOWN",
];

for (const { suiteRoot, file } of allSidecars) {
  if (fs.statSync(file).size === 0) callbackFaults.emptySidecars += 1;
  const relative = path.relative(suiteRoot, file);
  const match = relative.match(
    /^runs[\\/]c2[\\/](.+?)[\\/]seed_(\d+)[\\/]seat_(\d+)[\\/]sidecars[\\/]game_(\d{4})\.jsonl$/u,
  );
  if (!match) {
    callbackFaults.malformedPath += 1;
    continue;
  }
  const [, pathOpponent, pathSeedBase, pathSeat] = match;
  for (const event of jsonLines(file)) {
    if (!event || typeof event !== "object" || Array.isArray(event)) {
      callbackFaults.malformedJsonObject += 1;
      continue;
    }
    const callbackKey = canonical([
      event.version ?? "c2",
      event.opponent ?? pathOpponent,
      event.policy_seat ?? Number(pathSeat),
      event.seed_base ?? Number(pathSeedBase),
      event.seed,
      event.game,
      event.callback_ordinal,
    ]);
    if (event.event === "CALL_START") {
      increment(callbackStarts, callbackKey);
      continue;
    }
    if (event.event !== "CALL_END") continue;
    increment(callbackEnds, callbackKey);
    callbackOpponents.add(event.opponent ?? pathOpponent);
    callbackSeats.add(event.policy_seat ?? Number(pathSeat));
    if (event.exception !== null) callbackFaults.wrapperExceptions += 1;
    if (event.structurally_valid !== true) {
      callbackFaults.structuralInvalid += 1;
    }
    const trace = event.version_trace;
    if (
      event.version_trace_name !== "LAST_STAGED_POLICY_TRACE" ||
      !trace ||
      typeof trace !== "object" ||
      trace.rule_version !== expected.ruleVersion ||
      typeof trace.observation_fingerprint !== "string" ||
      trace.observation_fingerprint.length === 0
    ) {
      callbackFaults.missingOrWrongTrace += 1;
      continue;
    }
    if (trace.candidate_closure_sha256 !== expected.candidateClosure) {
      callbackFaults.wrongCandidateClosure += 1;
    }
    if (trace.parent_closure_sha256 !== expected.parentClosure) {
      callbackFaults.wrongParentClosure += 1;
    }
    const identity = trace.action_identity;
    const identityOk =
      identity &&
      identity.value_equal === true &&
      identity.type_equal === true &&
      identity.order_equal === true &&
      identity.returned_parent_object_unchanged === true &&
      typeof trace.action_python_type === "string" &&
      deepEqual(trace.raw_parent_action, trace.applied_action) &&
      deepEqual(trace.raw_parent_action, event.selected_action);
    if (!identityOk) callbackFaults.actionIdentity += 1;
    if (trace.metric_exception !== null) callbackFaults.metricExceptions += 1;

    const fingerprint = trace.observation_fingerprint;
    increment(fingerprintCallbacks, fingerprint);
    if (!fingerprintClasses.has(fingerprint)) {
      fingerprintClasses.set(fingerprint, new Set());
    }
    let emitted = false;
    for (const route of trace.route_rows ?? []) {
      for (const field of [
        "primary_distance",
        "fallback_attack_distance",
      ]) {
        const distance = route?.[field];
        if (!distance || typeof distance !== "object") continue;
        const routeClass = routeClasses.includes(distance.route_class)
          ? distance.route_class
          : "UNKNOWN";
        fingerprintClasses.get(fingerprint).add(routeClass);
        emitted = true;
      }
    }
    if (!emitted) fingerprintClasses.get(fingerprint).add("UNKNOWN");
    if (!fingerprintPayloads.has(fingerprint)) {
      fingerprintPayloads.set(fingerprint, new Set());
    }
    fingerprintPayloads.get(fingerprint).add(
      canonical({
        route_rows: trace.route_rows,
        best_primary_route: trace.best_primary_route,
        best_fallback_route: trace.best_fallback_route,
        unsupported_reasons: trace.unsupported_reasons,
      }),
    );
  }
}

for (const count of callbackStarts.values()) {
  if (count > 1) callbackFaults.duplicateStartKeys += count - 1;
}
for (const count of callbackEnds.values()) {
  if (count > 1) callbackFaults.duplicateEndKeys += count - 1;
}
const allCallbackKeys = new Set([
  ...callbackStarts.keys(),
  ...callbackEnds.keys(),
]);
for (const key of allCallbackKeys) {
  const starts = callbackStarts.get(key) ?? 0;
  const ends = callbackEnds.get(key) ?? 0;
  if (starts > ends) callbackFaults.unmatchedStarts += starts - ends;
  if (ends > starts) callbackFaults.unmatchedEnds += ends - starts;
}

const classUniqueStateCounts = Object.fromEntries(
  routeClasses.map((routeClass) => [
    routeClass,
    [...fingerprintClasses.values()].filter((classes) =>
      classes.has(routeClass),
    ).length,
  ]),
);
const fingerprintConflictCount = [...fingerprintPayloads.values()].filter(
  (payloads) => payloads.size > 1,
).length;

const candidateRoot = path.join(
  staged,
  "versions",
  "alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b",
);
const actualCandidateClosure = candidateClosure(candidateRoot);

const result = {
  schemaVersion: "v4-c2-fix4b-root-audit-v1",
  inputs: {
    suiteRoots,
    aggregateHashChecks,
    suiteManifestChecks,
    candidateRoot,
    expectedCandidateClosure: expected.candidateClosure,
    actualCandidateClosure,
    candidateClosureMatches:
      actualCandidateClosure === expected.candidateClosure,
  },
  schedule: {
    ledgerRows: ledgerRows.length,
    expectedBlocks: expectedBlockKeys.size,
    uniqueLedgerBlockKeys: ledgerScheduleKeys.size,
    missingLedgerBlockKeys: [...expectedBlockKeys].filter(
      (key) => !ledgerScheduleKeys.has(key),
    ).length,
    unexpectedLedgerBlockKeys: [...ledgerScheduleKeys.keys()].filter(
      (key) => !expectedBlockKeys.has(key),
    ).length,
    duplicateLedgerBlockKeys: [...ledgerScheduleKeys.values()].filter(
      (count) => count !== 1,
    ).length,
    incompleteBlocks: ledgerRows.filter((row) => row.block_complete !== true)
      .length,
    nonzeroExitBlocks: ledgerRows.filter((row) => row.return_code !== 0)
      .length,
    timedOutBlocks: ledgerRows.filter((row) => row.timed_out !== false)
      .length,
    incompleteSummaryBlocks: ledgerRows.filter(
      (row) =>
        row.summary_status?.rows !== 10 ||
        row.summary_status?.expected_rows !== 10 ||
        row.summary_status?.complete_game_index_set !== true ||
        (row.summary_status?.parse_errors?.length ?? 0) !== 0,
    ).length,
    gameRows: gameRows.length,
    expectedGames: expectedGameKeys.size,
    uniqueGameKeys: actualGameKeys.size,
    missingGameKeys: missingGameKeys.length,
    unexpectedGameKeys: unexpectedGameKeys.length,
    duplicateGameKeys: duplicateGameKeys.length,
    crossShardGameKeyOverlap,
    gameFaults,
  },
  callbacks: {
    sidecarFiles: allSidecars.length,
    callbackStarts: [...callbackStarts.values()].reduce(
      (total, count) => total + count,
      0,
    ),
    callbackEnds: [...callbackEnds.values()].reduce(
      (total, count) => total + count,
      0,
    ),
    uniqueCallbackKeys: allCallbackKeys.size,
    uniqueDecisionFingerprints: fingerprintCallbacks.size,
    duplicateDecisionCallbacks: [...fingerprintCallbacks.values()].reduce(
      (total, count) => total + Math.max(0, count - 1),
      0,
    ),
    fingerprintConflictCount,
    classUniqueStateCounts,
    opponents: [...callbackOpponents].sort(),
    seats: [...callbackSeats].sort(),
    callbackFaults,
  },
};

const schedulePass =
  result.schedule.ledgerRows === 70 &&
  result.schedule.uniqueLedgerBlockKeys === 70 &&
  result.schedule.missingLedgerBlockKeys === 0 &&
  result.schedule.unexpectedLedgerBlockKeys === 0 &&
  result.schedule.duplicateLedgerBlockKeys === 0 &&
  result.schedule.incompleteBlocks === 0 &&
  result.schedule.nonzeroExitBlocks === 0 &&
  result.schedule.timedOutBlocks === 0 &&
  result.schedule.incompleteSummaryBlocks === 0 &&
  result.schedule.gameRows === 700 &&
  result.schedule.uniqueGameKeys === 700 &&
  result.schedule.missingGameKeys === 0 &&
  result.schedule.unexpectedGameKeys === 0 &&
  result.schedule.duplicateGameKeys === 0 &&
  result.schedule.crossShardGameKeyOverlap === 0 &&
  Object.values(gameFaults).every((count) => count === 0);
const integrityPass =
  allSidecars.length === 700 &&
  [...callbackStarts.values()].reduce((a, b) => a + b, 0) ===
    [...callbackEnds.values()].reduce((a, b) => a + b, 0) &&
  Object.values(callbackFaults).every((count) => count === 0) &&
  fingerprintConflictCount === 0 &&
  actualCandidateClosure === expected.candidateClosure &&
  aggregateHashChecks.every(
    (row) => row.ledgerMatches && row.rowsMatches,
  );
const reachPass =
  fingerprintCallbacks.size >= 50 &&
  expected.opponents.every((opponent) => callbackOpponents.has(opponent)) &&
  expected.seats.every((seat) => callbackSeats.has(seat)) &&
  routeClasses.every(
    (routeClass) => classUniqueStateCounts[routeClass] >= 5,
  );
result.gates = {
  schedule: schedulePass ? "PASS" : "FAIL",
  integrity: integrityPass ? "PASS" : "FAIL",
  reach: reachPass ? "PASS" : "INSUFFICIENT_EVIDENCE",
  overall:
    schedulePass && integrityPass && reachPass
      ? "PASS"
      : schedulePass && integrityPass
        ? "INSUFFICIENT_EVIDENCE"
        : "FAIL",
};

console.log(JSON.stringify(result, null, 2));

# PTCG Competition Agent Workflow

The root agent owns planning, experiment selection, evidence synthesis, documentation updates, and every external Kaggle write. Subagents perform bounded work and return compact evidence.

## Current technical policy

- The active development path is pure, deterministic rule-based play. Do not
  implement or promote residual RL, learned action rankers, behavior cloning,
  Gold-action imitation, or replay-derived opponent-policy proxies unless the
  user explicitly reauthorizes them in a later instruction.
- Replays are evidence for deck theory, board-state diagnosis, resource and
  prize sequencing, and live failure analysis. They are not action labels to
  imitate.
- Use the exact historical-Silver Archaludon submission as the primary fully
  executable strength anchor. Keep additional complete historical agents as an
  anti-overfitting population.
- Follow the improvement loop that produced the strongest Archaludon agent:
  preserve the strongest known baseline, understand the deck's complete game
  plan, select one interpretable rule hypothesis, implement it in isolation,
  compare both seats on identical seeds, inspect the changed positions, and
  retain it only when absolute strength and adjacent matchups remain sound.
- Evaluate setup, board formation, backup readiness, resource use, attack
  continuity, prize exchange, disruption, tactical conversion, and matchup
  results together. Do not optimize only a loss bucket or only a win-plan
  metric.

## Model policy

- Keep the root agent on `gpt-5.6-sol` with `xhigh` reasoning for coordination,
  raw-evidence verification, documentation, packaging, and every external
  Kaggle write.
- Use `gpt-5.6-luna` with `low` reasoning only for deterministic command execution,
  log collection, and fixed-schedule simulation. These agents may relay exact
  tool output, paths, exit codes, hashes, and row counts, but must not interpret
  rates, deltas, uncertainty, trends, recovery, or promotion evidence.
- Use `gpt-5.6-sol` with `ultra` reasoning from the start for every task that
  interprets numerical evidence: win-rate aggregation, paired deltas, seat or
  seed sensitivity, confidence intervals, bucket floors, live-score trends,
  candidate comparison, and pass/fail recommendations.
- Use `gpt-5.6-sol` with `ultra` reasoning for qualitative replay diagnosis.
- Use `gpt-5.6-sol` with `xhigh` reasoning for every concrete rule
  implementation, including isolated candidate edits.
- Use the dedicated `ptcg_sol_ultra_worker` on `gpt-5.6-sol` with `ultra`
  reasoning for rule-improvement direction, hypothesis formulation and
  selection, and the final accept/reject judgment after evaluation. It is a
  read-only strategy judge: implementation remains Sol xhigh, and the root
  retains external Kaggle ownership.
- Do not use Sol Ultra for log collection, deterministic simulation execution,
  or routine packaging. Numerical evaluation and qualitative replay
  interpretation explicitly belong to Sol Ultra. Provide it the relevant raw
  paths, immutable comparison specification, constraints, and explicit decision
  question.

## Cost policy

- Do not spawn subagents for a trivial answer or a single cheap command.
- Use `ptcg_log_collector` for the multi-command fetch/classify pipeline, but
  treat its numeric output as unexamined raw evidence.
- Use at most two Sol-Ultra `ptcg_replay_analyst` instances in parallel, one per
  independent matchup bucket.
- Use one Sol-xhigh `ptcg_candidate_worker` only after the Sol-Ultra strategy
  judge selects a concrete hypothesis.
- Use at most one `ptcg_sol_ultra_worker` at a time. Invoke it first to select
  the rule hypothesis and again after numerical evaluation to judge adoption.
- Run `ptcg_eval_runner` after implementation to execute the immutable schedule.
  Then run the Sol-Ultra `ptcg_local_evaluator` over the raw outputs; do not run
  it concurrently with the candidate worker or before execution is complete.
- Close completed subagent threads promptly. Do not repeat work already represented by a fresh output file.
- Keep summaries compact; raw logs stay on disk.

## Coordination

1. The parent defines the current submission, baseline, loss buckets, and replacement threshold.
2. The log collector refreshes public evidence and stops early when nothing changed.
3. Independent Sol-Ultra replay analysts may inspect separate weak buckets in parallel.
4. The Sol-Ultra strategy judge selects one hypothesis from root-verified facts,
   and the parent gives the Sol-xhigh worker an isolated destination.
5. The low-cost evaluation runner executes the parent's immutable baseline and
   candidate schedule without interpreting the result.
6. The Sol-Ultra numerical evaluator independently recomputes the comparison
   from raw rows and reports uncertainty, floors, and regressions.
7. The parent verifies the critical columns again, then the Sol-Ultra strategy
   judge issues the rule-level accept/reject judgment. The root applies that
   judgment while retaining responsibility for packaging and external submission.

## Evidence authority and verification

Subagent prose is never authoritative evidence. Luna log collectors and
evaluation runners are execution operators: they may run parent-specified
commands and return raw output paths, command lines, exit codes, checksums, and
verbatim script output. They must not decide that an episode is new, a
submission is recovering, an archetype label is correct, a candidate improved,
or a submission is justified. Numerical interpretation starts with a Sol-Ultra
agent and is independently checked against the raw rows by the Sol-xhigh root.

Before delegation, the parent records an immutable comparison specification:

- source snapshot or episode CSV and its hash;
- expected episode IDs, or the previous ID set used for a set difference;
- baseline and candidate paths plus hashes;
- engine path, opponents, seats, seeds, and games per cell;
- exact output schema and destination.

After delegation, the root must verify submission-critical evidence directly:

1. Recompute `baseline_win` and `candidate_win` independently from raw rows.
2. Confirm unique `(panel, opponent, seat, seed)` keys and exact schedule equality.
3. Confirm row totals, exit codes, action errors, max-step hits, and duplicate controls.
4. Confirm replay IDs against the prior snapshot before using `new`, and inspect the
   score/game sequence before using `recovering`.
5. Treat archetype and causal labels as hypotheses until checked against the deck
   list and replay by the root.
6. Reject any custom LLM-authored aggregate that disagrees with the deterministic
   runner report or a root recomputation. Do not repair it silently; record the
   discrepancy.

`ptcg_eval_runner` must use checked repository runners and must not author a
custom aggregate. `ptcg_local_evaluator` reads the completed raw files and
recomputes all relevant columns with Sol Ultra. If no checked aggregator
supports the comparison, the numerical evaluator records its reproducible
calculation separately and the root verifies it. A subagent-generated Markdown
or JSON summary remains informational until the root validates every
submission-critical number. Never use a subagent recommendation alone as the
reason to consume a Kaggle slot.

## Kaggle submission policy

Use the established live-feedback submission loop in
`docs/gold_replay_distillation_goal.md`, section 14. The root agent does not
need per-submission user confirmation. It may use up to five daily slots for
locally justified candidates when the current and preceding mature
submissions remain below 1000. A clearly weak submission around 700 or below
may be replaced earlier after checking execution status and the initial loss
buckets. Do not replace a recovering submission without a valid candidate,
and record the hypothesis, paired local evidence, and target matchup before
using a slot.

This policy supersedes any later rule that required separate user approval for
each submission. Kaggle writes and final submission decisions remain exclusive
to the root agent.

Never run multiple source-writing agents at once. Read-heavy analysis may be parallel; candidate implementation is single-writer and sequential.

No subagent may submit to Kaggle, cancel or replace a submission, publish a Notebook or Discussion, expose credentials, or change Codex configuration. Those actions remain with the root agent under the submission policy above.

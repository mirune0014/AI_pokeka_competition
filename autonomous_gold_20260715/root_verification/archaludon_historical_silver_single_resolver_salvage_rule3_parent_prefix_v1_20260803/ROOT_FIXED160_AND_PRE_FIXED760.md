# Rule 3 parent-prefix v1: root fixed160 recomputation and pre-fixed760 freeze

Date: 2026-08-03 JST

## Frozen candidate

- Candidate `main.py`:
  `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Direct parent `main.py`:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Fixed160 overlay:
  `433DC2102AB5C6AFEBBC2253EAC3506E25D7651602DDE5E4032AA754D82018D9`
- Fixed160 runner:
  `83E084B44CBD844D30D71E5C47CDB135E08E6E37CD4708725A4232BD38866295`
- Independent numerical report:
  `E8E49D3AF720706F869148BB39BBE4A3B529351ED14CDC8BAE0F54BA3916AEAE`

## Root recomputation

Root independently read both `paired_results.csv` files, both manifests, all
candidate and baseline-A summaries, and all candidate and baseline-A trace
bytes.

- Paired rows / unique `(panel, opponent, seat, seed)` keys: `160/160`.
- Baseline wins / candidate wins: `100/100`.
- Paired gains / regressions / ties: `0/0/160`.
- Historical-Silver panel: `20/40 = 20/40`.
- Adjacent population: `80/120 = 80/120`.
- Every opponent/seat cell delta: `0`.
- Manifest rows / nonzero exits: `24/0`.
- Compared candidate plus baseline-A summaries: `320`.
- Action errors / max-step hits: `0/0`.
- Candidate versus baseline-A byte-trace matches: `160/160`.
- Checked-runner duplicate mismatch count: `0` in both panels.

These values match the independent Sol-Ultra audit exactly. Fixed160 passes
the retention, determinism, and execution-safety gates, but is not evidence of
a strength increase because its Rule 3 natural-start count is zero.

## Natural Rule 3 coverage

The separately checked engine verification supplies the required natural
coverage in both seats.

- Active-ex route, candidate seat 1, seed `271958323`: candidate and parent
  traces are byte-identical; candidate is the winner (`result=1`); Rule 3
  completes after preserving the full Silver setup prefix; irreversible abort
  faults `0`.
- Turbo route, candidate seat 0, seed `271958324`: candidate and parent traces
  are byte-identical; candidate loses (`result=1`), so this is behavior and
  transaction preservation evidence, not a win; Rule 3 completes;
  irreversible abort faults `0`.
- Former illegal first-turn route, candidate seat 0, seed `271958318`: no Rule
  3 start, and candidate/parent traces are byte-identical.

## Fixed760 authorization

Freeze the exact 760-key schedule from
`evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1/fixed760_spec.json`
and compare the direct parent against this candidate on identical opponents,
seats, and seeds. Use a new immutable output destination. Required checks are
760 unique keys, all duplicate controls, zero execution faults, candidate wins
at least `478/760`, paired gains at least regressions, Historical-Silver mirror
at least `98/200`, per-seat parent drop at most two wins, and per-adjacent-
opponent parent drop at most five wins. Inspect every candidate/parent trace
difference and every discordant result before adoption.

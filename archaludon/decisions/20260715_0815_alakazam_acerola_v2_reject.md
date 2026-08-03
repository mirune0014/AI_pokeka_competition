# Decision: reject Alakazam Acerola v2 final bridge

- Decision time: 2026-07-15 08:15:46 +09:00
- Decision: REJECT
- Kaggle submission: NO
- Daily submission slots consumed: 0
- Conditional trace stage: NOT_RUN_BY_SPEC

## Frozen evidence

- Evaluation specification:
  autonomous_gold_20260715/evaluations/alakazam_acerola_v2_seed2026071541/EVALUATION_SPEC.md
  - SHA256 9768C8466AEEF22019A459B399219F716D40B2506368A5B065DAEEB074290B34
- Runner report:
  autonomous_gold_20260715/evaluations/alakazam_acerola_v2_seed2026071541/full_run/report.json
  - SHA256 A8391FB690BC67B43ECF6ABD5E60EDD5EF8F41B493A038C6ED4F52C2A1307D0B
- Paired results:
  autonomous_gold_20260715/evaluations/alakazam_acerola_v2_seed2026071541/full_run/paired_results.csv
  - SHA256 22DDA47D30B6F14992B111616948EEC667B5E500BF2815EEE8D8289885CA9D14
- Manifest:
  autonomous_gold_20260715/evaluations/alakazam_acerola_v2_seed2026071541/full_run/manifest.jsonl
  - SHA256 3534A716C44EA2D279E5AC00E1FF38793B615916B1FB17A1F31ABC58F1045A0F
- Independent numerical audit:
  autonomous_gold_20260715/evaluations/alakazam_acerola_v2_seed2026071541/numerical_audit/numerical_audit.json
  - SHA256 34128732CD5BAD013B5A006CCCDBAAF5A3BA0890A16C0C69266E4ADD7D037EF4

## Root-verified result

- Integrity: all 27 frozen source hashes matched; 48/48 exits were zero;
  1,920 raw rows and 640 exact unique schedule keys were present; action
  errors, max-step hits, unstarted games, invalid results, duplicate-control
  mismatches, schedule mismatches, and runner/audit discrepancies were zero.
- Total: baseline 388, candidate 386, delta -2/640.
- Discordant pairs: 3 gains and 5 losses.
- Seat deltas: -1/320 and -1/320.
- Paired normal 95% interval: [-0.0117904463, 0.0055404463].
- Target panel: 281 to 277, delta -4/400.
- Adjacent panel: 107 to 109, delta +2/240.
- Historical-Silver: 34 to 33; candidate absolute result 33/80.

## Gate result and decision

- Gate 1 runner validity: PASS.
- Gate 2 absolute and paired strength: FAIL. Candidate absolute 386/640
  passed, but delta, both seats, and confidence-interval subchecks failed.
- Gate 3 target panel: FAIL.
- Gate 4 adjacent panel: PASS.
- Gate 5 Historical-Silver floor: FAIL.

Because Stage-1 gates 2, 3, and 5 failed, the predeclared 1,280-game trace
stage was not run. No causal claim is made about Acerola use, Battle Cage
absence, or the eight discordant outcomes without those traces.

The read-only Sol-Ultra strategy judge issued an unambiguous REJECT and
prohibited consuming a Kaggle slot.

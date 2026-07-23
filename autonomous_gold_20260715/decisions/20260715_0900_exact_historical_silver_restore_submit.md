# 2026-07-15 09:00 JST — Exact Historical-Silver Baseline Restore

## Decision

Use one live slot for the **unchanged exact Historical-Silver Archaludon**
archive. This is a baseline restore, not a claim that the Gold target has been
reached. No trace-derived experimental rule is included.

## Candidate identity

- Archive:
  `autonomous_gold_20260715/packages/anchors/submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
- Archive SHA256:
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`
- Root `main.py` SHA256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Root `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Dependencies: bundled `cg/` runtime and root `requirements.txt`; no model
  weights and no network dependency.

The archive files match the exact historical anchor. Package-runtime smoke:
`2/2` started, action errors `0`, max-step hits `0`.

## Local evidence

- Immutable broad panel: `520 / 640` wins (`81.25%`)
- Seats: `258 / 320`, `262 / 320`
- Opponents: self `40/80`, exact Alakazam `50/80`, Alakazam Rmy `62/80`,
  Marnie `74/80`, Mega Lucario `77/80`, Starmie `76/80`, Dragapult `76/80`,
  Cornerstone Ogerpon `65/80`
- Trace rerun matched all 640 prior `(opponent, seat, seed)` results and steps;
  action errors and max-step hits were `0`.
- Two independent trace buckets found no failure signature that survived both
  the numerical floor and matching-win continuity/safety checks. Therefore the
  exact anchor is safer than a speculative patch.

## Live replacement evidence

- Current submission `54697107`: `COMPLETE`, score `775.6`
- Current exact episode snapshot at 09:00: `53` unique completed games,
  `27-26`; latest episode `86008925` was a win from `769.5227894526231` to
  `775.677576261066`.
- Relative to the earlier exact 33-game snapshot, the 20-game increment is
  `11-9`, but the score remains below `782.7006415869863`.
- Previous submission `54695488`: `COMPLETE`, score `683.0`, `48` unique
  completed games (`31-17`).
- Both mature submissions remain below `1000`; the current one is also far
  below the current rank-20 score `1081.9`.

## Slot and timing checks

- Check time: `2026-07-15 09:00:16 JST`
- Kaggle UTC date `2026-07-15` submissions before this action: `0 / 5`
- Previous submit: `2026-07-14 19:23:35.043 UTC` = `2026-07-15 04:23:35 JST`
- Elapsed time: approximately `4 h 36 min`, above the three-hour cadence.

## Hypothesis and observation plan

Restoring the strongest executable broad-panel anchor should improve absolute
strength and board/resource continuity relative to the current experimental
Orbit policy, especially in the observed Alakazam and broad-meta buckets. This
does not guarantee Gold.

Immediately verify upload/validation status and execution errors. Then retain
the initial episode IDs and inspect matchup, setup, backup readiness, attack
continuity, prize exchange, and terminal conversion before considering another
slot. The scheduled three-hour loop continues rule diagnosis in parallel.

## Rollback

The prior live artifact remains at
`isolated_rule_agents/orbit_transfer_archaludon_20260715/orbit_archaludon_terminal_conversion_experimental_20260715.tar.gz`.
Rollback requires a fresh locally justified decision; no automatic score-only
rollback is authorized.

## External result

- Upload command exit: `0`
- Kaggle submission ID: `54704652`
- Submitted at: `2026-07-15 00:01:15 UTC` (`09:01:15 JST`)
- Initial status: `SubmissionStatus.PENDING`
- UTC-day usage after upload: `1 / 5`
- Uploaded archive SHA256 (immediately before upload):
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`

### Validation

- Status changed to `SubmissionStatus.COMPLETE`.
- Validation episode: `86009523`, type `EPISODE_TYPE_VALIDATION`.
- Both validation agents were `rurumi` using submission `54704652`; this was
  an exact self-play validation, so one side's `-1` is not a public matchup
  loss.
- Replay final statuses: `DONE,DONE`; `102` steps; observed statuses contained
  no `ERROR` or `TIMEOUT`; agent `info` objects were empty; minimum remaining
  overage time was `597.860346` seconds.
- The initial displayed `600.0` is the one-game validation initialization, not
  a mature public score. No replacement action is justified from it.

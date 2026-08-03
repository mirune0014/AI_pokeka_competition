# 2026-07-15 10:40 JST - Snotted Up escape v1 submission decision

## Decision

Use the second 2026-07-15 UTC submission slot for the accepted deterministic
Historical-Silver Snotted Up escape v1 package.

This is an early replacement under the clearly-weak-score exception, not a
routine three-hour-cadence replacement. The live anchor is healthy and has
recent wins, but the independently refreshed API and CLI score is 652.7. A
valid candidate now exists and weakly dominates the frozen anchor on the
tested panel while repairing a concrete public control matchup.

## Exact artifact

- Archive:
  `autonomous_gold_20260715/packages/historical_silver_snotted_escape_v1_20260715/submission_archaludon_snotted_escape_v1_clean_20260715.tar.gz`
- Archive SHA256:
  `05088556FAB149E9DF11B15A7EBC858A6C3D5EFC6E372E69401A5AD6A6DA3895`
- `main.py` SHA256:
  `48F58171C95DD9EC570DCD9D2843920215110FCD326832950BC1A6CD55032391`
- `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

The archive is cache-free, has no unsafe path, and extracts to those exact
source and deck hashes. Its bundled historical runtime imports in isolated
mode, exposes 1556 attacks, reads 60 deck rows, and completed four actual
Cubchoo games across both seats with zero action errors or max-step hits. The
new escape action was selected in both seats.

The earlier cache-containing archive in the same package directory is an
explicitly rejected audit artifact and is not the upload target.

## Local evidence

- Target Cubchoo/Articuno: 13/80 to 49/80, delta +36.
- Seat 0: 6/40 to 25/40, delta +19.
- Seat 1: 7/40 to 24/40, delta +17.
- Changed pairs: 36 loss-to-win, zero win-to-loss.
- Target paired normal 95% interval:
  `[0.3402940639, 0.5597059361]`.
- Adjacent panel: 520/640 to 520/640, delta zero.
- Adjacent seats: 258/320 and 262/320, both unchanged.
- Every one of 640 adjacent outcomes and all eight opponent totals are
  unchanged.
- Errors, max-step hits, unstarted games, duplicate controls, schedule
  mismatches, reference mismatches, and frozen-source hash mismatches: zero.

The root raw-row recomputation and independent Sol-xhigh evaluation agree.
The final Sol-Ultra rule judgment is ACCEPT for this exact source only.

## Live and slot check

- Current submission: 54704652, COMPLETE, API/CLI score 652.7.
- Episode-visible record: 13-8 over 21 public games.
- Most recent three: win Hop/Trevenant, win Mega Lucario, loss to the same Mega
  Lucario list; all runtimes healthy.
- 2026-07-15 UTC usage before this action: 1/5.
- Normal three-hour cadence has not elapsed, but the score is below 700 and
  the frozen candidate is valid. The early-replacement policy therefore
  applies.

## Hypothesis and observation plan

The new rule should retain exact anchor behavior in ordinary matchups while
converting Snotted Up attack-lock turns into resource-safe retreat, preserved
setup, and immediate attack continuity. Live validation must first confirm
archive execution. Public follow-up will inspect exact episode-ID additions,
runtime status, Cubchoo/Froslass exposure, retreat/attack continuity, board
backup readiness, prizes, and terminal route. A later slot requires another
isolated rule and full frozen evaluation; score movement alone is insufficient.

## External result

- Upload was initiated at 2026-07-15 01:43:08 UTC
  (10:43:08 JST).
- The archive transfer reached 100%. The Windows Kaggle CLI then returned
  exit 1 only while printing the server response because CP932 could not
  encode the character `é`. No retry was issued, preventing a duplicate
  submission.
- A UTF-8 read-only CLI query and an independent Kaggle API query both confirm
  the new row.
- Submission ID: `54707683`.
- File:
  `submission_archaludon_snotted_escape_v1_clean_20260715.tar.gz`.
- Description:
  `Historical-Silver Snotted Up escape v1; target +36/80; adjacent 520/640 unchanged`.
- Initial status: `SubmissionStatus.PENDING`.
- Public/private score: not yet assigned.
- 2026-07-15 UTC usage after upload: 2/5.

### Validation

- Status changed to `SubmissionStatus.COMPLETE`.
- Validation episode: `86021596`, `EPISODE_TYPE_VALIDATION`.
- Both teams are `rurumi` using submission `54707683`; the 1/-1 result is
  validation self-play, not a public strength result.
- Replay status: `DONE,DONE`.
- Replay steps: 132.
- ERROR/TIMEOUT rows and nonempty agent-info objects: zero.
- Minimum observed remaining overage time: 598.492401 seconds.
- Both extracted 60-card lists match the frozen candidate deck in exact order;
  ordered mismatches: zero for each seat.
- The displayed 600.0 is validation initialization and is not treated as a
  mature public score.

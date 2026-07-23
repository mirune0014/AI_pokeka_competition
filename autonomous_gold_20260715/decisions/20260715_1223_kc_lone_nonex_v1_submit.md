# 2026-07-15 12:23 JST - guarded lone non-ex evolution v1

## Decision

Use the third 2026-07-15 UTC submission slot for the accepted deterministic
Historical-Silver guarded lone non-ex evolution v1 package.

This is an early replacement under the clearly-weak-score exception. The
outgoing Snotted Up escape submission, `54707683`, was `COMPLETE`; its final
pre-upload CLI score was `676.5`. Its refreshed API score shortly before that
was `687.6`, while the last episode-visible update was `673.9610498275738`.
All are below `700`. A fully evaluated candidate exists, so score recovery is
not being replaced without a valid alternative.

## Exact artifact

- Archive:
  `autonomous_gold_20260715/packages/historical_silver_kc_lone_nonex_v1_20260715/submission_archaludon_kc_lone_nonex_v1_clean_20260715.tar.gz`
- Archive SHA256:
  `B938B393E3ABDD27136F4C48AB01DF587CCB201F3432F6BEBB10D908E8C73B4E`
- `main.py` SHA256:
  `44B846604C8A627BF9A1162BF1ADED3923976FAB1D200A333093347057790138`
- `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- `requirements.txt` SHA256:
  `9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47`

The clean archive contains the twelve expected files, no unsafe/cache entry,
and extracts byte-for-byte to the evaluated candidate. Isolated import and
four package-runtime games across both seats all passed with zero action
errors or max-step hits. The guarded action fired once in each seat.

## Isolated rule hypothesis

In the Kangaskhan/Crustle non-ex prize exchange, an Active Duraludon (`169`)
with exactly three Energy can remain unevolved even when Archaludon (`840`) is
legal. This can strand the only powered attacker and lose the exchange.

The new branch prefers the legal `840` evolution only when all of the
following hold:

- the target is the Active `169` with exactly three Energy;
- an opposing `344`, `345`, or `756` marker is visible;
- no own Cinderace (`666`) is in play;
- no benched `169`, `840`, or `190` already has at least three Energy; and
- the move does not replace a legal Raging Hammer knockout that Coated Attack
  cannot also take.

Existing endgame and Ogerpon rules remain ahead of this branch. The deck and
all other policy rules are unchanged.

## Frozen local evidence

- Kangaskhan/Crustle target: `30/80` to `57/80`, delta `+27`.
- Target seats: `+12` and `+15` wins.
- Target discordance: 27 loss-to-win, zero win-to-loss.
- Paired normal 95% interval for the target delta:
  `[0.23322688308393005, 0.44177311691607]`.
- Great Tusk guard panel: `64/80` to `65/80`; one loss-to-win, no regression.
- Cubchoo exact control: `49/80`, every paired outcome unchanged.
- Mega Lucario exact control: `74/80`, every paired outcome unchanged.
- Eight-opponent adjacent panel: `520/640`, every paired outcome byte-identical
  to the frozen parent.
- Raw comparison rows: `2880`; unique paired keys: `960`.
- Duplicate controls, schedule mismatches, action errors, max-step hits,
  unstarted games, invalid results, and frozen-reference mismatches: zero.
- First divergences: 42; all 42 were the exact legal guarded evolution and
  none fired outside the predicate.

The root recomputation, independent Sol-xhigh numerical audit, and final
Sol-Ultra rule judgment all agree: `ACCEPT` this exact source and deck as the
new parent.

## Live evidence and slot check

- Outgoing submission: `54707683`, `COMPLETE`, final pre-upload CLI score
  `676.5`.
- Refreshed outgoing episode CSV SHA256:
  `2B9F49093E8242F0FACDFEFC1EE51FCF870047A32C388DE7990DA3CC1AC60049`.
- The exact current-minus-previous set contained 17 episode IDs; the prior set
  was wholly retained.
- The 17 new outcomes were
  `W,L,W,W,W,L,L,L,L,W,W,L,W,W,W,L,W`.
- 2026-07-15 UTC usage immediately before upload: `2/5`.
- The outgoing score was below `700`, so the documented early-replacement
  policy applies even though the normal three-hour cadence had not elapsed.

## External result

- Upload completed successfully at `2026-07-15 03:23:38.957000 UTC`
  (`2026-07-15 12:23:38.957000 JST`).
- Kaggle CLI upload exit: `0`.
- Submission ID: `54710399`.
- File:
  `submission_archaludon_kc_lone_nonex_v1_clean_20260715.tar.gz`.
- Description:
  `Historical-Silver guarded lone non-ex evolution v1; KC +27/80; adjacent 520/640 unchanged`.
- Initial status: `SubmissionStatus.PENDING`.
- Public/private score: not yet assigned.
- 2026-07-15 UTC usage after upload: `3/5`.

### Validation

- Status changed to `SubmissionStatus.COMPLETE`.
- Validation episode: `86034564`, `EPISODE_TYPE_VALIDATION`, `COMPLETED`.
- Both agents are `rurumi` using submission `54710399`; the `1/-1` result is
  self-play validation, not a public strength result.
- Final runtime statuses: `DONE,DONE`.
- Replay steps / agent rows: `102 / 204`.
- ERROR/TIMEOUT rows and nonempty agent-info objects: `0 / 0`.
- Minimum remaining overage time: `598.6434770000001` seconds.
- Both extracted 60-card ordered lists match the candidate deck; ordered
  mismatches: `0 / 0`.
- Validation result: `PASS`.

The first exact public episode-ID set will be added after Kaggle makes it
available. A subsequent slot requires another isolated rule with a frozen
evaluation or a validated deployment correction; score movement by itself is
insufficient.

### First public observation

- Exact current-minus-validation ID set: `{86035204}`; reverse difference is
  empty.
- Result: win from policy seat 1 against `Neelima` submission `54534332`.
- Extracted opponent deck: Mega Lucario (`673-678` line).
- Score update: `600` to `715.0182427394724`; API display: `715.0`.
- Runtime: `DONE,DONE`, 0 ERROR/TIMEOUT rows, 0 nonempty agent-info objects.
- The target 60-card ordered deck has zero mismatches against the candidate.
- The new guarded non-ex branch cannot match this opponent list, so the win is
  not credited to the changed rule.

One public game is not mature evidence. Continue monitoring from this exact
two-ID snapshot.

### Three-public checkpoint

- Exact public sequence: `86035204 W, 86035713 W, 86036244 W`.
- Score chain:
  `600 -> 715.0182427394724 -> 812.8300535834865 -> 888.4653803679087`.
- API display after the third public game: `888.4`.
- Opponent decks: Mega Lucario, Archaludon mirror, and Chandelure Psychic
  control.
- All three replays finished `DONE,DONE`; ERROR/TIMEOUT and nonempty
  agent-info counts are zero.
- All three deployed target decks contain 60 cards with zero ordered mismatch.
- None of the three opponent lists satisfies the guarded rule marker predicate,
  so these wins demonstrate baseline/deployment health rather than direct live
  conversion by the new branch.

Retain and monitor. Three wins do not yet establish mature Gold performance or
authorize another submission.

### Six-public checkpoint

- Exact cumulative outcome sequence: `W,W,W,L,W,W` (`5-1`).
- Latest episode score: `948.9985578019498`; API display: `948.9`.
- New exact IDs since the three-public checkpoint:
  `{86036755,86037316,86037825}`; reverse difference empty.
- New outcomes: loss to verified Alakazam, win against an unlabelled extracted
  list, win in an Archaludon mirror.
- Every new replay is `DONE,DONE`; error, timeout, and nonempty agent-info
  counts are zero; all deployed deck order checks match 60/60.
- None of the six opponent decks satisfies the submitted KC marker predicate.

Retain submission `54710399` at 948.9. Slot usage remains `3/5`. A separately
selected Lucario rescue-follow-through hypothesis may be implemented and
evaluated locally, but no replacement is authorized from this checkpoint.

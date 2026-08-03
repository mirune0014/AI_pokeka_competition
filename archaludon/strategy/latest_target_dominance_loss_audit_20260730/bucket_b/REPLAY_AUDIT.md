# Bucket B public-loss replay audit

## Scope and immutable inputs

This audit is limited to submission `55099164` and episodes `88920116`,
`88921088`, `88927940`, `88928002`, `88928398`, `88934896`, `88935472`,
`88947304`, `88966008`, and `88967105`.

- Episodes CSV SHA-256:
  `5F568156AE4F77F6D0F75ABA210B1202C92FD2E42512A46B5FA760453690A0DB`
- Submitted source SHA-256:
  `6504E0E3EA69D59EAB5F9A73E306D70695A0E76ECA8D347C97F1EB43AEE31B7A`
- Direct-parent source SHA-256:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
- Every assigned replay matched its row in `sha256_inventory.csv`.
- The rurumi seat was resolved from `info.TeamNames`, not inferred from reward
  or deck contents.

## Exact shadow observations

Observed fact: the submitted source reproduced every recorded rurumi response,
including the initial deck callback and the four legal empty responses. The
direct parent produced the same response at every callback. There was therefore
no candidate-parent first difference to inspect in this replay set.

Observed fact: `PUBLIC_ONE_TURN_TARGET_DOMINANCE_WITH_EPHEMERAL_CHIP_VETO_V1`
had no eligible proposal, emitted action, suppression, active-owner-before
state, or active-owner-after state in any assigned episode. Its causal verdict
is **irrelevant** for every loss below. The firing counts are exact raw audit
counts, not an estimated rate; root should verify them from the callback rows
listed under "Raw rows".

| Episode | Opponent deck bucket | New-rule firings | Rule verdict | Earliest publicly credible fix |
|---|---|---:|---|---|
| 88920116 | Dragapult | 0 | Irrelevant | None certified; opening missed Cinderace and the line remained Metal-starved |
| 88921088 | Mega Lucario | 0 | Irrelevant | None certified; zero-energy rebuilds followed the first attacker KO |
| 88927940 | Dragapult | 0 | Irrelevant | None certified; public Dragapult/Dusknoir board pressure closed a thin board |
| 88928002 | Marnie's Grimmsnarl | 0 | Irrelevant | None certified; wide damage engine and prize race |
| 88928398 | Mega Lucario | 0 | Irrelevant | None certified; the final 440-HP Mega Lucario was outside one-hit range |
| 88934896 | Archaludon mirror | 0 | Irrelevant | None certified; no opening Metal made turn-1 Turbo Flare impossible |
| 88935472 | Archaludon mirror | 0 | Irrelevant | None certified; no Metal on turn 2 delayed Turbo Flare by one own turn |
| 88947304 | Mega Lucario | 0 | Irrelevant | Step 52: preserve access to the nearer-ready bench attacker instead of evolving the stranded Active |
| 88966008 | Marnie's Grimmsnarl | 0 | Irrelevant | None certified; opponent's wide engine won the late two-prize race |
| 88967105 | Archaludon mirror | 0 | Irrelevant | None certified; close exchange ended against a fresh opposing Archaludon ex |

Deck buckets come from the extracted submitted deck lists in
`root_deck_extract/decks.csv`; they are descriptive classifier labels, not
claims about opponent policy.

## Observed decision states

- `88947304`, rurumi seat 0, is the sole high-confidence preventable policy
  fork. At step 52 the public own board was Active Duraludon
  `(130 HP, 0 Energy)`, with benched Duraludon at 1 Energy and another at
  0 Energy. The hand held two Archaludon ex, and exactly one Metal was publicly
  in the discard. The agent evolved the 0-Energy Active. At steps 54-55 it
  attached that Metal to the 1-Energy benched Duraludon and ended at step 56.
  The public opponent Active was Hariyama. The following public log records two
  Premium Power Pro plays and Wild Press (`attackId=978`) for 270 damage,
  leaving the evolved Active at 30 HP. At steps 70-71 rurumi drew and attached
  Metal to the bench but still could neither retreat nor attack; the stranded
  two-prize Active was then removed. This is an attacker-access and prize-value
  routing failure: evolving the nearer-ready bench line leaves a one-prize
  Active pivot instead of converting the blocking Active into a two-prize
  liability. This fork is a contributing policy cause; it does not by itself
  prove that the alternative wins the game.
- `88934896` step 8 and `88935472` step 12 publicly show Cinderace Active with
  no Metal in hand. The respective turns end at steps 14 and 17; Turbo Flare
  first occurs on the next own turns (steps 33 and 34). These are setup/draw
  failures, not selectable-action errors.
- `88920116` never formed the Cinderace acceleration line and repeatedly
  exposed a single underpowered Archaludon line to Dragapult. `88921088`
  attacked once with the first powered Archaludon ex at step 67, then ended
  later turns at steps 86 and 113 with replacement lines short of attack
  payment. Those are primarily setup/resource variance amplified by strong
  opposing boards.
- `88927940`, `88928002`, `88928398`, `88966008`, and `88967105` contain no
  comparably certified action fork. Their terminal public states are consistent
  with opponent board strength or an already-lost prize/board race. Treating a
  hidden opponent card, a later draw, or a tied search ordering as the missing
  action would exceed the public evidence.

## Qualitative failure hypothesis

The repeated qualitative failure state is loss of attack continuity after the
first powered Archaludon ex is removed. In this set it mostly originates from
opening/energy variance or opponent strength, not from the new target-dominance
rule. The reusable policy defect that survives the public-certification bar is
narrower: **evolving a stranded Active can block promotion of the closer
attack-ready bench line while also upgrading the eventual prize liability**.

## Narrow countermeasure and regression risks

Test an **attacker-access / sacrificial-pivot certificate** only: when the
Active basic cannot attack or retreat this turn, a benched evolution target is
strictly closer to a payable attack, and the public opposing board has payable
KO pressure, compare bench evolution against Active evolution before applying
the generic "evolve Active first" hierarchy.

Regression risks are over-sacrificing a one-prize Active when Active evolution
is needed to survive, exposing the prepared bench line to a public gust effect,
and withholding an evolution whose Assemble Alloy attachments immediately make
the Active payable. Those states must remain vetoes. No broader deck,
target-selection, or matchup-specific mechanism is supported by this replay
set.

## Raw rows for root verification

- Original evidence:
  `autonomous_gold_20260715/evidence/latest_target_dominance_submission_refresh_20260730/episode_<EPISODE_ID>_replay.json`
  for the ten episode IDs above, plus `sha256_inventory.csv`,
  `submission_55099164_20260730_episodes.csv`, and
  `root_deck_extract/decks.csv`.
- Exact all-callback candidate/parent/recorded shadow rows:
  `C:\Users\amuam\AppData\Local\Temp\ptd_bucket_b_all_callback_shadow_rows.jsonl`
  (SHA-256
  `B9F19C086E32094B3E90C949095B60BB415777743D83A53AE6AC44984509BB59`).
- Public-state/action rows used for the qualitative audit:
  `C:\Users\amuam\AppData\Local\Temp\ptd_bucket_b_public_state_rows.jsonl`
  (SHA-256
  `E2C5FFBEA38E83F83C056680B3996D9391694C90A2BDC79955FC797AEEF3D07C`).

The derived JSONL files are reproducible diagnostics, not authoritative
aggregates. Root retains responsibility for independently verifying every
count or submission-relevant inference against the original replay rows.

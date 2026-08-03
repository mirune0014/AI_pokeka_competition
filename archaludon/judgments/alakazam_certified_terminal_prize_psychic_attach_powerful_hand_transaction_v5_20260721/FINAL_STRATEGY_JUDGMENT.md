# Final strategy judgment: terminal Prize transaction v5

Recorded: 2026-07-21 JST  
Scope: v5 only; one exploratory live probe; not formal adoption

## Verdict

**PERMIT_ONE_EXPLORATORY_LIVE_PROBE** using only:

- source SHA-256
  `C7E6E7DBCBB6357F0B559CEB6D9CC64DAACBDC660AFBDB890F91C5D1F462DA43`;
- clean archive
  `autonomous_gold_20260715/packages/alakazam_certified_terminal_prize_psychic_attach_powerful_hand_transaction_v5_clean_20260721/submission_alakazam_certified_terminal_prize_psychic_attach_powerful_hand_transaction_v5_20260721.tar.gz`;
- archive SHA-256
  `D22D4A174550C2E1DC4D3CD719F2568318791EA97EDBC781FF5BD83381B1AFBF`
  and exact size `2,026,199` bytes.

The live parent remains
`23B89E347565F1782F44494E8ACD89FAB0FEED20C484B2DA14DE1195B908CBE9`;
formal rollback remains
`4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`.
This permission does not promote v5 over either artifact.

## Verified facts used

- Receipt SHA-256 is
  `DC3992E434078FC62626E65DE50F23468FE17DDA7E8B8877DB4F169A0B78DE66`.
  Deck and runtime remain byte-identical to the live parent at
  `7B413177...1141` and `9CA7A415...CD9A`.
- Source inspection confirms a deterministic, public-state-only transaction.
  It admits only the exact safe Archaludon public lane: exact card and attack
  fingerprints, no opponent Tools, only absent or exact Full Metal Lab, exact
  harmless Bench-skill witnesses, a safe discard allowlist, and an exactly
  empty public `lost` zone. The same lane checks run before attachment,
  before Powerful Hand, and before taking Prizes.
- The rejected v1 Gear Coating false positive is closed. Focused package tests
  pass `16/16`, including Klinklang/Gear Coating, Iron Defender/Acerola-like
  transient reducers, Frigid Fangs, Drum Beating, Sand Attack, Torment,
  unknown skills/attacks/discard/Tools/Stadium, nonempty lost zone, both seats,
  permutations, duplicates, and continuation mutations. Every blocker returns
  exact live-parent behavior and leaves or clears the new latch.
- Checked engine SHA-256
  `5CDB5F1D2486FDFCA552EE8C1B44D8059B9F009286BC64630FDF85BDBE96AFBF`
  passes both semantic seats. In each, the parent chooses Enriching-to-Bench;
  v5 chooses Basic Psychic-to-Active, then Powerful Hand for 400, then both
  Prize cards, reaching zero own Prizes and the correct terminal winner with
  duplicate-identical callbacks and a cleared latch.
- Fresh current-49 shadow SHA-256
  `7E8774D51B9E607BACE8874CCE28C93034FE09B89108BE51A063DE705EB44683`
  binds exact live parent to exact v5 over 3,410 callbacks: exactly one
  classified difference, `87139766/S124`, with zero invalid actions and zero
  duplicate mismatches. The latest 11 episodes add no activation or fault.
- Frozen current-42/formal/historical raw hashes are respectively
  `FAE25AE1...A8DD`, `37E55A3C...E6EC`, and `082B90D1...C052`.
  Current-42 has only S124; formal has the four inherited live/formal changes
  plus S124; the 136-row/186-seat-run/11,866-callback historical population has
  zero differences, invalid actions, or duplicate mismatches.
- The clean archive contains the expected 12 regular files plus `cg/`, no
  cache/bytecode, and its extracted `main.py` and deck exactly match the frozen
  hashes. Package Historical-Silver duplicate smoke wins in both seats: seat 0
  in 131 steps and seat 1 in 109, with identical per-seat traces, zero action
  errors, and no max-step hit.
- The authenticated final refresh reports submission `54861184` `COMPLETE`,
  49 completed episodes of which 48 are public, public record `27-21`, and
  score `748.326559609227` (`748.3` in the CLI). Submission-list and episode
  commands exited zero. Exactly four submissions are recorded on UTC
  `2026-07-20`, leaving one policy slot at the frozen refresh.

## Reasoning

The observed mechanism is the intended rule, not score correlation. At S124,
setup and board formation are complete; the only missing attacker resource is
one Basic Psychic. Spending it leaves 20 cards, the conservative Full Metal
Lab floor is 370 into 300 HP, and the checked engine proves uninterrupted
attach -> attack -> final two-Prize conversion in both seats. Because the game
ends, backup readiness, retained Enriching draw, future Energy, deck clock,
disruption, and the opponent's next turn have no residual value.

Regression risk is bounded by the strict public-lane certificate and exact
continuation fingerprints. Adjacent live and historical populations preserve
parent behavior; package smoke establishes practical executable strength and
both-seat safety; no action-error, duplicate, or max-step gate fails. The live
parent is mature and remains materially below 1000, so one evidence-gathering
replacement is proportionate under the five-slot policy.

Activation remains rare: only one start appears in the 3,410-callback live
shadow and none in the historical population. There is no compact-panel gain
or repeated mechanism bucket. Therefore this is **not** acceptance on a tiny
delta and not formal promotion; it is one live experiment justified by an
exact loss-to-win major break. Formal adoption still requires primary-anchor
movement, repeated-bucket evidence, both-seat and adjacent-population floors,
and the frozen compact/full evaluation.

## Hard live stops

The root must stop without writing if any one is false immediately before the
Kaggle call:

1. Recomputed source, archive, deck, runtime, archive size, and archive member
   hashes equal the frozen values above; the uploaded path is exactly the clean
   v5 archive.
2. Submission `54861184` is still `COMPLETE` without an execution error, and
   no newer replay exposes an invalid action, duplicate mismatch, unclassified
   v5 difference, or contradiction of the terminal certificate.
3. Authenticated quota still permits a write. If another submission consumed
   the fifth UTC slot, stop. If the UTC date rolled over, refresh the quota and
   mature-submission state before proceeding; this judgment still permits only
   one probe.
4. The Kaggle request names and describes v5 as an exploratory terminal-Prize
   probe. Do not cancel/replace another submission, change the deck/source,
   submit a different archive, or make any Notebook/Discussion/configuration
   write under this permission.
5. Make at most one submission call. An API failure or `ERROR` result does not
   authorize a retry or a second slot without a new root decision.

## Evidence required after the probe

Record the submission ID, UTC timestamp, exact local archive hash, API result,
execution status, score/game sequence, all new episode IDs, correct-seat
actions, action errors, max-step hits, and every v5-versus-parent first
difference. Confirm any gain begins with the certified Basic Psychic ->
Powerful Hand -> two-Prize mechanism. If the rule never activates, score
movement is not causal evidence. Before any formal adoption, run the frozen
compact comparison and then the full both-seat population with practical
absolute strength, Historical-Silver movement, repeated activation buckets,
adjacent-matchup floors, duplicate identity, and zero-fault gates.

Uncertainty is high about frequency and leaderboard effect, but low about the
tested transaction and package safety. That uncertainty is exactly why the
permission is one exploratory probe and nothing more.

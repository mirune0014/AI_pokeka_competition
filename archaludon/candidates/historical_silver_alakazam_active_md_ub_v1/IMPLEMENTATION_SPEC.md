# Immutable implementation specification: Alakazam Active-MD Ultra Ball v1

Frozen by the root at 2026-07-15 15:27 JST.  This authorizes one isolated,
pure deterministic rule implementation only.  It does not authorize a deck
change, full evaluation, package, or Kaggle submission.

## Parent and isolated destination

- Exact parent:
  `autonomous_gold_20260715/candidates/historical_silver_kc_lone_nonex_v1`
- Parent `main.py` SHA256:
  `44B846604C8A627BF9A1162BF1ADED3923976FAB1D200A333093347057790138`
- Parent `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Parent `requirements.txt` SHA256:
  `9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47`
- Isolated destination:
  `autonomous_gold_20260715/candidates/historical_silver_alakazam_active_md_ub_v1`

Keep destination `deck.csv`, `requirements.txt`, and every `cg/` file
byte-identical to the parent.  Preserve this specification.  Only destination
`main.py` may differ from the parent source.  Do not touch the parent or any
other candidate.

## Sole allowed behavior change

The only changed score is a legal MAIN `PLAY` option whose hand card is Ultra
Ball `1121`.  First obtain the parent's normal `score_play` result.  If that
score is negative and every predicate below is true, return exactly:

```text
(34000, "Alakazam: Active MD Ultra Ball")
```

Otherwise return the exact parent result.  Do not change discard, search,
evolution, Alloy attachment, attack, Boss, promotion, setup, or any other
score.  Add no persistent game state, replay-derived memory, learned ranker,
randomness, or hidden-card inference.

## Public-state predicate: all clauses mandatory

1. Context is MAIN, the current option is legal `PLAY 1121`, and the parent's
   unmodified Ultra Ball score is negative.
2. `detect_matchup(obs) == "alakazam"` and `obs.current.turn >= 3`.
3. Own Active is Duraludon `169`, `appearThisTurn == false`, and has `E` Metal
   Energy with `1 <= E <= 3`.
4. Own Bench is non-empty and contains Duraludon `169`.
5. Own hand contains no Archaludon ex `190`; `need_archaludon(obs)` is true;
   own deck count is positive; and fewer than four `190` copies are publicly
   visible across own hand, field, and discard.
6. Opposing Active is visible, worth exactly one prize, and has positive HP.
7. At least one attack option is legal now.  The maximum effective damage of
   all currently legal attacks is below the opposing Active's current HP,
   while Metal Defender's effective 220 damage reaches that HP.
8. Boss-target veto: if Boss `1182` is legally playable now and any currently
   legal attack can knock out any visible opposing Bench target after Boss,
   fail the override.  This veto applies regardless of that target's prize
   value.
9. Remove the exact played Ultra Ball instance from the ordered hand.  Using
   the unchanged Ultra Ball `score_discard` logic and exact parent
   `(score, -option_index)` tie break, project the actual top-two discard
   multiset `pair`.  Reconstruct current discard Metal count `M` from public
   state only.
10. Let `metal_needed = (E + min(2, M) < 3)`.  If true, `pair` must be exactly
    multiset `{Boss 1182, Metal 8}`.  If false, it must be exactly multiset
    `{Boss 1182, Cinderace 666}`.  The projection must fail closed on any
    uncertainty.  It must never consume a sole draw supporter, Night Stretcher
    `1097`, Duraludon `169`, Hero's Cape `1159`, `190`, or `840`.
11. With `M_after = M + count(Metal 8 in pair)`, require
    `E + min(2, M_after) >= 3`.
12. `final_prize_nonex_no_backup(obs)` is false.
13. Search ordering must be publicly safe: if `190` is offered after the
    projected cost, unchanged `score_to_hand` must select it above every
    possible Pokemon competitor.  In particular, a Duraludon emergency-backup
    score may not outrank `190`.  Do not inspect the hidden deck or prizes.
14. The Active Duraludon must remain evolution-legal after the search.  Using
    `M_after`, reproduce the exact current `score_evolve` values.  Active
    evolution must strictly outrank every legal established-Bench Duraludon
    evolution; any tie fails closed.  Newly played Bench Pokemon are not legal
    evolution targets.
15. The projected Active-evolution score must outrank every remaining legal
    hand-changing or turn-ending MAIN action under the unchanged policy.  Any
    higher intervening action is allowed only if a conservative public dry-run
    proves it non-terminal and proves that it preserves the searched `190`,
    Active evolution legality, Active Energy, and discard-Metal count.
    Otherwise fail closed.
16. Dry-run the unchanged ordered Assemble Alloy target scorer for at most two
    attachments using `M_after`.  The projected evolved Active must finish
    with at least three Metal.  The unchanged attack scorer must then select
    legal Metal Defender against the unchanged opposing Active for the
    same-turn knockout.

The MAIN observation cannot prove that a non-visible `190` is in the deck
rather than in face-down prizes.  Clause 5 only rejects a publicly certain
miss.  Never use a later replay search result or a cross-step flag to make the
MAIN decision.  A search miss during evaluation is a hard rejection, not a
reason to add memory or broaden the rule.

## Required pointwise behavior

Positive states:

- Live `86039927`, replay step 24: turn 4, established Active Duraludon with
  one Metal; projected pair Metal + Boss; score exactly 34000.
- Live `86044692`, replay step 40: turn 4, established Active Duraludon with
  three Metal; projected pair Cinderace + Boss; newly benched Duraludon is not
  evolution-legal; score exactly 34000.
- Frozen `alakazam_exact/p0/2026071601`, first matching step 93: projected pair
  Cinderace + Boss, Boss-target veto false, and the Ultra Ball PLAY is the
  first policy divergence.

Required negatives:

- `alakazam_exact/p0/2026071610`, step 111: Boss-target KO veto.
- `alakazam_rmy/p1/2026071595`, step 78: Boss-target KO veto.
- `alakazam_exact/p1/2026071600`, step 71: historical win and Boss-target KO
  veto.
- `exact/p0/2026071595`, `exact/p0/2026071608`,
  `exact/p1/2026071608`, and `rmy/p1/2026071608`: `turn < 3`.
- Live `86036755`, step 72: Active has zero Energy.
- Every Ultra Ball state in live `86045168` and `86045681`: Active Cinderace
  and/or empty Bench.
- Every archived empty-Bench Alakazam Ultra Ball probe.
- Frozen `alakazam_rmy/p1/2026071584`, later step 110: top-two pair is not the
  allowed unneeded-Metal pair.
- New Alakazam win `86054070`: no legal MAIN Ultra Ball state; therefore no
  positive trigger can be introduced.
- Synthetic public snapshots with four visible `190`, final-prize guard,
  Active/Bench evolution tie, unsafe pair, already available Active KO,
  Boss-target KO, sole-supporter consumption, or search-order ambiguity.

Every off-predicate state must preserve the exact parent action score and
reason.  Failure of a pointwise test rejects this implementation; do not repair
it by forcing downstream actions or tracking state.

## Worker boundary and checks

- Copy the exact parent runtime into the destination around this frozen spec.
- Use small pure helpers with fail-closed exception handling; keep the diff
  reviewable and confined to `main.py`.
- Compile the destination source.
- Verify parent/destination deck, requirements, and all `cg/` hashes are
  identical.
- Run snapshot/unit checks for the two live positives and all immediately
  available negatives.  Report exact clause diagnostics, scores, actions,
  commands, exits, hashes, and a concise diff.
- Do not run or interpret the full paired evaluation, package, or submit.

Numerical evaluation, root verification, and all Kaggle writes remain outside
the worker's authority.

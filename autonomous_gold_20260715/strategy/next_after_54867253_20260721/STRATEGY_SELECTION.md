# Strategy selection after Kaggle 54867253

- Frozen by root: 2026-07-21 22:01 JST
- Selected direct parent: `alakazam_public_h0_h1_turn_objective_guard_v1`
- Parent source SHA-256: `23B89E347565F1782F44494E8ACD89FAB0FEED20C484B2DA14DE1195B908CBE9`
- Formal rollback SHA-256: `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`
- Rejected as parent: live source SHA-256 `7838FBFF3CBA3AE5D9142E45B1334B192A5E758CFFA5598AF2A626E5C7D636E3`

## Selected hypothesis

Implement exactly one deterministic public-state rule:
`alakazam_starmie_shaymin_bench_protection_guard_v1`.

The rule reserves and deploys Shaymin against the public Mega Starmie spread
attack only when an existing non-rule-box Bench Pokemon is already within the
exact 50-damage Bench-KO range. It does not change the deck and does not stack
the unexercised finalized-Super-Psy-Bolt retreat overlay.

## Immutable contract

### Dawn `TO_HAND`

Prefer a legal offered Shaymin over an additional Abra only when every condition
is true:

1. The opponent public field contains Staryu `1030` or Mega Starmie ex `1031`.
2. No Shaymin `343` is already in own hand or field.
3. Own hand plus field already contains at least two Abra-line bodies
   (`741`, `742`, or `743`).
4. An own Benched non-rule-box Pokemon has remaining HP at most 50.

Stable tie-breaking chooses the lowest legal Shaymin option index. Do not alter
any other Dawn selection.

### Ordinary `MAIN`

When the opponent Active is Mega Starmie ex `1031`, it has Basic Water Energy
`3`, an own Benched non-rule-box Pokemon has remaining HP at most 50, own
Shaymin is absent, and Shaymin is a legal PLAY:

1. Certified immediate win/KO and already certified enabling actions keep
   highest precedence.
2. Otherwise PLAY Shaymin before any optional Basic that could consume its
   Bench slot and before END.
3. Reserve the final open Bench slot for Shaymin.
4. If Shaymin cannot legally be placed, suppress only an optional PLAY of a
   fragile non-rule-box Basic with HP at most 50 that would consume the reserved
   slot. Never suppress attachments, evolutions, attacks, retreat, or established
   attacker/backup continuity.

Do not use opponent identity, replay/episode ID, hidden information, learned
action labels, or other Water attackers. Battle Cage is not equivalent
protection because the observed threat deals attack damage rather than placing
damage counters.

## Mandatory positives

- `87206063/S17`: Dawn chooses offered Shaymin option 0 over Abra option 2.
  The following ordinary MAIN deploys Shaymin before another Abra.
- `87203877/S53`: held legal Shaymin is deployed before Genesect or Abra can
  consume its slot while a 20-HP Bench Dunsparce is threatened.
- Both visible Staryu and visible Mega Starmie satisfy the Dawn predicate.
- Remaining HP exactly 50 satisfies the threshold.

## Mandatory negatives

- Bench remaining HP above 50.
- Rule-box Bench target.
- No threatened Bench.
- Fewer than two total Abra-line bodies at Dawn.
- Shaymin already in hand or field.
- Mega Starmie without Basic Water Energy during MAIN.
- Shaymin illegal or not offered.
- Unrelated Water attackers.
- Certified immediate KO or win.
- Mirror and Lucario callbacks that do not satisfy the predicate.

## Minimum practical probe gates

- Compile/import, loader-last single callable, legal 60 cards with one ACE SPEC,
  source/runtime parity, and cache-free candidate tree.
- Both target replays activate and complete the intended Shaymin sequence.
- Full current-35 plus historical shadow: every first difference classified,
  zero invalid actions, zero duplicate mismatches, and all nonactivating rows
  action-identical.
- Deterministic both-seat checked-engine smoke against historical-Silver
  Archaludon, Starmie, Alakazam mirror, and Mega Lucario with zero action errors
  and zero max-step hits.
- No historical-Silver seat regression and Starmie is not net worse in the
  fixed paired smoke.
- Package-local both-seat smoke and archive hygiene.

If every gate passes, one exploratory live submission is permitted. This is a
probe, not formal adoption. Root alone packages and writes to Kaggle.

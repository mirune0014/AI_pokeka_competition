# Strategy selection: Active-ready plus draw-survival merge v1

Selected: 2026-07-20 JST  
Owner: root  
Status: one isolated implementation authorized; evaluation and Kaggle write are not authorized

Unchanged `alakazam_next_turn_draw_survival_certificate_v3` is **DO NOT SUBMIT**.

## Frozen lineage

- Candidate:
  `autonomous_gold_20260715/candidates/alakazam_evolve_active_ready_draw_survival_v3_merge_v1`.
- Innermost executable parent:
  `alakazam_evolve_active_ready_source_transition_v2`, source SHA-256
  `305A6C597609E82E8611DBF83DA8C8845E70BD5B89781988E74C720BD6B53267`.
- Wrapper donors, in order:
  - draw-survival v1 source `225CDAC94FD1C87C3956993120D519F8B191279CA8737F758B717E8DDA9E3F07`;
  - draw-free v2 source `D0E0DD3945547446084301B6CBC90648E46550AD7DA7949E9F4AFF59D72E5981`;
  - Boss-terminal v3 source `AA5A4BC31A6CCA09FC7671AE0E61F0A3042C5EA76A3F08C39B4ACF6832512739`.
- Runtime/deck SHA-256 remain
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

## Sole mechanism and precedence

Use source-transition v2 as a private inner parent, then append the already
tested draw-survival v1, draw-free terminal-evolution v2, and Boss-Lucario v3
wrapper sections. Do not change scoring, deck, any certificate, or recreate
Active evolution as a fifth wrapper. Rebind all old strict-parent witness calls
to the source-transition parent.

- At most one transaction latch owns a callback.
- Existing Active latch at entry owns; outer layers delegate.
- Start order is Active source-transition, draw v1, draw-free v2, Boss v3.
- Active start is barred while any outer latch is active.
- Every outer start is barred while the Active latch exists or was cleared in
  the same callback. A clear/fail-closed callback is quarantined once.
- Snapshot/restore covers all base state, `_certified_turn_plan_latch`, source
  decision cache, all outer latches, and all wrapper caches.
- Filtered reruns commit the complete rerun state or restore the complete
  initial-after-parent state; partial adoption is forbidden.
- Latch/cache names remain distinct. Repeated callbacks return cached actions
  without stage advancement. Any collision, ambiguity or unexpected mutation
  delegates once to the immediate parent.

## Mandatory implementation gates

1. New live anchor `86924873/57-60`: `[3]` Active energized/tool-bearing Abra
   evolution, exact YES, post-draw delegation, later Bench evolution. `[4]`
   Bench-first is forbidden.
2. Preserve all source-transition positives, mutation and repetition controls,
   and current42 behavior.
3. Preserve draw suppressions `86892228/155` and `86893328/158`.
4. Preserve both draw-free recovery routes, including Marnie.
5. Preserve the full `86909242/133` Boss→Mega Lucario→Powerful Hand→final
   Prizes route.
6. Collision fixtures cover active/just-cleared pairings, simultaneous
   eligibility, filtered-rerun failure, state restoration and repetition.
7. Compile/import, legal deterministic 60 cards with one ACE, valid actions,
   and zero caches.

The worker owns only the new candidate directory and
`autonomous_gold_20260715/implementation/alakazam_evolve_active_ready_draw_survival_v3_merge_v1`.
It must not edit any donor, replay, evaluation, package, strategy, or live file.

## Initial rapid evaluation gate

Use the fixed schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
restricted to seeds `2026071586`, `2026071600`, `2026101801`, and
`2026101804`: 72 games across nine opponents and both seats, candidate primary
plus duplicate, reusing frozen source-transition baseline.

Source-transition compact anchor is `38/72`, P0 `20/36`, P1 `18/36`.
Require candidate at least `39/72`, P0 at least `21/36`, P1 at least `18/36`,
at least one paired gain and zero regressions, Marnie recovery as expected,
Historical recovery retained, no opponent below its source-transition floor,
duplicate summary/full-trace identity `72/72`, no faults, and every first
difference classified as an existing authorized wrapper mechanism.

Passing this gate permits a final strategy judgment for one rapid live probe;
it does not itself authorize packaging or submission.


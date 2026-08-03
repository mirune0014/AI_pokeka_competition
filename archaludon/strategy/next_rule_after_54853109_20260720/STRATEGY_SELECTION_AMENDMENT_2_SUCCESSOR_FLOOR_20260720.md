# Second strategy clarification: successor-continuity floor

## Ruling

**Choose option B: retain the nonterminal prize-lead one-Prize Active KO lock
with exactly one additional public board-theory guard.** Do not classify every
literal-certificate start as safe, and do not reject the hypothesis yet.

The one new guard is a **successor-continuity floor**. Before the candidate may
replace an eligible resource detour with Powerful Hand, the current Bench must
already prove either:

1. one complete, serial-distinct Benched Kadabra or Alakazam whose currently
   attached public Energy pays at least one of its printed attacks if promoted
   unchanged; or
2. two complete, serial-distinct Benched Alakazam lines, at least one of which
   was not formed this turn.

No Basic Abra, Dunsparce/Dudunsparce, Energy in hand/deck/discard, future draw,
future evolution, future attachment, or Active attacker counts toward this
floor. Unknown stacks, Energy payment, printed attacks, ownership, serials, or
status fail closed. This is one coherent guard with two public proofs of the
same proposition: either a successor can attack already, or the Stage-2 board
has enough completed redundancy to survive losing one line while needing only
Energy rather than both evolution and Energy.

This report supersedes the “first differences exactly the three anchors” gates
in both earlier reports and strengthens their one-formed-backup condition. It
does not change the parent, nonterminal `P >= 2`, one-Prize target, two-Prize
lead, unique exact lethal Powerful Hand, detour whitelist, no-higher-Prize
route, EVOLVE/selection retention, terminal exclusion, or numerical gates.
The destination remains
`autonomous_gold_20260715/candidates/alakazam_certified_prize_lead_one_prize_active_ko_lock_v1`.

## Verified facts used

Root directly inspected the literal implementation's frozen current-20 shadow
and the raw replay states. The relevant raw files are:

- `live/54853109/refresh_20260720_20public/episode_87076890_replay.json`,
  SHA-256
  `607FFBB919F717FF9EB664EF08F2CE190E3A8C93150D1180F5D997F67440C679`;
- `live/54853109/refresh_20260720_20public/episode_87078566_replay.json`,
  SHA-256
  `FE1E487DA8C57B2C20C960BAC0123ADE5F5CE155AA01E89F25EDA7A4141179FA`;
- `live/54853109/refresh_20260720_20public/episode_87079669_replay.json`,
  SHA-256
  `8DA69F2A56C3B701B6FB98F5B2D490D1DF6B5EE5C49265DAC7CE203AE0F39506`;
- `live/54853109/refresh_20260720_20public/episode_87087306_replay.json`,
  SHA-256
  `5EFED6F0738B616F5D47A5CCB8576B00CF831B6CCD735CB6E58D2F5C0ECD00DA`.

The literal amended certificate exposed three earlier natural starts not
listed in the first two reports. All named base, nonterminal, eligible-detour,
and no-higher-Boss predicates passed:

- `87076890/S114`, seat 0: Prizes `4/6`, hand `4`, deck `14`; old paid Active
  Alakazam versus 50-HP Abra; parent Hilda, unique lethal Powerful Hand. Bench:
  unenergized Kadabra `s9`, unenergized Alakazam `s11`, unenergized Kadabra
  `s10`, and two Dudunsparce.
- `87078566/S75`, seat 0, a recorded win: Prizes `4/6`, hand `14`, deck `18`;
  old paid Active Alakazam versus 70-HP Dunsparce; parent Poke Pad, unique
  lethal Powerful Hand. S73 EVOLVE and S74 Psychic Draw have already resolved.
  Bench includes newly formed Alakazam `s11` and old Alakazam `s12` already
  paid by Telepath Psychic Energy.
- `87087306/S56`, seat 1: Prizes `4/6`, hand `18`, deck `21`; old paid Active
  Alakazam versus 70-HP Dunsparce; parent Poke Pad, unique lethal Powerful
  Hand. Bench has only one formed Alakazam `s72`, unenergized, plus two Abra and
  two Dunsparce, one carrying Enriching Energy.

These facts prove that the earlier exact-three shadow assertion was false.
They do not prove the three actions equivalent: their successor states differ
materially.

## Qualitative judgment of the three new states

### S114: unsafe start; mandatory negative

S114 fails the successor-continuity floor. The only Benched Alakazam and both
Kadabra are unenergized, so an immediate KO would leave no attacking successor.
The parent Hilda is not empty processing: its S115-S116 selections obtain
Kadabra `s8` and Telepath Psychic Energy `s61`; the parent attaches `s61` to
Benched Alakazam `s11` at S117 and attacks at S118. Hilda therefore crosses
the readiness floor on the observed path. Skipping it would sacrifice board
formation and attack continuity for one-Prize tempo while the damaged Active
is only at 80 HP. Exact parent identity is required at S114.

This does not discard the later `87076890/S173` target. At S173, the Bench has
Kadabra `s9` with Basic Psychic Energy already attached, so the ready-successor
branch passes; Dawn would draw the last deck card before the same KO. S173
remains the reachable first intended start in this replay.

### S75: intended natural start; critical win retention

S75 passes both forms of the floor: old Benched Alakazam `s12` is paid, and
the Bench contains complete Alakazam `s11` plus `s12`. The useful S73 evolution
and S74 Psychic Draw remain parent-identical. The subsequent parent path spends
two Poke Pads, Hilda, and an Energy to ready the second backup before attacking
at S82. Under the selected rule, one already ready successor is sufficient
while leading `4/6`; the extra sequence is redundancy expansion rather than
the only route to continuity. S75 is therefore an intended first difference,
not a negative.

However, the recorded parent won. That result is not counterfactual evidence
that attacking at S75 also wins. Treat S75 as the highest-risk positive and a
retention boundary, not as evidence of improvement. A mechanism-first loss in
a checked continuation or repeated ready-successor local bucket rejects the
candidate even if loss-replay anchors improve.

### S56: unsafe start; mandatory negative

S56 fails the floor. Benched Alakazam `s72` has no Energy and is the only
formed Psychic evolution; the remaining prospective attackers are Basics.
The parent's Poke Pad selects Kadabra `s67`, followed by evolution/Psychic
Draw, Dudunsparce formation, Basic Energy attachment to Alakazam `s72`, Dawn,
Rare Candy into a second Alakazam, another Poke Pad, and further evolution
before the S73 attack. This is substantial board and successor construction,
not dispensable resource churn. Exact parent identity is required at S56.

The later `87087306/S82` target remains intended. By then Benched Alakazam
`s72` is paid with Basic Psychic Energy and a second Alakazam `s71` is complete,
so both floor proofs pass. The S82 Poke Pad can be cut without abandoning the
only successor route.

## Complete amended behavioral contract

The implementation must compute the guarded parent's finalized action first,
then apply every prior base/nonterminal predicate and this successor floor on
the same observation. The new floor is a pure, stateless certificate. It may
read only current public/own state and immutable card metadata; it creates no
sequence flag or latch and cannot infer that an earlier setup action happened.

For the ready-successor proof, resolve complete ownership and evolution stack,
positive HP, status, attached Energy cards/units, and printed attack costs. A
future manual attachment, Enriching move, Psychic Draw, retreat, evolution, or
search does not count. For the redundant-Stage-2 proof, count physical Benched
Alakazam serials with complete stacks, not cards in hand/deck/discard or an
Alakazam already Active; require at least one old line so two same-turn malformed
or transient entries cannot pass.

If neither proof passes, return exact parent identity before considering the
resource-detour override. Do not special-case Hilda or Poke Pad, an episode,
step, player, deck count, Prize count beyond the existing lead invariant, or
recorded outcome. S114 and S56 are consequences of the generic board guard,
not named runtime exceptions.

The four presently known intended positives are:

- `87076890/S173`: ready Benched Kadabra branch; Dawn -> Powerful Hand;
- `87078566/S75`: ready successor and double-Alakazam branches; Poke Pad ->
  Powerful Hand;
- `87079669/S83`: double-Alakazam branch after retained S81 EVOLVE and S82
  Psychic Draw; Poke Pad -> Powerful Hand;
- `87087306/S82`: ready successor and double-Alakazam branches; Poke Pad ->
  Powerful Hand.

Mandatory focused negatives now include `87076890/S114` and `87087306/S56`,
plus `87079669/S81-S82`, every EVOLVE/owned-selection callback, terminal S147,
and all earlier negatives. Test each failed floor atomically: one unenergized
Alakazam; Alakazam plus any number of unenergized Kadabra; Energy-bearing
Dunsparce/Dudunsparce only; two Alakazam with malformed/duplicate serial or
stack; future Energy only; status/metadata ambiguity. Also mutate the four
positives by removing the paid backup Energy or one Alakazam so the expected
branch transitions or fails exactly.

## Corrected shadow and mechanism gates

Delete the assertion that first differences must equal a fixed three-anchor
set. Before numerical evaluation, rerun the frozen current-20 and historical
shadow and produce a callback-complete census. Require:

1. exact parent identity at S114, S56, S81-S82, and every other mandatory
   negative;
2. the four known positives above as reachable first differences unless an
   earlier newly discovered state in the same replay validly satisfies the
   strengthened certificate;
3. every difference selects the unique certified Powerful Hand, satisfies all
   old predicates plus exactly one or both successor-floor proofs, and has no
   inherited-state mutation;
4. zero illegal actions and a root-reviewed classification for every newly
   exposed natural start.

Additional public-information starts are not failures merely because they were
not named here. They are intended only if the complete semantic certificate
passes and qualitative inspection confirms the observed board matches the
claimed ready or redundant successor mechanism. If another unsafe setup-cutoff
passes this strengthened floor, **reject the hypothesis**; do not add a third
state-separating guard to this candidate.

Telemetry must record `ready_successor`, `double_alakazam`, or both, along with
the parent action class and attack certificate, outside gameplay state. Local
evaluation must report activations and paired outcomes separately for the two
floor proofs, both seats, known/fresh blocks, Historical Silver, mirrors, and
adjacent nonmirror opponents. Require zero action errors/max-step hits and
inspect every gain and regression trace. In particular, a tiny aggregate delta
cannot offset a ready-successor regression resembling S75.

All compact-72 and full-144 absolute-strength, paired-delta, seat, block,
opponent-floor, Silver, duplicate, and mechanism-linked adoption thresholds
from the original report remain unchanged. Passing retention authorizes only
the next independent judgment; it is not acceptance or Kaggle permission.

## Residual risk and exact evidence needed next

The double-Alakazam proof is deliberately weaker than a paid successor: S83
has board redundancy but no proven backup Energy, so attack continuity under
gust, Hammer, or a KO remains uncertain. The ready-successor proof can also be
weak when the only paid backup is Kadabra with a low-damage attack, as at S173.
S75 shows the opposite risk: stopping after one ready successor may surrender
useful second-backup development in a game the parent already won. These are
falsifiable evaluation risks, not reasons to widen the rule further.

Next evidence must be:

1. one isolated worker patch implementing only this successor floor, with
   source/runtime/deck hashes and a diff against the exact guarded parent;
2. focused exact-engine proof of four positives, S114/S56/S81-S82 retention,
   floor mutations, cache/latch non-mutation, legality, KO/Prize continuation,
   and terminal exclusion;
3. root-verified callback-complete current-20 and historical shadow census,
   including every newly natural start and floor-proof telemetry;
4. the unchanged compact-72 raw evaluation and independent Sol-Ultra audit of
   absolute wins, paired changes, both seats/blocks, opponent floors, action
   errors, max steps, and mechanism-linked outcomes;
5. if and only if those pass, full-144 confirmation and a fresh Sol-Ultra
   accept/reject judgment. Any additional unsafe certificate-satisfying start
   or repeated ready/redundant-successor regression rejects this hypothesis.


# Selected next rule: symmetric Full Metal Lab combat / Prize boundary v1

## Source and isolation

Implement one append-only deterministic suffix directly from:

- parent:
  `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- parent SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Do not stack PBNS, its attack-legality repair, or any rejected Explorer overlay.
PBNS final audit SHA
`52AE2B0937F573CD54D4D2EC9D02070FFB1C9CFF8E0DEEEB060129E850E9B183`
is a negative-control input only.

## Single hypothesis

Replace the reachable inherited `Full Metal Lab = 20000 when our Active is
Metal` behavior with an exact public-state comparison of:

- `KEEP_CURRENT_STADIUM`; and
- `PLAY_FULL_METAL_LAB`.

Apply Full Metal Lab's 30 attack-damage reduction symmetrically to both players'
Metal Pokémon after Weakness and Resistance.  It does not reduce damage-counter
placement.  Own the action only when one world strictly improves the hard
combat/Prize hierarchy.

This is selected before Lillie, Jumbo Ice Cream, and broader Boss logic because
all decisive FML inputs are public and exact, natural use is frequent (172
target-seat turns), and the inherited fixed score is directly reachable.

## Activation and precedence

1. Call the exact direct parent once per callback.
2. Preserve result/deck/setup/mandatory contexts and every inherited live owner.
3. Resume an already-owned FML watch deterministically.
4. Begin only at a transaction-free, single-choice clear `MAIN` callback.
5. Require exact FML ID/name/type/text hash, one unique semantic PLAY role,
   `stadiumPlayed == False`, complete serial identity, and exact current-stadium
   projection.
6. Require an actual legal ATTACK option.  Energy readiness alone is not attack
   permission.  Reject the first player's game turn one and re-certify the exact
   ATTACK option immediately before emission.

Compare the same attacker, opposing Active, and exact attack ID in KEEP and FML
worlds using the shared public combat resolver and exact public return graph.
Unknown, unsupported, incomparable, physically ambiguous, or multiple
nondominated attack states return the parent; never convert UNKNOWN to zero.

Hard comparison order:

1. exact win now;
2. avoidance of exact next-turn terminal loss;
3. certain current Prize and KO;
4. certain return Prize loss and current-attacker survival;
5. exact next-attacker readiness and next-Prize timing;
6. exact benefit/harm from replacing the current Stadium;
7. post-action/post-reply public resource ledger.

No lower layer may worsen a higher layer.

## Allowed ownership modes

### INSERT_FML_BEFORE_PARENT_ATTACK

The direct parent already selected the exact certified attack.  FML strictly
improves a layer above resource conservation and worsens no earlier layer.
Emit FML, verify its resolution, re-certify the same attack, then emit it.
Do not pre-empt productive setup and later claim that the attack was urgent.

### VETO_HARMFUL_FML

The parent selected FML, but KEEP has an exact terminal attack, or FML destroys
a certain current Prize/KO and no supported productive prefix remains.  Emit the
exact KEEP attack.  A terminal attack in both worlds attacks immediately and
does not spend FML.

### APPROVE_PARENT_FML

The parent selected FML and PLAY_FML has an exact certified purpose.  Return the
same action and watch through Stadium resolution.  This is not an action
difference but is required lifecycle evidence.

An exact tie, unemittable HOLD, or incomplete comparison returns the parent
without claiming ownership.

## Lifecycle and state

Save game epoch, seat, first player, turn/action count, FML serial, prior
Stadium owner/serial, public fingerprint, attack semantic, both counterfactual
certificates, and first differing hard layer.

- Duplicate callback: rebind the same semantic role without advancing.
- After PLAY: verify FML left hand, became the sole Stadium, the displaced
  Stadium entered the correct owner's discard, PLAY log/action count match, and
  realized combat projection equals the saved certificate.
- Owned continuation: require the unique exact ATTACK option, emit it, and
  confirm its ATTACK log before completing.
- Owner collision, invalid action, exception, stale role, duplicate advancement,
  and post-spend mismatch are hard candidate faults; target count is zero.

The rule does not change Energy/deck contents and accounts for the one-card hand
to Stadium resource transition.  It may improve backup continuity only through
exact survival or supported Stadium displacement.  It never sacrifices an
immediate win or Prize for a lower defensive gain.

## Required engine fixtures

Positive in both seats:

- FML preserves the parent-selected KO and changes an exact opponent return from
  KO to survival.
- Both Active Pokémon are Metal: outgoing minus 30 still preserves our KO while
  return minus 30 removes theirs.
- Replacing an exactly supported hostile Stadium enables a terminal/current-
  Prize attack.
- Parent-selected FML resolves with exact displaced-Stadium ledger.

Negative/control in both seats where meaningful:

- FML saves the opposing Metal Active from a KEEP-world KO.
- Terminal attack in both worlds attacks immediately without FML.
- Weakness -> Resistance -> FML ordering.
- Damage counters are not reduced.
- Unsupported Stadium/effect, unknown reply, multiple incomparable attacks,
  live inherited owner, no actual ATTACK option, and first-player turn one all
  return the exact parent.
- Same-ID FML copies, option permutation, duplicate callback, seat inversion,
  and turn/result reset are deterministic.

Run focused engine fixtures twice byte-identically.  Require both seats and zero
invalid actions, exceptions, stale/postcondition faults, and max-step hits.

## Pre-edit census gate

Before any source edit, freeze a row-level FML opportunity census over the exact
207-replay / 209-target-seat corpus.  Each row records replay, seat, step, turn,
parent semantic action, live owner, FML role/serial, prior Stadium, actual legal
attack roles, KEEP and FML damage/Prize/return fields, exact classification, and
rejection reason.  Freeze its script, schema, source manifest, and hashes.

The census determines whether 172 historical FML plays contain enough exact
two-world opportunities; raw play count alone is not promotion evidence.

## Full-shadow gate

From the frozen implementation source and the same corpus require:

- reproduce all 172 natural FML turns;
- at least 40 exact two-world classifications, both seats, at least 20 replays;
- at least 20 complete owned starts, both seats, at least 10 replays;
- at least 12 first differences, both seats, at least eight replays;
- at least three PLAY-direction and three HOLD/VETO-direction differences;
- at least two independent mechanism classes;
- every difference root-audited `GOOD_CAUSAL`;
- trigger-external parent identity; zero owner overlap, unknown-as-zero,
  invalid, duplicate advancement, stale, or postcondition faults.

Failure is `RARE_NARROW_FAIL`; do not relax thresholds and do not run fixed-760.

## Fixed-760 adoption gate

Only after full-shadow PASS, run the immutable Silver200 + adjacent560 schedule.
Require exact key equality, 760 unique rows, and zero execution/action/max-step/
duplicate faults.  Required strength:

- overall at least `+16/760`, paired 95% CI lower bound above zero;
- Silver at least `+8/200`, both Silver seats nonregressing, practical absolute
  floor `108/200` if the established `100/200` A/A baseline reproduces;
- each overall seat at least `+4/380`;
- adjacent total nonregressing, any opponent-seat loss at most two and fully
  audited, existing Kangaskhan/Crustle floors retained;
- three of four contiguous seed blocks positive and none below `-2`;
- completed mechanism in both seats and at least four opponents;
- every parent-win/candidate-loss and action difference attributable to the
  symmetric Stadium mechanism.

## Deferred order

After FML: Lillie purpose/hold, then Jumbo Ice Cream heal-versus-Hammer tradeoff,
then broader Boss targeting.  Global attack-turn legality is mandatory shared
infrastructure, not a behavioral candidate.


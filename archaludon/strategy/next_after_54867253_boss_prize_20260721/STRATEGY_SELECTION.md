# Strategy selection — exact Prize-lane Boss arbitration v1

- Frozen by root: 2026-07-21 JST
- Implementation parent:
  `alakazam_finalized_super_psy_bolt_retreat_ready_alakazam_ko_bridge_v1`
- Parent source SHA-256:
  `7838FBFF3CBA3AE5D9142E45B1334B192A5E758CFFA5598AF2A626E5C7D636E3`
- Formal rollback SHA-256:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`
- Root evidence:
  `analysis/54867253_new17_boss_prize_20260721/ROOT_VERIFIED_EVIDENCE.md`
- Root evidence SHA-256:
  `289BF48C182BA0856624C2A23D35D01698FB15F35843FC58A9EF541C86E68431`

## Selected single hypothesis

Implement exactly one deterministic public-state rule:
`alakazam_exact_prize_lane_boss_arbitration_v1`.

The two verified Boss directions are one rule, not two stacked rules. At one
attack-ready decision boundary, compare the unchanged opponent Active lane
with every exact legal Boss target lane:

1. take a unique exact terminal lane;
2. otherwise, do not replace an exact lethal higher-Prize Active with a
   strictly lower-Prize Boss KO;
3. delegate everything else to the exact live parent.

Do not import the broad Boss-v1/v2 source wholesale. Prior implementations are
transaction references only.

## Ownership gate

Run the complete live parent first. This overlay may own a callback only when
all conditions hold:

1. No inherited transaction/latch owns, just completed, or just aborted.
2. The finalized live-parent action is either a legal Boss's Orders `1182`
   PLAY or the unique legal Powerful Hand `1072` ATTACK.
3. Own Active is exactly one complete, paid, positive-HP Alakazam `743`.
4. Exactly one legal Powerful Hand option is present.
5. The complete public hand/count, own Prizes, opponent Active/Bench, prize
   values, Energy, status, Stadium, protection/modifiers, and legal Boss
   options are exact and internally consistent.

Compute the unchanged Active lane with `20 * current handCount`. Compute each
semantic Boss-target lane with the exact post-Boss hand count and resulting
Powerful Hand damage. Certify exact public-clear KO and Prize value using the
existing conservative metadata/protection helpers. Determine whether the KO
ends the game.

Equivalent legal Boss copies collapse into one semantic target lane. If the
rule starts a Boss route, choose the lowest legal Boss option index
deterministically. Two or more distinct terminal targets are ambiguous and
must delegate.

## Decision ordering

1. If exactly one semantic lane is terminal:
   - unchanged Active terminal: return Powerful Hand immediately;
   - unique Boss target terminal: start the frozen Boss transaction.
2. If two or more terminal semantic lanes exist, delegate unchanged.
3. If no terminal lane exists, and the finalized parent chose Boss, and the
   unchanged Active is exact lethal with Prize value strictly greater than
   every exact lethal Boss lane, return Powerful Hand.
4. Otherwise delegate unchanged.

Never proactively choose a merely higher-Prize nonterminal Boss lane.

## Boss transaction

Freeze the chosen Boss card/serial, target serial, Active Alakazam, full
hand/count, Prizes, both public fields, Energy, Stadium/effects, and expected
post-Boss damage.

1. PLAY only the frozen deterministic Boss option.
2. At the exact Boss target prompt, require the certified transition and
   select only the frozen target.
3. At the resulting MAIN callback, require the exact Active/Bench permutation,
   exact post-Boss hand, unchanged attacker readiness, one unique lethal
   Powerful Hand, and the frozen target now Active; then attack.
4. Verify the attack/KO transition, clear only this latch, and delegate all
   Prize selection to the live parent.

Duplicate callbacks return the same cached action. Any mismatch, tie,
protection, damage shortfall, malformed option, state mutation, stale callback,
or failed continuation clears only this latch, restores/snapshots parent state
as required, and delegates to a genuine unfiltered live-parent decision.

## Mandatory positives

### Active Prize dominance

`87220395/S126`, seat 0:

- ready paid Alakazam, hand 15, Powerful Hand 300;
- opponent Active Mega Lucario ex at 100 HP, worth three Prizes;
- finalized parent plays Boss toward one-Prize Lunatone;
- candidate returns Powerful Hand on the unchanged Active and never starts the
  lower-Prize Boss detour.

### Unique terminal Boss lane

`87214287/S129`, seat 1:

- ready paid Alakazam, hand 25, own Prizes three;
- current Active Hariyama at 80 HP, worth one Prize;
- two equivalent legal Boss copies;
- unique Bench Mega Lucario ex at 340 HP, worth the final three Prizes;
- candidate deterministically PLAYs one Boss, selects that Mega Lucario,
  verifies post-Boss hand 24 / Powerful Hand 480, attacks, and completes the
  terminal three-Prize route.

Both complete routes must pass exact checked-engine transactions in both
semantic seats.

## Mandatory negatives

- Finalized parent action is setup, ATTACH, EVOLVE, ABILITY, another attack,
  RETREAT, or END.
- Active Alakazam/Powerful Hand is incomplete, unpaid, nonunique, illegal, or
  status-blocked.
- Multiple distinct terminal targets or equal-Prize ambiguity.
- Unknown Prize value, protection, modifier, hand, target, or Boss legality.
- Post-Boss Powerful Hand is insufficient.
- Boss lane is nonterminal and merely higher value.
- Active and best exact Boss lethal lanes have equal Prize value.
- Any inherited live latch is active, including the finalized retreat bridge.
- Every known broad Boss-v1 9/144 regression row remains exact-live-parent.
- All successful inherited Boss conversions, direct terminal attacks, setup,
  draw, attachment, evolution, retreat, and attack-continuity routes remain
  exact-live-parent unless the complete ownership gate proves one of the two
  Prize-lane decisions above.

## Mandatory causal bridge retention

Episode `87213204` must remain candidate-versus-live identical on every
callback: step 33 RETREAT, exact Energy payment, ready-Alakazam promotion,
Powerful Hand `1072`, and board-out win. Candidate-versus-H0/H1 first
difference remains step 33. The equivalent route must pass both semantic
seats.

## Minimum practical gates

- Exact parent diff; compile/import; legal unchanged 60-card deck with one ACE
  SPEC; loader-last callable; source/runtime parity; cache-free tree.
- Focused positives plus tie, duplicate-Boss, multiple-target, protection,
  damage-shortfall, metadata, duplicate-callback, abort, rollback, and all
  broad-v1 regression mutations.
- Current52 and historical callback-complete shadows against live, H0/H1, and
  formal rollback: every first change classified, all nonactivating callbacks
  live-identical, zero invalid actions, zero duplicate mismatches.
- Both-seat exact-engine completion for both positives and the complete
  episode-`87213204` retention transaction.
- Fixed paired both-seat smoke against Historical-Silver Archaludon, Mega
  Lucario, Alakazam mirror, and Starmie: zero action errors/max-step hits, no
  Historical-Silver seat regression, and no adjacent-opponent decline.
- Clean package/re-extract inventory and package-local both-seat smoke.
- Immediately before any Kaggle write, authenticated status/score/quota and
  exact episode-ID/replay refresh, with every genuinely new replay shadowed
  and inspected.

If every gate passes, one exploratory submission is permitted. It is not
formal adoption. Root alone packages and writes to Kaggle.

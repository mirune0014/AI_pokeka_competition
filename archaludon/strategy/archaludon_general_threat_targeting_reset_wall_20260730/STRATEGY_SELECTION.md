# Frozen strategy: public one-turn target dominance with ephemeral-chip veto v1

Date: 2026-07-30 JST

## Authority and parent

Implement one deterministic public-state component directly from:

`autonomous_gold_20260715/candidates/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2`

Frozen parent `main.py` SHA-256:

`DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`

Frozen historical-Silver anchor SHA-256:

`F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Frozen deck SHA-256:

`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Candidate destination:

`autonomous_gold_20260715/candidates/archaludon_cumulative_public_one_turn_target_dominance_v1`

Implementation evidence destination:

`autonomous_gold_20260715/implementation/archaludon_cumulative_public_one_turn_target_dominance_v1`

Do not stack the prepared Boss-ledger, normal two-Prize race, post-attachment
non-ex 120, or narrow Kadabra-only siblings.  The submitted eight-rule source
is the direct parent so that every changed action belongs to this mechanism.

## User-selected problem

The component must solve the general target-selection failure rather than copy
episode 88899620:

- an immediately KO-able low-threat Active may expose a much stronger Bench
  successor;
- a Boss KO of a Bench evolution bridge can take the same Prize while reducing
  the opponent's best next-turn response;
- nonlethal damage into a Pokemon that can return or fully reset itself may
  have zero persistent value and merely buy setup time;
- Duraludon, Archaludon ex, and non-ex Archaludon must use the same comparator;
- attack side effects such as Metal Defender, Coated Attack, and Turbo Flare
  must not be discarded merely because damage is nonlethal.

The motivating replay is:

`C:/Users/amuam/Downloads/88899620.json`

Replay SHA-256:

`D6C6D21FDA0DE8B083061A9FE390115F973127C13EA299F81B10F16546D6E98A`

The root-verified memo is:

`autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/DEFERRED_LOSS_MEMO_88899620_READY_KADABRA_BOSS_THREAT_REMOVAL.md`

The exact submitted eight-rule agent and the Silver parent made zero action
differences over all 33 correct-seat decisions in that replay.

## Selected component

Rule ID:

`PUBLIC_ONE_TURN_TARGET_DOMINANCE_WITH_EPHEMERAL_CHIP_VETO_V1`

This is one coherent public-state component with one Boss transaction.  It is
not a learned ranker, opponent-policy proxy, replay label, episode exception,
or deck-name rule.

### Activation boundary

Start only at an ordinary single-choice `MAIN` callback when:

1. the game is unresolved;
2. no cumulative transaction owner is active;
3. the exact parent selects exactly one currently legal `ATTACK`;
4. no attachment, evolution, retreat, search, or setup action is being
   preempted;
5. the exact Active serial, attack ID, payment, complete boards, Prizes,
   statuses, flags, Stadium, public counts, hand/discard material, legal option
   multiset, and supported modifiers are complete and unambiguous;
6. Boss's Orders is legal and uniquely bindable;
7. spending Boss leaves at least one other Boss in hand for every nonterminal
   use; a certified immediate winning KO may waive that reserve.

### Compared lanes

Compare:

- the exact parent attack into the current Active, including whether it KOs;
- Boss plus that same exact attack into every Bench target that the attack
  exactly KOs.

Boss non-KO lanes are outside v1.  The attacker and attack ID must remain
identical in every compared lane.  This keeps payment, backup readiness, and
the attack's public side effect comparable.

### Exact own-attack closure

Support the current deck's printed attacks:

- Hammer In `223`;
- Raging Hammer `224`;
- Metal Defender `253`;
- Coated Attack `1212`;
- Turbo Flare `965`.

Exact damage, weakness, resistance, Stadium, Tool, conditions, attack
prevention, and attack-specific effects must be accounted for.  Any unsupported
effect makes the component ineligible.

Turbo Flare's target-independent acceleration remains valuable even when its
damage is nonlethal.  If a Boss-plus-Turbo-Flare KO transaction is selected,
the component owns only Boss, target, and the attack; subsequent acceleration
callbacks are delegated to the actual parent after the attack log.

### One-opponent-turn threat envelope

For each post-action board, conservatively calculate every surviving visible
Pokemon's one-turn reachable threat:

- it may become Active;
- it receives the mandatory next-turn draw;
- at most one ordinary manual Energy attachment is allowed;
- at most one legal evolution is allowed from the structural evolution graph;
- deterministic evolution and attack abilities are included;
- damage and damage-counter channels remain distinct;
- attack lock, forced switch, protection, immediate Prize exposure, ready
  route count, and deterministic setup/draw gain are retained.

Threat vector:

`T = (terminal_or_board_out_routes, attack_lock_routes, max_prizes_exposed,
max_effective_damage_or_counters, ready_route_count,
deterministic_setup_gain)`

The structural registry comes from `all_card_data()` and records ID, name,
stage, `evolvesFrom`, HP, Prize class, type, Weakness, Resistance, retreat,
Tera, attacks, skills, and an exact metadata digest.

The initial exact semantic closure must include:

- Dunsparce `65` and `305`;
- Dudunsparce `66`;
- Abra `741`;
- Kadabra `742`;
- Alakazam `743`;
- attacks `74`, `75`, `76`, `423`, `424`, `1070`, `1071`, and `1072`;
- Run Away Draw, Psychic Draw, Powerful Hand, Teleportation Attack, and their
  exact printed metadata;
- Basic and attached special Energy semantics needed by these boards;
- Full Metal Lab and all visible modifiers present in a positive.

An unknown card, successor, attack, Ability, Tool, Stadium, Energy, status,
protection, Prize modifier, or damage modifier returns `UNKNOWN` and blocks
the component.

### Hard dominance

A Boss lane is eligible only when all clauses hold:

1. its immediate Prizes are at least the parent lane's;
2. it does not displace a current terminal, board-out, final-Prize, or
   higher-Prize deterministic route;
3. the parent's exact attack benefit and our attack continuity are no worse;
4. `T_boss <= T_parent` componentwise;
5. at least one threat-vector component is strictly lower;
6. if the parent lane contains a one-turn lethal or lock route, the Boss KO
   removes every such public route rather than only one duplicate;
7. exactly one target hard-dominates.

Only already eligible targets may be tie-broken with:

`100000*terminal_routes_removed
+10000*lock_routes_removed
+1000*extra_prizes
+100*ready_routes_removed
+30*deterministic_draw_denied
+20*attached_energy_removed
+10*tools_removed
+10*effective_damage_drop`

An equal maximum fails closed to the parent.

Kadabra wins a positive because its registered public successor creates a
stronger one-turn route, not because a branch checks `cardId == 742`.

## Ephemeral-chip semantics

Register return/heal effects by exact normalized metadata text and digest:

- `SELF_RETURN_ALL_ATTACHED_AFTER_DRAW`;
- `FULL_HEAL_BEFORE_DAMAGE_MATTERS`;
- future classes only after their complete semantics are supported.

Dudunsparce `66` is the first required exact member:

`Once during your turn, you may draw 3 cards. If you drew any cards in this
way, shuffle this Pokemon and all attached cards into your deck.`

For a non-KO parent attack into a certified resettable target:

- persistent damage is zero;
- the target's deterministic setup/draw gain remains;
- the attack's target-independent effect remains fully credited.

Exact KO bypasses the ephemeral-chip classification.

V1 never replaces an otherwise legal chip attack with `END` merely because
damage is ephemeral.  It changes the action only when a certified exact Bench
KO hard-dominates.  With no dominating Bench KO, it preserves the parent.  This
prevents accidental loss of Turbo Flare acceleration or useful defensive
effects.

## Precedence

Preserve:

1. rank 0 engine/result safety;
2. rank 1 exact-parent terminal;
3. rank 2 active transaction owner;
4. the existing eight components at ranks 3 through 10;
5. this component at rank 11;
6. exact historical parent fallback at rank 12.

The component is ineligible while any existing owner is active.  It does not
edit the parent scoring or any existing component.

## Transaction

Stages:

`BOSS_PLAY -> EXACT_TARGET_SERIAL -> SAME_EXACT_ATTACK -> CLEAR`

Requirements:

- snapshot complete public material and semantic option keys;
- select the lowest eligible Boss serial and lowest equivalent position;
- bind exactly one unique hard-dominating target serial;
- after the switch, revalidate the same attacker, attack payment, target,
  damage, Prize yield, attack effect, and threat dominance;
- bind only the original exact attack ID;
- returning an option never advances state;
- advance only on novel public log/material confirmation;
- identical retries rebind semantically and return the same action;
- target ambiguity, option mutation, board mutation, metadata mismatch,
  exception, owner collision, or missing serial clears and delegates to the
  actual exact parent;
- after irreversible Boss use, never invent a replacement target or attack;
- clear immediately after the attack log.

## Required synthetic positives

For both logical seats, repeated callbacks, equivalent duplicate options, and
option-order permutations:

1. Duraludon/Raging Hammer:
   Active Abra at 50 HP and unique Bench Kadabra at 80 HP, same one-Prize
   yield, public Alakazam successor creates the stronger response, and two
   Boss remain before play.  Emit Boss, exact Kadabra serial, exact Raging
   Hammer.
2. Archaludon ex/Metal Defender:
   a same-Prize Active KO is available, but an exact Bench KO uniquely removes
   a catastrophic public one-turn route.  Emit Boss, exact target, Metal
   Defender.  Retain the no-Weakness effect in both lanes.
3. Non-ex Archaludon/Coated Attack:
   full-HP Dudunsparce `66` at 140 HP is a non-KO resettable Active, while one
   80-HP Bench evolution bridge is an exact Coated Attack KO.  Treat the Active
   damage as ephemeral, retain Coated protection, and emit Boss, bridge, Coated
   Attack.
4. A generic structural successor variant with different supported card IDs
   must trigger from metadata/evolution/threat semantics rather than an
   explicit Kadabra ID branch.

## Required positive preservation

1. Dudunsparce at exact-KO remaining HP: reset veto is off and the parent KO
   remains legal unless another lane independently hard-dominates.
2. Turbo Flare into non-KO Dudunsparce with no dominating Bench KO: parent
   Turbo Flare and its acceleration continuation remain unchanged.
3. Low-threat non-reset Active, non-KO, no dominating Bench KO: parent remains
   unchanged.

## Required negatives

At minimum:

- parent terminal or board-out;
- active existing owner and every existing clear-component collision;
- equal/unknown rank collision;
- duplicate equally dominant targets;
- alternate lethal/lock route remaining after the candidate KO;
- lower immediate Prize Boss lane;
- only one Boss for a nonterminal use;
- supporter already used or Boss absent;
- Boss target is non-KO;
- attack changes between lanes;
- unsupported/variable attack effect;
- unsupported card, successor, Ability, Energy, Tool, Stadium, status,
  prevention, Prize, weakness, resistance, or metadata digest;
- target HP, serial, option, board, hand/discard material, or flags change
  during the transaction;
- target no longer Active after Boss;
- same target has an unknown healing/return route;
- exact parent side effect or attack continuity is worse in the Boss lane;
- resettable Active is non-KO but no superior exact Bench KO exists;
- exact-KO resettable Active;
- exception, reset, retry, turn/seat change, and result.

Every negative must be exact-parent identical.  Require zero invalid actions,
exceptions, stale owners, action errors, or max-step hits.

## Verification and packaging policy

The user explicitly requested destructive-safety only:

- compile/import;
- legal 60-card deck with exactly one ACE SPEC;
- exact source-parent diff;
- required synthetic positives and negatives;
- both logical seats;
- duplicate/retry and option-order determinism;
- exact transaction completion;
- updated collision registry;
- loader-last emulation;
- cache-free candidate tree;
- clean archive contents and packaged positive/negative smoke.

Do not run fixed-760, a full historical replay shadow, or local win-rate
evaluation for this candidate.  Synthetic success proves only that the intended
mechanism fires and that the tested destructive failures are absent.


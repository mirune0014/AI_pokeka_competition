# Strategy selection: certified prize-lead one-Prize Active KO lock v1

## Decision

**SELECT hypothesis 1 and implement exactly one isolated rule.**

Destination:
`autonomous_gold_20260715/candidates/alakazam_certified_prize_lead_one_prize_active_ko_lock_v1`.

The only implementation parent is
`autonomous_gold_20260715/candidates/alakazam_guarded_teleportation_attack_continuity_v1`:

- source SHA-256:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`;
- runtime SHA-256:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- legal deck SHA-256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Do not inherit from, import, wrap, or edit the submitted unique-Mist source.
Do not add Dawn alignment, lone-Psyduck rescue, Night Stretcher targeting,
Sacred Ash timing, Boss-readiness repair, or any other sibling. The deck and
runtime remain byte-identical to the parent.

### One invariant

When an old, already paid Active Alakazam has one unique, currently legal and
exactly lethal Powerful Hand against the unchanged complete one-Prize Active,
own remaining Prizes are at least two, and own remaining Prizes lead the
opponent's by at least two, do not spend hand/deck/recovery/Boss resources
before that **nonterminal** KO, provided the formed-board,
parent-action-class, and no-higher-Prize-route guards below pass.

Prize-terminal and board-terminal behavior is outside this new invariant.
Preserve whatever the guarded parent already does there; do not import or
reimplement the earlier direct-terminal Powerful Hand rule.

This is an observable-state deck-theory rule. It contains no episode ID, team
name, opponent ID, score, hidden opponent card, replay action label, or learned
ranking.

## Verified facts used

The root evidence packet has SHA-256
`DC8CED220B974A590E48B81BE9763222F6C025EF6FDFF2F24E2E3EDA81E985B2`.
The guarded parent reproduced the submitted source on all 1,331 target-seat
callbacks through twenty public games: zero invalid actions, zero action
differences, and zero unique-Mist starts/targets/attacks/resolutions/aborts.
Thus the diagnosed actions are guarded-parent behavior, not Mist behavior.

Three independent mirror losses expose the same reachable nonterminal first
decision in both seats:

- `87076890/S173`, seat 0: Prizes `2/6`, deck `1`, hand `13`; old paid
  Alakazam versus 50-HP one-Prize Kadabra; unique Powerful Hand option `4`,
  `260` lethal. Parent played Dawn, drew the last deck card, then attacked and
  later lost on the mandatory draw clock.
- `87079669/S81`, seat 0: Prizes `4/6`, deck `11`, hand `4`; old paid
  Alakazam versus 50-HP one-Prize Abra; unique option `9`, `80` lethal. Parent
  entered Psychic Draw and then spent Poke Pad, two Helmets, Run Away Draw,
  Night Stretcher/Energy, and Boss before taking the same one Prize. The
  publicly observed escape package was no longer available after a later gust.
- `87087306/S82`, seat 1: Prizes `3/6`, deck `8`, hand `22`; old paid
  Alakazam versus 50-HP one-Prize Abra; unique option `38`, `440` lethal.
  Parent chose Poke Pad, spent tools and Boss, gusted an equal-value Dunsparce,
  and only then attacked. Root's exact verifier re-executed all 84 target-seat
  callbacks with zero invalid actions or candidate-parent differences. The
  verifier/output SHA-256 values are
  `880FB15513AE336DD841C4BB92FD9D14AB05CA66D087DA25D25F0E3AF7258AA1`
  and
  `236EC02E72F610897CAF94E4C24074D47AE9D97D3105E44AC9B1726519836EB9`.

The same `87087306` parent trajectory supplies a terminal boundary at S147:
Prizes `1/5`, deck `2`, hand `7`, old paid Alakazam versus 140-HP one-Prize
Alakazam, unique Powerful Hand option `8`, exact `140` lethal. Parent spent
Poffin/draw/Poffin/Hilda, reached deck `0` and hand `6`, attacked for only
`120`, and lost. This is prior-art territory, not a positive for this
candidate: it is downstream of the earlier S82 first difference, and the
selected helper must not start when `P == 1`. Use S147 only as a retention
negative and never count it as a reachable activation.

The twenty-game score and `8-12` record were not used to choose the rule. The
selection rests on the repeated action-level mechanism: three reachable
nonterminal opportunities in three losses, across both seats. S147 contributes
no hypothesis support.

Guarded-parent strength anchors are the root-verified fixed-144 results:
`89/144`, P0 `48/72`, P1 `41/72`, known `47/72`, fresh `42/72`, Historical
Silver `8/16`, and `3G/0R` versus exact-v3. These are retention floors, not an
argument that the parent was formally adopted.

## Why this hypothesis wins

It has the strongest causal and frequency profile of the three offered rules.
The first anchor is a high-confidence deck-clock cause, the second is a
medium-high-confidence recovery/escape sequencing cause, and the third is an
independently root-verified recurrence in the other seat. All begin from a
currently legal KO, so no future draw, evolution, Energy, or hidden card is
assumed.

Dawn energized-Abra alignment has one medium-confidence counterfactual anchor
(`87080205/S75`) and did not recur in the three new mirror losses. The
lone-Psyduck Hilda-Enriching extension has one high-confidence policy error
but only low-to-medium outcome confidence because the four-card draw can
whiff; it did not recur in either new Mega-Lucario loss. The new Lucario Boss
readiness defect is real and root-verified, but it is outside the frozen three
choices and remains next-cycle evidence only. Its verifier/output SHA-256
values are
`299DD0AA20DC10D729EDC9F25A9B2155410043E2DBB920E982DFD48C70FD9040`
and
`1F00D9D0D28FDF9CC01388A6B29A4447ED05CA5E6AFF4937D628D390CC392CD2`;
this candidate must remain parent-identical at those Abra/no-ready-attack
states.

Across the complete game plan, the selected rule starts only after setup has
already produced an old paid Alakazam and, for a nonterminal KO, a formed
backup line. It preserves hand size, deck clock, Night Stretcher/Energy, and
Boss; advances the Prize exchange immediately; avoids replacing an equal-value
Active; and keeps disruption resources for a later gust/escape cycle. It does
not choose an attacker, form the initial board, spend Energy, or predict the
opponent. Its main regression risk is attacking before useful deterministic
setup, which is why nonterminal starts are restricted to a mature board and a
finite detour whitelist rather than a global "attack every KO" rule.

## Implementation-ready behavioral contract

Let `P` be own remaining Prizes, `O` opponent remaining Prizes, `H` the exact
own hand length, and `T` the exact current opponent Active. The lead condition
is `O - P >= 2` because fewer remaining Prizes is ahead.

### Base certificate

Evaluate the helper only on the guarded parent's ordinary live MAIN callback,
after boundary cleanup and duplicate-cache lookup. Every clause must pass:

1. `result == -1`, `looking is None`, turn at least two, exact single-choice
   MAIN envelope, and one legal selection is required. Raw and parsed player,
   turn, ownership, zones, counts, card IDs, serials, and option mappings agree.
2. No inherited latch/quarantine owner existed at entry and none is active:
   Hilda source, Enriching reserve, Fez bridge, active-Psychic KO, stranded
   retreat, or guarded Teleportation. If boundary preparation just cleared a
   stale owner, delegate this entire callback; do not restart here.
3. Own field has exactly one Active: Alakazam `743`, `appearThisTurn == false`,
   unstatused, correct owner, positive serial/HP, exact printed-plus-public
   max HP, complete pre-evolution/Tool/Energy stack, and exact public Energy
   units that currently pay Powerful Hand. No attachment, evolution, switch,
   retreat, or draw may be needed.
4. The option set contains exactly one fully encoded legal
   `ATTACK/attackId=1072` and no malformed or competing attack encoding. The
   attack metadata and payment are exact. Own hand is serial-complete and
   `len(hand) == handCount == H`; require `20 * H >= T.hp`. Credit no future
   search, draw, Prize card, or speculative `max_hand_size`.
5. Opponent has exactly one unchanged Active `T`, with correct owner and
   positive unique serial/HP, exact max HP and stack, and exact Prize value
   `prize_count(T) == 1`. Every public Tool, Energy, Stadium, status, Ability,
   effect, and relevant log is understood. Mist, applicable Rock protection,
   Psychic resistance, unknown special Energy/effect text, prevention,
   variable HP, transient protection, malformed stack, or helper disagreement
   fails closed.
6. `P >= 2`, `O >= 1`, and `O - P >= 2`. `P == 1` is expressly out of scope.

### Nonterminal branch and precedence

Require all of the following in addition to the base certificate:

- the opponent has at least one complete Benched Pokemon, so this is not a
  disguised board-terminal rule;
- own Bench contains at least one complete serial-distinct Kadabra or
  Alakazam, establishing a formed backup line before setup is curtailed;
- the guarded parent has computed one unique finalized ordinary action and it
  is a certified resource detour: PLAY of Dawn, Hilda, Poke Pad, Night
  Stretcher, Sacred Ash, or Boss's Orders; exact Lucky Helmet attachment; or an
  exact known optional draw Ability on Kadabra/Alakazam, Dudunsparce, or
  Fezandipiti ex. Unknown abilities/actions fail closed;
- do not override evolution, Rare Candy, Buddy-Buddy Poffin, Basic benching,
  Psychic/Enriching Energy attachment, Enhanced Hammer, Stadium, retreat, END,
  another attack, or any unclassified action;
- there is no strictly higher certified current-turn Prize route. Inspect
  every complete opponent Bench target and the current legal Boss option. A
  route is higher only if Boss's one-card hand cost leaves a currently payable
  exact Powerful Hand (`20 * (H - 1)`) that KOs a clear target worth more than
  one Prize, or wins the game when the Active KO does not. Any incomplete
  Bench, switch/protection ambiguity, or uncertain prize/HP calculation vetoes
  the new rule. An equal one-Prize gust is not higher; preserve Boss and take
  the unchanged Active.

All inherited behavior—including any parent-owned terminal behavior—keeps its
existing precedence. This candidate adds no `P == 1` or empty-opponent-Bench
branch.

If the finalized parent already selected the same Powerful Hand, return exact
parent identity and do not count a start.

### Ordering, state, cache, rollback, and fail-closed behavior

Keep all inherited continuation overlays and the active-Psychic attach-to-KO
start ahead of this rule. Compute the parent's complete scores and overlays,
including its Run Away/fragile guard and Fez start, before classifying the
final action. Insert this pure helper after that finalized choice and before
guarded-Teleportation/stranded starts and before arming a new Hilda source
latch. Because the nonterminal whitelist excludes RETREAT and END, it cannot
steal either later transaction.

This is one atomic decision, not a multi-callback latch. It creates no new
persistent transaction state and mutates no inherited latch, ability flag, or
quarantine state. Return the selected physical option index through the
existing `_remember_action` cache; an identical callback returns the cached
attack without re-running the parent. On a distinct observation, turn/seat/
game boundary, exception, ambiguity, or failed predicate, clear only ordinary
cache as the parent already does and return the exact guarded-parent action.

There is no post-action rollback: an emitted attack cannot be undone. Safety
therefore comes entirely from the pre-action certificate. The following Prize
selection, KO resolution, next promotion, or terminal callback is delegated
unchanged to the parent. External trace telemetry, not gameplay state, records
`nonterminal_start`, selected attack, KO/Prize resolution, and the first failed
predicate.

The Kaggle loader must still resolve this candidate's `agent` as the final/last
callable. No helper or donor callable may follow it.

## Frozen anchors and focused tests

Mandatory positives:

- `87076890/S173`: Dawn `0` -> Powerful Hand `4`;
- `87079669/S81`: Psychic Draw `0` -> Powerful Hand `9`;
- `87087306/S82`: Poke Pad `30` -> Powerful Hand `38`.

For each, assert unchanged card/serial ownership, target, damage, Prize value,
lead, option set, and zero inherited-state mutation. Permute irrelevant option
order and physical duplicate resource cards; resolve the attack by exact
option metadata, never a frozen index.

Mandatory negatives retain guarded-parent identity:

- `87080205/S75` Dawn Stage-1 selection and `87080766/S25` lone Psyduck;
- root-verified Boss-readiness states `87085133/S20` and `/S45` because no
  ready Active Alakazam/Powerful Hand exists;
- prior three-Prize setup anchors, including `86991375/S53`, `86972084/S130`,
  and `86981695/S121`, because the target is not one Prize;
- direct-terminal board-out-only and multi-Prize anchors from `86947939` and
  `86948467`, plus prize-terminal `87087306/S147`; all must retain exact parent
  behavior because terminal behavior is outside the selected domain;
- active Kadabra stage-up anchors: wrong Active and future evolution/draw;
- mandatory-draw reserve and Hilda/Enriching fixtures: Energy attachment,
  singleton rescue, or selection-latch behavior is never changed;
- lead `0/1`, tied/trailing Prizes, target Prize value `0/2/3`, nonterminal
  empty opponent Bench, no formed backup, appeared-this-turn/unpaid/statused
  Alakazam, insufficient hand, multiple/malformed attack, protection or max-HP
  uncertainty, Legacy prize ambiguity, and a certified higher-Prize Boss KO;
- finalized EVOLVE, Poffin/Rare Candy/Basic setup, Energy attachment, Hammer,
  Stadium, RETREAT, END, and unclassified parent actions;
- each inherited latch active, each stale-latch cleanup, repeated callback,
  option permutation, duplicate serial, wrong owner, changed turn/player,
  malformed raw state, exception path, and failed effect-card metadata.

Run all existing guarded Teleportation positives/negatives, Hilda-Enriching,
Fez, active-Psychic, stranded-retreat, strict-Prize, setup, recovery, Boss,
and terminal-attack retention suites unchanged. Static audit must find zero
episode/team/opponent IDs and no score-based condition.

## Full-engine, shadow, and evaluation gates

### Structural and mechanism proof

Require compile/import, exact legal 60 cards and one ACE SPEC, byte-identical
runtime/deck, deterministic valid initial action, cache-free tree, exact
last-callable loader emulation, and packaged Historical-Silver smoke in both
seats. Action errors and max-step hits must be zero.

Complete at least three checked-engine `MAIN -> Powerful Hand -> KO ->
mandatory Prize callback` continuations: the two original nonterminal states
and the S82 seat-1 recurrence. Reindex at least one fixture to the opposite
seat. The continuations must leave the intended deck/hand/recovery/Boss
resources unspent through attack resolution. Separately prove exact parent
identity at S147 and the prior direct-terminal fixtures. Also run exact-engine
higher-Prize Boss, protection, stale-owner, and malformed-state aborts.

Shadow the complete twenty-public `54853109` target-seat set and the existing
checked historical live corpus against exact guarded parent, with a frozen
replay manifest before execution. Require zero illegal actions and classify
every first difference. The reachable first differences must include exactly
S173, S81, and S82 above. S147 on an isolated shadow must remain parent-equal;
on the recorded parent continuation it is downstream/unreachable after S82
and is never counted. All Boss-readiness,
Dawn-alignment, Psyduck, active-Kadabra, reserve, and existing-parent
transaction states remain unchanged outside this certificate. Any
unclassified first difference rejects the candidate.

### Compact-72 immutable screen

Use the checked schedule
`autonomous_gold_20260715/evaluations/alakazam_active_psychic_immediate_ko_transaction_v1/PHASE0_SCHEDULE.csv`,
SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`.
Select exactly seeds `2026071586`, `2026071600`, `2026101801`, and
`2026101804`, retaining original block/opponent/seat/order: nine opponents,
both seats, 72 unique keys, one engine-seeded game per key, max steps 1000 and
trace options enabled.

Run `parent_primary`, `candidate_primary`, and `candidate_duplicate`: 216
commands. Keys/order must match exactly; candidate duplicate normalized
summaries and trace bytes must match `72/72`; exits, action errors, max-step
hits, nonempty stderr, missing/extra/duplicate keys, and raw-hash mismatches
must all be zero.

The compact extraction of the root-verified guarded fixed-144 raw rows is
parent `39/72`: P0 `21/36`, P1 `18/36`, known `25/36`, fresh `14/36`;
opponent floors are Historical Silver `3/8`, Mega Lucario `7/8`, Starmie
`3/8`, Dragapult `7/8`, Marnie `5/8`, Great Tusk `1/8`,
Kangaskhan/Crustle `6/8`, Alakazam oselcoun `3/8`, and Alakazam rmy `4/8`.
Root must independently recompute these parent rows before judging the
candidate; disagreement invalidates the screen rather than moving a gate.

Exploratory-retention eligibility requires candidate at least `39/72`, zero
paired regressions, P0/P1 and known/fresh no lower than `21/18` and `25/14`,
every opponent at least its listed floor, duplicate identity, zero faults, all
shadow/mechanism gates, and no mechanism-first loss. A local gain is not
required only because three natural reachable nonterminal live anchors span
both seats. Passing this gate permits return to a final judge for at most one
packaged exploratory probe under the user's practical preference; it is not
adoption or automatic Kaggle permission.

Formal adoption cannot rest on a tiny paired delta or compact retention. The
compact screen must first reach at least `42/72`, at least `3G/0R`, gains in
both seats and both known/fresh blocks, combined Alakazam mirrors at least
`9/16` with two mechanism-linked gains, Historical Silver at least `4/8` with
a mechanism-linked gain, and no adjacent-opponent decline. It must also show
at least four natural completed starts across both seats, two seeds, and two
opponents.

If those conditions pass, confirm on the full 144-key schedule: candidate at
least `92/144`, at least `3G/0R`, P0 at least `48/72`, P1 at least `42/72`,
known at least `47/72`, fresh at least `43/72`, Historical Silver at least
`9/16` with a gain and no seat regression, and every guarded-parent opponent
floor retained. Require repeated nonterminal mechanism-linked outcome
movement, both-seat safety, zero faults, and no action outside the intended
rule. Only a later independent Sol-Ultra judgment may adopt it.

## Prior-corridor audit: not a disguised retry

- Direct-terminal Powerful Hand source
  `FB739274DDD5410251B0E9B5B21663D2E87328DBCEDA99AC1D68E2438EB47390`
  already implemented and was submitted with the certificate “all remaining
  Prizes covered or opponent Bench empty”; the submission later scored
  `670.8`. Its root presubmit decision is
  `pre_submit/alakazam_direct_terminal_powerful_hand_v1/ROOT_PRESUBMIT_DECISION.md`
  (SHA-256
  `A344B87783D4DCF783AF49F1145D408C99FD42E887FD66C8475ED7A3DBFA7019`).
  It had compact `38/72, 0G/0R`, was mechanically sound, and was not adopted.
  Therefore S147 cannot justify this selection, and adding any terminal branch
  would be a disguised retry. This candidate is driven exclusively by the
  three reachable **nonterminal** one-Prize/prize-lead resource errors; all
  Prize-terminal and board-terminal states stay exact-parent behavior and
  cannot satisfy any mechanism or adoption gate.
- Three-Prize pre-KO setup v2 was rejected at `38/72`, Historical Silver
  `3/8`, with zero proved setup transactions. This rule requires target Prize
  value exactly one and does not execute any setup route; its nonterminal
  guard does not override evolution/Poffin/Rare Candy/Energy attachment.
- Mandatory-draw reserve/Kadabra resource-first was rejected at `87/144`,
  `1G/0R`, Silver `8/16`. It suppressed reserve/resource actions based on a
  future draw clock and never activated its Hammer route. This rule never
  maintains a reserve latch or generically suppresses Energy/Enriching; it
  selects a currently legal lethal attack.
- Active-Kadabra stage-up spent an evolution plus a three-card draw from low
  deck counts and remained exploratory at parity. This rule requires an old
  already evolved, already paid Alakazam and predicts no draw.
- Hilda-first Energy relay failed before implementation because the second
  Energy was not publicly guaranteed. Lone-Dunsparce Hilda-Enriching is an
  accepted inherited transaction but historically sparse. This rule neither
  chooses Hilda's selections nor attaches Enriching nor creates a reserve; all
  such callbacks remain inherited behavior.

## Regression risks, uncertainty, and exact evidence needed next

The nonterminal attack can forgo useful setup, a dangerous equal-Prize gust,
or backup Energy placement; a prize lead does not guarantee the Active will
survive disruption. The mature-board and detour whitelist reduce but do not
eliminate that risk. Hand-dependent damage, HP modifiers, Legacy Energy,
counter prevention, transient effects, stale latches, and downstream replay
rows are implementation hazards. The observed opportunities are repeated but
still only three independent parent trajectories; only the first is a
high-confidence causal deck-clock diagnosis, and no candidate full-game outcome
has yet been measured.

Next evidence, in exact order:

1. one Sol-xhigh worker's isolated source, diff, source/runtime/deck hashes,
   focused results, loader/legality result, and checked-engine continuations;
2. root verification of the three positive anchors, terminal retention
   negatives, every other mandatory negative, inherited state non-mutation,
   and current-plus-historical first-difference shadow;
3. immutable compact-72 freeze, raw ledger/rows/traces, candidate duplicate,
   and exact hashes from the deterministic runner;
4. independent Sol-Ultra recomputation of wins, paired changes, uncertainty,
   seats/blocks/opponents, mechanism incidence, action errors and max steps,
   followed by root recomputation of every critical column;
5. a new Sol-Ultra rule-level accept/reject judgment. If compact retention
   passes without practical/primary-anchor movement, the only permissible
   positive disposition is one explicitly exploratory probe; if any retention
   or semantic gate fails, reject and use the separately verified Boss
   readiness defect as a future isolated selection, never as an in-place patch.

# Strategy selection: certified unique-Active-Mist Hammer KO transaction v1

## Decision

**BUILD exactly one isolated public-state rule:** when the unchanged parent has
already finalized Enhanced Hammer, redirect its mandatory Energy target to the
opponent Active's unique Mist Energy only when that removal certifies an
immediate, payable Powerful Hand KO; then lock that attack. Do not add Boss
stalling, Kadabra lanes, generic protection removal, or any other replay fix.

Implementation parent:

- `candidates/alakazam_guarded_teleportation_attack_continuity_v1/main.py`
- source SHA-256
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`
- unchanged 60-card deck SHA-256
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

The exact-v3 source
`49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`
is the immutable rollback and secondary comparator. The submitted CB52 source
is not the parent.

### Why guarded Teleportation is the practical parent

This does **not** reverse its earlier formal rejection. Guarded Teleportation
scored `89/144` versus exact-v3 `86/144`, with three paired gains and zero
regressions, but missed the frozen Historical-Silver, P1, fresh, and
Kangaskhan-Crustle floors. Its live-best `778.9` is whole-artifact evidence,
not causal evidence for the overlay: the checked first 42 live games contained
zero guarded starts and zero action differences from exact-v3. Nevertheless,
it is the strongest practical complete Alakazam artifact on both the fixed
panel and live score, its six audited changes were mechanism-correct, and its
Teleportation context is disjoint from an Enhanced-Hammer target callback.
It is therefore the least speculative practical parent for one exploratory
probe, while exact-v3 remains mandatory as the anti-stacking safety comparator.

CB52 is excluded because submission `54841997` was `22-20`, score `661.1979`,
at the root-verified 2026-07-20 13:47 JST refresh, and its extra exposed-
Dudunsparce mechanism did not fire in the audited live block. Its proposed
three-prize pre-KO successor also failed `38/72`, Historical-Silver `3/8`, and
proved zero setup/guard transactions. Continuing that stacked genealogy is
less justified than rolling back to the strongest compact policy.

## Verified mechanism evidence

The positive anchor is episode `86987527`, steps `61-65`. Before Enhanced
Hammer, Active Alakazam had Telepath Psychic Energy and eight cards. At the
step-62 `DISCARD_ENERGY` callback, after Hammer left hand, seven cards remained.
The opposing Active was a 130-HP Crustle with exactly one Mist Energy. The
parent discarded a benched Mist, then spent Boss and dealt only 120 to a
170-HP target. Selecting the Active Mist instead preserves Boss, leaves
Powerful Hand payable, and certifies `7 * 20 = 140 >= 130`.

Episode `86660075` independently establishes the deck-theory failure family:
Powerful Hand placed zero counters into a Mist wall, and an earlier Hammer
selected Spiky before Mist even though Spiky does not stop damage-counter
placement. It is supporting domain evidence, not a counterfactual win label.

The decisive negative is `86992980`, steps `79-81`: the Active had two Mist
Energy, so one Hammer could not remove protection. It must remain parent-
identical. `86993519` is also negative because no Hammer-to-lethal certificate
existed. Any unenergized attacker, non-Mist protection, hidden/uncertain
modifier, or nonlethal post-Hammer count is negative.

## Frozen behavioral contract

### Start certificate

Evaluate only after the guarded parent and all inherited latches have produced
their ordinary final `MAIN` choice. Start only when every condition is true:

1. No inherited or guarded latch is active, selection is single-choice `MAIN`,
   and the parent's exact selected option is one specific Enhanced Hammer
   `PLAY`. The overlay may not make Hammer top-ranked.
2. Own Active is an exact public Alakazam with a currently payable, uniquely
   identifiable Powerful Hand. No attachment, retreat, evolution, switch, or
   future draw is needed to attack.
3. The unchanged opponent Active has exact serial, current HP, Prize value,
   status, Tool, Ability, attached-card fingerprints, and modifier state. It
   has exactly one attached Mist Energy and no second Energy, Tool, Ability,
   Stadium, status, or other public effect that would still prevent Powerful
   Hand's damage counters after that Mist is removed.
4. Let `H` be the exact current hand count before Hammer and `H1 = H - 1`.
   Require `20 * H1 >= active_hp` and the one-card lethal cliff
   `20 * (H1 - 1) < active_hp`. Credit no future draw, search, prize card,
   evolution draw, or hidden identity.
5. No unused public fixed-count hand-increase Ability or already-legal
   evolution route can be certified to improve setup while retaining the KO;
   otherwise delegate. This prevents repeating the rejected pre-KO rule's
   tendency to preempt useful setup.
6. There is no publicly certified post-Hammer Boss target that is an exact
   same-turn KO for more Prizes, or that wins the game when the Active KO does
   not. Boss damage uses the exact post-Boss hand floor `H1 - 1`; optimistic
   search or draw is forbidden.
7. Deck/Prize counts, attack modifiers, and all card-to-Energy-unit mappings
   are exact. Any unknown, duplicate ambiguity, malformed option, or helper
   disagreement fails closed.

Return the exact parent Hammer option and arm one transaction. This preserves
setup, board formation, attacker and backup readiness, Energy placement, and
all resource use before the parent already commits Hammer. The one-card cliff
and absence of a certified safe setup route make the immediate Prize strictly
safer than spending another hand card. The attack uses no deck cards, preserves
Boss, advances the Prize exchange, and prevents a zero-output attack.

### Transaction stages

`await_hammer_target`

- Accept only the immediate same-turn `DISCARD_ENERGY` callback with
  `minCount == maxCount == 1`.
- Revalidate player, turn, attacker, opponent Active, HP, Prizes, Stadium,
  hand/discard delta, every attached Energy fingerprint, and the unique Mist.
- Resolve the target by `(opponent player, Active area, Pokemon serial,
  Energy serial, Energy card id)`, never by a stale option index.
- Choose only the exact option for the frozen Active Mist. Repeated identical
  callbacks return the cached action without advancing.

`await_attack`

- Require Hammer resolution, the same Active and attacker, the frozen Mist
  absent, no remaining counter-prevention, unchanged HP/Prize/field facts, the
  exact `H1` hand count, and one legal payable Powerful Hand whose exact
  counter count still KOs.
- Select Powerful Hand immediately. No Boss, setup, draw, benching, attachment,
  evolution, Ability, retreat, or second Hammer is permitted inside the
  certified transaction.

`await_resolution`

- Clear only after the expected KO/Prize or terminal resolution is publicly
  observed. On any mismatch, clear the new latch and delegate the current
  observation to an unmodified guarded-parent decision from a clean module
  snapshot. Never reuse cached indices or partially restored globals.

The candidate must remain the final/last callable agent insertion because the
Kaggle loader selects the last inserted callable.

## Required positive, negative, and retention fixtures

- Positive: reconstructed `86987527/S61-S65` must keep the parent's Hammer,
  select Active Mist serial `67` rather than benched Mist serial `65`, suppress
  Boss, and complete Powerful Hand `140` into `130` HP.
- Negative: `86992980/S79-S81` with two Active Mist remains byte-for-byte
  parent-identical.
- Negative: unenergized Alakazam, non-Alakazam Active, nonlethal hand floor,
  no Mist, two or more Mist, another counter blocker, a better terminal Boss
  KO, or a certified safe count-increasing setup route all delegate.
- Option order, duplicate Hammer copies, duplicate non-target Mist, repeated
  callback, stale turn/player, changed Active/HP/Prizes/hand/Stadium, malformed
  Energy-unit mapping, and failed resolution must be explicit tests.
- All existing guarded Teleportation positives/negatives, exact-v3 retreat and
  active-Psychic transactions, successful Boss KOs, setup choices, terminal
  attacks, and ordinary Hammer targets remain unchanged outside this predicate.

## Falsifiable evaluation gates

### Structural and mechanism gate

Require compile/import, exact legal 60 cards with one ACE SPEC, deterministic
valid actions, cache-free tree, final-callable loader emulation, package smoke
in both seats, and zero action errors/max-step hits. Full-engine tests must
complete at least four full `Hammer -> exact Active Mist -> Powerful Hand KO`
transactions spanning both seats and at least two Active HP/Prize states, plus
the two-Mist and stale-state aborts. Shadow all current and historical live
callbacks; every difference must be one certified target or attack stage, and
the reconstructed positive/negative anchors above must match.

### Fixed comparison

Run the exact guarded-parent 144-key schedule with identical seeds and both
seats, retaining exact-v3 on the same keys as a secondary comparator.

Exploratory-package floor:

- candidate at least `89/144`, zero paired regressions, zero faults;
- P0 at least `48/72`, P1 at least `41/72`, known at least `47/72`, fresh at
  least `42/72`;
- Historical-Silver at least `8/16`, Kangaskhan-Crustle at least `10/16`,
  Great Tusk at least `4/16`, Starmie at least `9/16`, with no seat regression;
- no candidate bucket or seat below exact-v3 on the identical keys.

Formal adoption is stricter: at least `91/144`, at least two net paired gains,
zero paired regressions, gains in both seats or two independent seed buckets,
and Historical-Silver at least `9/16` with a mechanism-linked gain and no seat
regression. A tiny single-pair delta is insufficient.

If the fixed panel does not exercise the rule, run a frozen extension against
Kangaskhan-Crustle and Historical-Silver with at least 16 paired seeds per seat
and telemetry for start, target, attack, resolution, and abort reason. Require
at least four completed transactions over at least two seeds and both seats,
targeted net gain at least two with zero regression, and Historical-Silver
non-regression. Without primary-anchor movement the artifact may receive one
root-authorized exploratory live probe after every safety/package gate passes,
but it is **not** adopted as the new baseline. This distinction matches the
user's practical submit-repair preference without pretending that a narrow
Crustle improvement proves broad strength.

## Excluded duplicate/rejected directions

- Boss tempo/sticky-target control was already covered by certified Boss-v2;
  its `4` gains and `4` regressions left the parent tied and the direction was
  deferred. Do not reopen it here.
- Protected-Great-Tusk Kadabra v2/v3 diverted attachment from same-turn
  Hammer/Alakazam KOs and was terminated. This rule never selects Kadabra,
  attachment, retreat, or attacker source.
- Sacred Ash timing, recycle draw-budget, Hilda second-Energy, Xerosic victim,
  broad three-prize setup, and pre-KO setup v2 are rejected or Phase-A failed.
  None may be stacked.

## Evidence registry

- exact-v3 source: `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3/main.py`, SHA-256 `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`.
- guarded source: `candidates/alakazam_guarded_teleportation_attack_continuity_v1/main.py`, SHA-256 `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`.
- submitted CB52 source: `candidates/alakazam_exposed_dudunsparce_run_away_ready_alakazam_ko_transaction_v1/main.py`, SHA-256 `CB52F1737417EAEEAEF226CFF79ABD4FA58119E3F2AF1D448DFBE5D68722E213`.
- guarded final judgment: `judgments/alakazam_guarded_teleportation_attack_continuity_v1_20260719/FINAL_STRATEGY_JUDGMENT.md`, SHA-256 `9E8A062035FB2C991483A6D3126A5B7D1E2AF6957158F49165ACDF7DEC27AFB7`.
- guarded numerical audit: `evaluations/alakazam_guarded_teleportation_attack_continuity_v1/fixed_phase0_20260719/numerical_audit/AUDIT_REPORT.md`, SHA-256 `3E9676DC8C78E26AB691232428D19BCEB96A6B2C0600187E4037340424F01A21`.
- guarded 42-game live census: `analysis/live_54824578_current42_1855_20260719/ROOT_POLICY_CENSUS_V4_VERIFICATION.md`, SHA-256 `FD0C72A8F4ABBD1CEA5237F4DC79FD2F015F4A8110EE6A84578183460AD785C2`.
- current root evidence packet: `strategy/next_rule_after_54841997_20260720/ROOT_VERIFIED_EVIDENCE.md`, SHA-256 `A8FB971BBE3869D8A68465264E2F153DE6308C1C7091DA76AA007D1A81B1C707`.
- positive replay audit: `live/54841997/analysis_public_losses_86987527_86988084_sol_ultra_20260720/REPORT.md`, SHA-256 `F9D4B407667461EC2B0EA0B4112C0C6628FA8BEE48E243729D4FAE2278BDBA7E`.
- two-Mist negative audit: `live/54841997/analysis_public_losses_86992980_86993519_sol_ultra_20260720/REPORT.md`, SHA-256 `89F080FA53CC0C0024E49F770E5F106173CC75B69760EC1FB91877565DAEB871`.
- older Mist-wall diagnosis: `analysis/live_54802782_public13_increment_20260718/episode_86660075/QUALITATIVE_DIAGNOSIS.md`, SHA-256 `5C190D9639FA5D1DF521A941CE46530CE1CE751799E0CE545F48418E8CADFC0B`.
- Boss-v2 contract: `strategy/certified_boss_public_utility_transaction_v2_20260718/STRATEGY_SELECTION.md`, SHA-256 `5B35CB636F08AA7FF44F9153ABC40499ADAAA45EC204E42297C351D1146F19F7`.
- protected-Tusk-v3 rejection: `decisions/20260717_0051_alakazam_attachment_aware_protected_tusk_kadabra_v3_reject.md`, SHA-256 `D03DAB50A92102649381CDE5F953A463F52344D436A266F74C547D5A70E35CCD`.
- pre-KO-v2 rejection: `judgments/alakazam_certified_three_prize_pre_ko_setup_transaction_v2_20260720/FINAL_STRATEGY_JUDGMENT.md`, SHA-256 `BACC6B89E36AE236ADA94868AA7372FF5512051275117B1824FD3D54A23A9F65`.
- latest root live/quota verification: `live/54841997/refresh_20260720_1747/ROOT_VERIFICATION.md`, SHA-256 `12D2F5A7DE6310A3001D2810AA4E1A001B56CC1A59756B684D8400EEC9952D41`.

## Uncertainty and next discriminating evidence

The exact tactical correction is high confidence; a full-game improvement is
medium confidence, and live frequency is unknown. The next discriminating
evidence is therefore not another prose replay diagnosis: it is (1) exact
positive/negative shadow behavior, (2) repeated full-engine completion in both
seats, and (3) a paired Kangaskhan-Crustle extension showing at least two net
gains without regression while Historical-Silver remains safe. Failure of any
one of those gates rejects the candidate rather than broadening the predicate.

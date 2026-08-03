# Strategy judgment: Prize-lane v1 NO-SELECT; Run Away Draw hit-bound v1 SELECT

- Judgment time: `2026-07-17T02:24:50+09:00`
- Judge: `/root/ptcg_sol_ultra_worker` (`gpt-5.6-sol`, Ultra)
- Parent: exact public Best-5 Alakazam
- Parent source SHA-256:
  `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4`
- Parent runtime SHA-256:
  `D37DBBE7933F939266D1D1DEEFEEC666CF908A910F56539AFF37936E30CBCBA9`
- Parent deck SHA-256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

## Final Prize-lane judgment

**NO-SELECT** `alakazam_sustained_attack_prize_lane_audit_v1`.

The arithmetic is reproducible, but only one unique loss schedule has a
Prize-completing Boss line before the first opponent choice. The remaining
positive rows cross an uncertified opponent choice or hidden continuation.
Only five independent matched controls and nine matched opportunity states
qualify, below the immutable floor of twelve. Sequence-level H1 safety is
also unproved because 25 of 26 earliest loss events precede parent setup
actions. Do not implement, relax, or reinterpret this rule.

## Selected next hypothesis

**SELECT** exactly one isolated candidate:
`alakazam_run_away_draw_hit_bound_v1`.

No additional behavior-neutral diagnostic is required before implementation.
The frozen traces already show one public-state mechanism in 18 unique loss
schedules and 15 unique win schedules, across both blocks, both seats, and
seven policies. The engine's current legal options, rather than replayed
opponent actions, certify that a second Dudunsparce remains independently
usable after the first. The fresh-p0 loss slice has only three schedules, so
this is hypothesis selection rather than promotion; fresh paired retention
remains mandatory.

## Exact behavior predicate and ordering

Compute the exact parent score vector first. The new branch may run only when
all of the following are true at the current observation:

1. context is MAIN and the exact parent top-ranked action is Powerful Hand
   (`ATTACK 1072`, parent score `1500`);
2. own Active is Alakazam `743`, has Psychic Energy `5` or `19`, and Powerful
   Hand is currently legal;
3. at least one engine-offered legal Dudunsparce `66` ABILITY source is on the
   Bench; Active or non-offered copies never qualify;
4. the opposing Active has positive remaining HP and Powerful Hand is not
   blocked by Mist Energy, nor by Rock Fighting Energy when its printed
   Fighting-Pokemon condition applies;
5. the exact parent conservative `safe_draws` value is at least `3`;
6. with current hand size `h` and opposing Active remaining HP `r`,
   `ceil(r / (20*h)) > ceil(r / (20*(h+3)))`; zero damage is infinity;
7. shuffling the Bench source cannot remove the own Active or cause board-out.

When the predicate holds, rank exactly one qualifying legal Run Away Draw at
score **1550**. This is strictly above Powerful Hand `1500` and strictly below
the lowest valid parent Retreat `2000`, Supporter `3000+`, Boss `3200`,
attachment/evolution, and other preparatory priorities. If several legal
copies qualify, choose the fewest attached cards, then lowest Bench index;
recompute after resolution so a second copy is used only if its own additional
three cards again reduce the current hit bound.

The existing exact-KO Run Away Draw branch and its score `30000` remain
unchanged. Do not simply delete the global Dudunsparce flag. Ignore that flag
only for engine-offered legal Bench Dudunsparce options inside the ready-Active
Alakazam predicate above. Parent estimates and every non-Dudunsparce option
score remain frozen until the parent winner is known to be Powerful Hand.

## Phase 0: immutable trigger-trace gate

Before candidate execution, materialize and hash a `PHASE0_KEYS.csv` from the
frozen 720-trace digest. It contains all and only the 33 unique schedules in
the root-verified opportunity population: 18 losses and 15 wins. Run parent
and candidate once each on the identical opponent, seat, and seed with engine
seeding, `--trace-options`, and `max_steps=1000`: 33 paired keys, 66 one-game
commands, 66 valid summaries, and 66 nonempty traces.

All gates are conjunctive:

- compile/import, legal byte-identical 60-card deck, exact schedule equality,
  zero action errors, and zero max-step hits;
- every changed first action is qualifying Bench Dudunsparce ABILITY versus
  parent Powerful Hand; there is no earlier setup, Boss, target, attachment,
  evolution, Supporter, Retreat, or END divergence;
- at least 12 of the 18 loss-derived keys exhibit the certified branch,
  spanning both blocks, both seats, at least three opponents, and at least
  eight distinct `(block, seat, seed)` groups;
- every exhibited branch draws exactly three before the same-turn attack and
  strictly reduces the recomputed public current-target hit bound;
- the eight post-one-use loss keys must not be suppressed by the global lock
  when their state remains reachable; any unreachable key must be explained
  by an earlier predicate-valid Run Away Draw in that same trace;
- all 15 win-control keys remain wins; every parent same-turn KO, attack, and
  H1-ready attacker is preserved;
- at least four loss-derived keys convert the bound into an observed earlier
  target KO, additional Prize, additional attack before terminal, or win;
- the attached-Enriching source case receives explicit resource/continuity
  review; and
- every first divergence and every result discordance receives qualitative
  trace review before broad retention.

Thus no pre-implementation replay audit is required, but post-implementation
Phase-0 qualitative audit is mandatory. Any gate failure rejects v1 without
adding an exception.

## Broad retention: immutable paired schedules

Run only after Phase 0 passes, against the same frozen nine opponents in both
Alakazam seats.

1. **Reference:** the exact general-audit schedule, 20 games per cell on
   `known 2026071581..2026071600` and
   `fresh 2026081701..2026081720`: 720 paired keys. Parent must reproduce
   `406/720`, known `210/360`, fresh `196/360`, p0 `210/360`, p1 `196/360`,
   and Historical-Silver `29/80`.
2. **New fresh:** 40 games per opponent/seat on previously unused seeds
   `2026091701..2026091740`: 720 paired keys. Root must verify zero prior use
   before freezing the execution manifest; a collision invalidates execution
   rather than permitting a silent replacement range.

Retention gates are conjunctive:

- exact schedules and frozen hashes; zero errors, invalid rows, max-step hits,
  duplicate mismatches, or runner discrepancies;
- reference candidate at least `410/720` (`+4`), with nonnegative delta in
  each old block and each seat;
- new-fresh total delta at least `+4/720`, with both seats nonnegative;
- combined delta at least `+8/1440`, paired gains greater than regressions,
  and exact one-sided discordant sign-test `p <= 0.10`;
- Historical-Silver is nonnegative in each schedule and every one of the nine
  opponents is nonnegative after the two schedules are combined;
- all 15 frozen win-opportunity controls remain wins;
- every changed first action obeys the exact predicate, all regressions and a
  deterministic sample of gains are traced, and no parent immediate KO or
  ready H1 attacker is lost.

Only a later independent numerical audit, root recomputation, qualitative
discordance audit, and final Sol-Ultra adoption judgment can retain the
candidate. This selection authorizes neither package nor Kaggle write.

## Prohibited spillover

- No deck, target-selection, Boss, Fezandipiti, Kadabra, protection, mill-clock,
  setup, promotion, retreat, attachment, or Supporter rule change.
- No Active Dudunsparce use and no Run Away Draw outside a ready Active
  Alakazam with legal Powerful Hand.
- No draw when the hit bound is unchanged, the target effect is blocked,
  `safe_draws < 3`, or board-out is possible.
- No global removal of once-per-turn bookkeeping and no option inferred legal
  from card presence when the engine does not offer it.
- No combination with the rejected Prize-lane, Zone, Acerola,
  Active-MD/Ultra-Ball, visible-mill, protected-Tusk Kadabra, H0-miss,
  promotion, board-out, or retreat-END fragments.
- No learned component, hidden-state assumption, replay action label, or
  opponent-policy proxy.

# Strategy selection: Alakazam Run Away Draw cost certificate v2

- Selection time: `2026-07-17T03:23:11+09:00`
- Judge: `/root/ptcg_sol_ultra_worker_run_away_final`
  (`gpt-5.6-sol`, Ultra)
- Exact parent: public Best-5 Alakazam
- Selected successor: `alakazam_run_away_draw_cost_certificate_v2`
- Decision: **SELECT exactly one isolated, stateless rule hypothesis**
- Package/Kaggle authorization: **none**

## Decision among the proposed routes

The stateful atomic two-action commitment is **not selected**. The frozen
v1 branch reduces the theoretical `h -> h+3` bound in all 33 traces, but only
30 retain that reduction at the realized attack hand. Those three misses are
all cases that remain losses; there is no observed conversion showing that
forcing an immediate attack would win them. Conversely, current continuations
legally use setup, additional draw, attachment, and in one retained control a
newly drawn Boss before attacking. A pending-action state would therefore
change many routes beyond the three misses and can preempt engine formation,
targeting, and retained wins. The evidence does not certify that risk.

The literal card-specific proposal—require immediate KO for an attached
source or Crustle `345`—would exclude the two regressions and the attached
Enriching `L -> L`, leaving 17 case and 13 control branch keys. It is safer
than v1, but the Crustle-ID exception is narrower than the public game concept
supported by the evidence.

The selected v2 uses the more general single cost/benefit certificate:

> A non-immediate Run Away Draw hit-bound reduction is allowed only when the
> chosen Dudunsparce is unattached and the current target is publicly worth
> at least two Prizes. If the source carries any Energy or Tool, or the target
> is worth at most one Prize, `h+3` must already make Powerful Hand an
> immediate KO.

This uses only public board state, the existing public prize-value function,
and exact integer damage. It neither identifies an opponent nor learns an
action from a replay. It subsumes the Crustle regression because that visible
Crustle is a one-Prize target, while also declining two other unsupported
non-immediate one-Prize/resource-cost branches. It preserves all six observed
v1 gains: the one-Prize Alakazam and Great Tusk gains are immediate KOs after
three cards; the remaining Kangaskhan and Starmie gains use clean sources
against multi-Prize targets.

## Exact parent, destination, and isolation

Authoritative parent artifacts remain:

| Artifact | SHA-256 |
| --- | --- |
| parent source | `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4` |
| parent runtime | `D37DBBE7933F939266D1D1DEEFEEC666CF908A910F56539AFF37936E30CBCBA9` |
| parent/deployment deck | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| rejected v1 source | `E3A035D61A144E37F3986F534EF25CA885746A3D4ACBE5BFE636CA7B7C515FAC` |
| frozen v1 Phase-0 keys | `A6934CE3318DD0F7551464A273900371B2BBD250E796E1F04DFBA2AF1D7CA094` |

Create source only under:

`autonomous_gold_20260715/candidates/alakazam_run_away_draw_cost_certificate_v2`

The exact Best-5 parent is the comparison baseline. The v1 source may be used
only as a mechanical read-only input; the final parent-to-v2 diff must contain
the already-audited v1 helpers/overlay plus this one cost-certificate guard.
The deck must remain byte-identical. No other source or repository artifact
may be edited.

## Frozen public predicate and ordering

First compute the exact parent scores and stable parent winner. Retain every
v1 guard and ordering rule unchanged:

1. context is MAIN and exact parent winner is legal Powerful Hand `1072` at
   parent score `1500`;
2. own Active is Alakazam `743`, has Psychic Energy `5` or `19`, and remains
   the legal attacker;
3. target is the current opposing Active, has positive remaining HP, and is
   not blocked by Mist `11` or conditional Rock Fighting `20`;
4. exact parent `safe_draws >= 3`;
5. an engine-offered legal Bench Dudunsparce `66` exists;
6. `ceil(r/(20h)) > ceil(r/(20(h+3)))`.

Choose the legal Bench Dudunsparce exactly as v1: fewest total attached
Energy plus Tools, then lowest Bench index. From that chosen public source,
compute:

```text
post_draw_hits = ceil(r / (20 * (h + 3)))
source_has_attachment = (len(energyCards) + len(tools)) > 0
target_prizes = prize_count(op_active)
cost_requires_immediate_ko = source_has_attachment or target_prizes <= 1
certificate = (not cost_requires_immediate_ko) or post_draw_hits == 1
```

Only when `certificate` is true may that one legal ability receive score
`1550`. Stable ordering, all original scores, and the existing exact-KO
Run Away Draw score `30000` remain unchanged. Recompute on every subsequent
observation; do not reserve a source or infer a future option.

There are **no new state variables and no reset behavior**. In particular,
do not create a pending attack, force the next MAIN action, suppress a drawn
setup card, or modify the parent's per-turn global booleans. After Run Away
Draw, the exact parent scorer chooses the continuation from the new public
observation.

Helper scope is limited to the existing integer hit-bound helper, the legal
Bench Dudunsparce resolver, and a small pure/public certificate calculation.
Use the existing `prize_count` result rather than opponent identity or a new
matchup table.

## Exact frozen Phase-0 population

Before source creation, materialize and hash a v2 key ledger that contains
the exact same 33 schedules as v1 `PHASE0_KEYS.csv`: 18 parent-loss cases and
15 parent-win controls. Compare the exact parent and v2 once each on the same
opponent, Alakazam seat, and seed, with engine seeding, `--trace-options`, and
`max_steps=1000`: 33 pairs and 66 one-game commands.

The public certificate classifies exactly these five original first branches
as ineligible; each had exactly one parent opportunity event:

| Population | Block/opponent/seat/seed | Public reason |
| --- | --- | --- |
| case | known/great_tusk/p0/`2026071589` | one-Prize target, post-draw bound `2` |
| case | known/starmie/p0/`2026071591` | source has Enriching `13`, post-draw bound `4` |
| control | fresh/kangaskhan_crustle/p0/`2026081712` | one-Prize target, post-draw bound `2` |
| control | fresh/starmie/p1/`2026081708` | one-Prize target, post-draw bound `3` |
| control | known/starmie/p1/`2026071590` | source has Lucky Helmet `1156`, post-draw bound `2` |

All and only the other 28 original first branches are eligible: 16 cases and
12 controls. This is a rule-derived audit expectation, not permission to
check seed, block, opponent name, or target ID in source.

## Conjunctive Phase-0 gates

All gates must pass:

1. compile/import, legal byte-identical 60-card deck, deterministic action,
   both-seat packaged-runtime smoke, exact 33 paired keys, 66 zero exits, zero
   action errors, zero max-step hits, and no invalid/duplicate output;
2. for all 28 eligible keys, the first candidate-parent divergence is exactly
   legal Bench Dudunsparce versus parent Powerful Hand at the same public
   state, and the v2 trajectory/action sequence matches the frozen v1 trace;
3. for the five ineligible keys, v2 selects the parent Powerful Hand at the
   frozen opportunity, never overlays that state, and the full parsed action
   trajectory and result match the parent; any later divergence is a hard
   failure because each parent key has only that one opportunity event;
4. every exhibited branch draws exactly three, attacks in the same turn, and
   satisfies both the v1 strict-bound predicate and the new certificate;
5. branch coverage is exactly 16/18 cases and 12/15 controls, spanning both
   blocks, both seats, at least three opponents, and at least eight distinct
   `(block, seat, seed)` groups;
6. all 15 control keys remain wins; no parent win, immediate KO, ready H1
   attacker, attachment, target, or pre-branch setup action is lost;
7. all six frozen v1 case gains remain wins: fresh OSEL p1 `2026081705`,
   fresh Kangaskhan/Crustle p0 `2026081720`, fresh Starmie p0
   `2026081707` and `2026081708`, fresh Starmie p1 `2026081702`, and known
   Great Tusk p1 `2026071584`; expected targeted result is at least 6/18 case
   wins, 15/15 control wins, zero regressions, and at least `+6/33` paired;
8. independently inspect every first divergence, the five suppressed states,
   every result discordance, every attached-source branch, and the three v1
   realized-bound-decay states. Do not claim an atomic route from the
   theoretical `h+3` certificate.

Any failure rejects v2 without an exception, post-hoc guard, Phase 1, or
package.

## Broad retention after Phase 0 only

If and only if Phase 0 passes, use the v1 immutable retention design against
the same nine-opponent anti-overfitting population in both seats:

1. reference 720 keys on known `2026071581..2026071600` and fresh
   `2026081701..2026081720`, with parent reproduction `406/720`, known
   `210/360`, fresh `196/360`, p0 `210/360`, p1 `196/360`, and
   Historical-Silver `29/80`;
2. new-fresh 720 keys on unused seeds `2026091701..2026091740`, after root
   proves no collision.

Retention remains conjunctive: reference delta at least `+4/720` with each
old block and seat nonnegative; new-fresh delta at least `+4/720` with both
seats nonnegative; combined delta at least `+8/1440`; gains exceed
regressions; exact one-sided discordant sign-test `p <= 0.10`;
Historical-Silver nonnegative in each schedule; all nine opponents
nonnegative after schedules combine; all 15 frozen controls remain wins;
zero execution faults; and every regression plus a deterministic gain sample
receives trace review. Numerical evaluation, root recomputation, and a new
final Sol-Ultra adoption judgment are mandatory.

## Prohibited spillover

- No atomic draw-then-attack commitment and no new stateful route.
- No opponent, seed, block, replay-hash, Crustle-ID, or archetype condition.
- No deck, target, Boss, setup, evolution, attachment, Supporter, Retreat,
  Fezandipiti, Kadabra, mill-clock, protection, or promotion change.
- No global deletion of Dudunsparce bookkeeping, Active Dudunsparce use, or
  inferred legal option.
- No learned component, replay action label, hidden-state assumption, or
  opponent-policy proxy.
- No package, Phase 1, or Kaggle write before every frozen gate passes.


# Historical-Silver vs cumulative Task 6 / Task 9

Root comparison completed on 2026-08-03 JST. No candidate source, deck, or
Kaggle state was changed by this audit.

## Verdict

Task 6 and Task 9 are both materially weaker than exact Historical-Silver on
the frozen same-seed, both-seat schedule. Task 7-9 change which games are won,
but produce zero net improvement over Task 6.

The primary regression is not deck construction. All three policies use the
same exact 60 cards. It is a turn-order/arbitration error: the cumulative
policy can replace Historical-Silver's setup, attachment, evolution, recovery,
or draw action with an immediate nonterminal attack when it cannot certify the
prefix action's value. In particular, `SECURED_ATTACK_NOW` treats incomplete
knowledge of a prefix as permission to attack rather than as a reason to keep
the parent action.

Task 8 adds useful local materialization before Lillie, but can also END or
attack while deterministic setup remains. Task 7 and Task 9 add useful exact
Boss/prize conversions, but they do not repair the inherited attack-now
regression.

## Frozen policies

All decks have SHA-256
`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

| Policy | `main.py` SHA-256 | Lines | Bytes |
| --- | --- | ---: | ---: |
| Historical-Silver | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` | 1,337 | 53,448 |
| Task 6 cumulative | `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756` | 33,404 | 1,207,886 |
| Task 9 cumulative | `0A9F0052095257B08CC5C5ABACAA0E912D7E02A9842145B48E2192A6F50ED4AE` | 37,788 | 1,374,663 |

The original Historical-Silver scoring functions remain structurally intact
inside the cumulative policy. The regression is introduced by outer wrappers
that can replace the parent result after it has been scored. The inner
cumulative rank order does not protect Silver from these outer overrides.

## Fixed 760-game comparison

The immutable specification SHA-256 is
`8C7F2C3BD994966EE7E004B35C698E3E006E7416E9BC801C5ECDFA23ED3E970E`.
Each policy used the exact same 760 `(panel, opponent, seat, seed)` keys.
Duplicate controls, report validity, action errors, and max-step checks all
passed. Root reconstructed every win from the engine result and policy seat.

| Comparison | Silver wins | Candidate wins | Delta | Paired gains | Paired regressions | Ties |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Silver vs Task 6 | 478 | 368 | -110 | 37 | 147 | 576 |
| Silver vs Task 9 | 478 | 368 | -110 | 44 | 154 | 562 |

The paired effect is `-14.47` percentage points for both cumulative agents.
The independent Sol-Ultra seed-cluster 95% interval is `[-17.11, -11.71]`
points for Task 6 and `[-17.24, -11.84]` points for Task 9. Exact two-sided
discordant-pair tests are `1.02e-16` and `1.67e-15` respectively.

Direct Task 6 vs Task 9 comparison on the same keys:

- Task 6 wins: 368;
- Task 9 wins: 368;
- Task 9 gains: 42;
- Task 9 regressions: 42;
- ties: 676;
- exact discordant-pair test: `p=1.0`.

Task 9 is therefore a redistribution of wins, not an aggregate-strength
repair. It improves seat 0 by five wins and worsens seat 1 by five wins.

### By opponent

| Opponent | Games | Silver | Task 6 | Task 9 | Task 6 delta | Task 9 delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical-Silver mirror | 200 | 100 | 36 | 39 | -64 | -61 |
| `arch_peak` | 80 | 39 | 13 | 11 | -26 | -28 |
| `arch_shumpei` | 80 | 40 | 27 | 31 | -13 | -9 |
| `alakazam_capbloo_gold` | 80 | 62 | 61 | 59 | -1 | -3 |
| `marnie_kazuki_live` | 80 | 68 | 64 | 68 | -4 | 0 |
| `mega_lucario_public` | 80 | 74 | 72 | 72 | -2 | -2 |
| `kang_crustle` | 80 | 28 | 30 | 27 | +2 | -1 |
| `cynthia_v23` | 80 | 67 | 65 | 61 | -2 | -6 |

The severe floor is concentrated in Archaludon matchups, where low-value chip
attacks lose the setup, energy, evolution, and successor race. Task 9 repairs
Marnie and part of `arch_shumpei`, while worsening `arch_peak`, Alakazam,
Kangaskhan/Crustle, and Cynthia. It does not establish a stable replacement.

## Exact controlled example

At historical-mirror seed `271828182`, seat 0, all three policies reach the
same public state at step 25:

- active Duraludon: 30/130 HP, one Metal;
- bench Duraludon: 130/130 HP, zero Energy;
- hand includes Metal, two Archaludon ex, non-ex Archaludon, Night Stretcher,
  and two Lillie;
- opponent active Cinderace: 130 HP;
- both manual Metal attachment and Hammer In are legal.

Historical-Silver chooses the active Metal attachment, scored `12000`, and
wins in 136 steps. Task 6 and Task 9 both override it with Hammer In for 30
damage, whose inherited Silver score is only `30`; both lose. This proves the
failure is an outer arbitration decision, not a disagreement inside the
original scorer. Task 7-9 leave this exact regression unchanged.

Trace SHA-256 values:

- Silver win: `1DE3C22C430E91F6AD27CF0D239235029C997BC4222A6F7D5109C3D476986414`;
- Task 6 loss: `5CC1678E62B9CA8A576CC3BBCD9B32DA636AB37A0F5C8A1EEEB02560AF0D3971`;
- Task 9 loss: `DF6B18A1297CD7A89DC2277CEA9AF1F6E56CC9F8A04A83893D2EED02A13D4B17`.

## Replay first-difference audit

The frozen corpus contains 77 readable replays and one malformed file. There
were zero invalid actions.

### Historical-Silver to Task 6

There were 52 first differences:

- clearly beneficial: 37;
- clearly harmful: 7;
- neutral/equivalent: 2;
- uncertain: 6.

The clearly useful groups were all 18 initial one-Duraludon setup choices,
most declared-complete Ultra Ball routes, exact terminal attacks, exact Boss
prize upgrades, and useful Turbo allocation choices.

All seven clear harms came from `SECURED_ATTACK_NOW`. Five more firings were
uncertain. These firings replaced Explorer, a live Night Stretcher, Hero's
Cape, Lillie, evolution, or attachment with an immediate attack. Ten of the
twelve rejection reasons were `card_or_target_binding_unknown`; the remaining
two were `not_supported_energy_or_bench_evolution`. The rule did not prove the
prefix was bad. It failed to model the prefix, then attacked.

The apparently favorable 37-to-7 first-difference count does not contradict
the fixed simulation. Eighteen replays diverge during setup, after which later
Task 6 actions are counterfactual and cannot be inspected from that replay.
First-difference evidence is a local safety audit, not a complete-trajectory
win estimate.

### Task 6 to Task 9

There were 40 first differences:

- clearly repairing: 23;
- clearly harmful: 10;
- neutral/equivalent: 5;
- uncertain: 2.

Task 8 supplied 15 useful materializations before Lillie: six Basic plays,
four evolutions, one manual attachment, and four Full Metal Lab plays. Task 7
and Task 9 supplied exact terminal/Boss prize conversions.

All six Task 8 `PLAY -> END` changes were harmful. Additional harms included
Lillie shuffling immediately usable recovery, Turbo Flare with an empty bench,
Hammer In while two evolutions were legal, and Gear-to-Lillie preempting an
exact Ultra Ball -> Archaludon ex -> Assemble Alloy route.

On those same 40 public states, Task 6 exactly matched Historical-Silver in 37
rows. Task 9 returned exactly to Silver in only one row. Task 7-9 therefore
mostly add new outer decisions rather than repair the earlier regression.

## What should be retained and what should be replaced

Retain as isolated hypotheses, re-based directly on Historical-Silver:

- exactly one Duraludon during setup;
- declared-complete Ultra Ball resource protection;
- exact terminal attack and exact Boss/prize conversion;
- useful Task 8 pre-Lillie materialization;
- exact Turbo Energy concentration and exact same-active attack dominance,
  after their own paired checks.

Do not carry forward unchanged:

- `SECURED_ATTACK_NOW` with unknown-prefix fail-open behavior;
- broad role-empty Duraludon suppression without successor/board-depth proof;
- Task 8 `HOLD_LILLIE` paths that can END while a deterministic non-Supporter
  materialization remains;
- the current stack of independent outer wrappers as the final arbiter.

The safe redesign is to use exact Historical-Silver as the executable parent
and have every new rule return a proposal plus a proof. One final resolver
should apply hard order:

1. exact terminal win;
2. deterministic setup/recovery/attachment/evolution that preserves the same
   attack;
3. exact prize upgrade or exact threat removal;
4. parent Historical-Silver action when the proposal is unknown or
   incomparable;
5. nonterminal attack only after useful deterministic prefixes are exhausted.

This preserves the good rules without allowing one incomplete proof to erase
the deck's setup and attack-continuity plan.

## Primary artifacts

- `IMMUTABLE_COMPARISON_SPEC.md`
- `ROOT_RECOMPUTE_FIXED760.json`, SHA-256
  `78D8C2E3A948EFCC3C047E8DCE064B9D89CF728307AA3D034027867B265B4C15`
- `replay_first_differences_classified.json`, SHA-256
  `99253897ECAB5764D2D5A6331692C745CBE34A180D1246F6528BE1E1EF070060`
- `TASK6_VS_TASK9_DISCORDANT_KEYS.csv`, SHA-256
  `6334CC55868DAF31E426BEC0424212CD6C8A7C81AF2B18A8FAB3987094F13B3F`
- `SOL_ULTRA_NUMERICAL_AUDIT.md`, SHA-256
  `5B5E16726DD71E3DED2967DEFD35DE6DAE231868DF0BD4B4C07C2263DFF0C088`

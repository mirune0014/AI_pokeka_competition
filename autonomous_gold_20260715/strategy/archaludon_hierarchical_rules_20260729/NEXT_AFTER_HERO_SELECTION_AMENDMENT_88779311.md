# Selection amendment — new last-Bench survival source

This amendment adds genuinely new Root-verified evidence after the original
selection specification. It does not alter H6/Hero ordering and does not
authorize implementation, packaging, or a Kaggle write.

## Prior decision

Original specification:
`NEXT_AFTER_HERO_SELECTION_SPEC.md`

SHA-256:
`E1327C1D131CFD222FA789F63F6DCEF8D742F18A3262EC5DBC6CAC8BD29827C1`

The prior Sol-Ultra decision was `NO_SAFE_SELECTION`:

- `88247531:115` failed because redirecting Archaludon ex to the Bench could
  sacrifice the parent's deterministic two-attack Prize conversion;
- `88776108:44` failed because the opposing completion was not public.

Those rejections remain controlling for those two sources.

## New independent source

Root memo:
`DEFERRED_LOSS_MEMO_88779311_LAST_BENCH_EVOLUTION.md`

Memo SHA-256:
`F4CB09C69E1B601470DAE9E943632E1A5DFC6462A086E8C46766BD59FABB95DE`

Replay:
`autonomous_gold_20260715/live/55077607/refresh_20260729_1855/episode_88779311_replay.json`

Replay SHA-256:
`846F9BEA46F3B08A9109863152D88D207488D881436A6F80E76D8B1EF537C2D5`

H6 was parent-identical on all 56 correct-seat callbacks. This is not an H6
repair.

At row 140, seat 0:

- our Active was Archaludon ex `190#7`, 140/300, with three Metal;
- our only Bench Pokémon was Hero's-Cape Duraludon `169#6`, 10/230, with
  three Metal;
- hand contained non-ex Archaludon `840#32`;
- the opposing Active was Munkidori `112#76`, 100/110 with Darkness Energy;
- the parent had already played Boss to that exact Munkidori;
- legal options were evolve the last Bench, Metal Defender `253`, Retreat,
  or End;
- parent scored evolution `-1,000` and Metal Defender `220`, then attacked;
- the attack KOd Munkidori and took one Prize.

The following opposing turn used only publicly visible/reachable components:

- Night Stretcher was in the opponent's hand;
- Basic Darkness existed in public discard;
- a second Bench Munkidori was public;
- Night Stretcher recovered Darkness and attached it to that Munkidori;
- Adrena-Brain moved 30 damage to our 10-HP last Bench Duraludon and KOd it;
- the still-payable Shadow Bullet KOd our Active and produced board-out.

Exact evolution arithmetic:

- Duraludon carried 220 retained damage;
- non-ex Archaludon base maximum HP is 180;
- retained Hero's Cape produces maximum HP 280;
- projected current HP is `280 - 220 = 60`;
- the certified counter movement is 30;
- projected remaining HP is 30.

Unlike `88247531`, the changed action need not redirect the same Archaludon-ex
resource away from the Active or sacrifice the current attack. It uses a
separate non-ex Archaludon on the only Bench before the same stored parent
Metal Defender.

## Reconsideration question

Judge exactly one hypothesis:

`LAST_BENCH_PUBLIC_BOARD_OUT_EVOLUTION_BEFORE_STORED_ATTACK`

Potential action sequence:

`non-ex Archaludon -> only Bench Duraludon -> confirm retained HP/Tool/Energy -> exact stored parent Metal Defender`.

The trigger must require:

1. exact ordinary Main callback and one untied parent Attack;
2. the parent Attack is deterministic and nonterminal;
3. exactly one Bench Pokémon remains;
4. exactly one legal evolution option binds that Bench lineage;
5. retained-damage arithmetic is exact before and after evolution;
6. a full public, currently reachable opposing event sequence KOs the Bench
   before our next turn without evolution but not after evolution;
7. the same public sequence also KOs our current Active, so failure to evolve
   certifies board-out while evolution preserves at least one body;
8. evolution does not change current attacker, target, attack ID, payment,
   damage, or Prize yield;
9. no exact same-turn match win, higher-Prize route, forced defense, or setup
   transaction has precedence;
10. every recovery, attachment, Ability, attack, modifier, and damage formula
    is supported and public; ambiguity fails closed.

If the source is not sufficient, return `NO_SAFE_SELECTION` with the exact
missing public certificate. If sufficient, return an experiment-only bounded
contract with one evolution action plus stored-attack completion, retries,
snapshot/rollback, mandatory positive/negative branches, telemetry, fixed
floors, and explicit package/live authorization status.

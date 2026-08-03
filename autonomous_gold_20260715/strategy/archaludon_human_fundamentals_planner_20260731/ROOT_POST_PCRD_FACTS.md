# Root facts after PUBLIC_COMBAT_RETURN_DOMINANCE_V1

This file records code and execution facts only. It does not select the next
rule and does not authorize a package or submission.

## What the current child fixes

The child implements a shared public combat/effect oracle for our attack and
the opponent's return. It explicitly handles:

- Weakness, Resistance, Full Metal Lab order, Hero's Cape HP, and Jumbo Ice
  Cream healing;
- Hammer In, Raging Hammer, Metal Defender, Coated Attack, Turbo Flare, and
  Powerful Hand's current attack-time hand count;
- Sturdy, amended Run Away Draw, Prize value, post-KO promotion, payable
  retreat including printed cost zero, and one-attachment threat tiers;
- ex, non-ex, and no-evolution combat plans without the parent's unconditional
  non-ex score penalty;
- hard exact win, exact loss avoidance, and exact public Pareto comparison;
- board-wide public Ability, Tool, Energy, Stadium, status, and HP-invariant
  inventory, with unsupported relevant effects returning to V2.

The candidate is the exact 668,927-byte V2 prefix plus one final callable
layer. Its final source SHA is
`DCF7A4AB477CEA3743E7053DCABD0B1FBFDA20B13E84D256995A3557209400F1`.

## What remains in the inherited score fallback

The preserved Historical-Silver-derived policy still contains coarse
single-action scores. Examples in the frozen V2 source include:

- generic playable Pokémon `18000`;
- generic playable item `20000`;
- Ultra Ball skip `-1000`;
- Lillie generic play `5000`;
- non-ex Archaludon outside one matchup `-1000`;
- generic evolution `10000`;
- Hero's Cape on ex `11000`, Duraludon `8000`, otherwise `-1000`;
- generic card-selection and target fallbacks `1000`;
- opponent-name-specific Ice Cream HP thresholds.

These values remain reachable whenever no later certified rule owns the
callback. Therefore the current child is not a complete replacement for
human card-use sequencing, resource conservation, or Prize planning.

## Verified execution state before fixed760

- candidate-specific fixtures: `17/17`
- inherited V2 fixtures: `16/16`
- targeted engine transactions: `2/2` completed across both seats
- duplicate retries: `2/2`
- invalid action / exception / stale transaction: `0/0/0`
- eight-game instrumentation:
  46 MAIN attack callbacks, 42 comparable, natural overrides `0`
- fixed safety16:
  V2 `8/16`, candidate `8/16`, gains `0`, regressions `0`,
  all opponent×seat buckets equal, all 48 commands exit zero

Safety16 proves non-regression only. Zero natural override is a frequency
warning, not an implementation success.

## Remaining player-fundamentals groups

The TODO still requires broad, effect-aware conditions for:

1. mulligan and going-first/second setup;
2. whole-turn sequencing before attack;
3. Pokégear, Explorer, Lillie, Night Stretcher, and Boss purposes;
4. manual Energy and Turbo Flare/Alloy allocation without overattachment;
5. exact Prize race, harmful-KO avoidance, Bench-threat conversion, and
   comeback lines;
6. deterministic telemetry that identifies whether the final choice came from
   the inherited policy, a hard rule, or a multi-callback transaction.

The next strategy decision must use the fixed760 activation/result evidence.
If the present rule is too sparse, adding more games is not the repair. The
repair must broaden explicit card/effect coverage or replace all-field Pareto
silence with an ordered hard-condition hierarchy while retaining exact
legality and public-state semantics.

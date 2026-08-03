# Controlling H3 amendment — legal Explorer's Guidance veto

This amendment supersedes H3 v1's arm behavior only when Explorer's Guidance
is currently a legal public play. Every other condition in
`STRATEGY_SELECTION_H3.md` and
`STRATEGY_SELECTION_H3_AMENDMENT_BOSS_SAFETY.md` remains controlling.

## Exact rule

At an otherwise H3-eligible ordinary `MAIN` callback, before creating any H3
transaction:

1. Inspect only the current engine options.
2. Resolve each legal `OptionType.PLAY` option against the public hand.
3. If at least one such legal option is Explorer's Guidance card id `1185`,
   leave H3 unarmed, preserve `_h3_transaction = None`, and delegate the
   unchanged observation to exact historical-Silver.

The veto is semantic:

- lowest option index is irrelevant because H3 chooses no Explorer option;
- duplicate legal Explorer options all produce the same veto;
- Explorer in hand without a current legal play option does not veto H3;
- Lillie's Determination and all other Supporters do not veto H3;
- the rule uses no option-position, serial, episode, seed, opponent, row,
  hidden-card, or revealed-card prediction.

## Callback-local behavior

The veto is recomputed from scratch on each ordinary `MAIN` callback.

- If the parent plays Explorer and finds Duraludon, the parent owns the
  resulting setup.
- If Explorer resolves without forming the line and is no longer legal, H3 may
  arm on a later `MAIN` callback only if every original H3 and Boss-safety
  certificate still passes.
- No H3 stage or snapshot survives a vetoed callback.

## Required positives and negatives

- Preserve the full original H3 positive at `88684114:20`; it has Lillie's
  Determination rather than Explorer.
- Make the three fixed-760 Explorer-first traces parent-identical at their
  former first differences:
  `arch_peak`, `marnie_kazuki_live`, and `mega_lucario_public`, seat 0, seed
  `271958329`, game 16.
- Test both seats, changed serials, permuted options, and duplicate legal
  Explorer options.
- Test Explorer in hand but illegal as a positive.
- Test legal Explorer that forms the line without H3 ownership.
- Test legal Explorer miss followed by later H3 re-arm and full transaction.
- Preserve all original rollback, reset, duplicate, Boss-safety, probability,
  deterministic-Metal, exact-engine, shadow, and fixed-760 gates.

The refined candidate remains a direct sibling of exact historical-Silver.
H1, H2, H4, submission state, and live scores are not implementation inputs.

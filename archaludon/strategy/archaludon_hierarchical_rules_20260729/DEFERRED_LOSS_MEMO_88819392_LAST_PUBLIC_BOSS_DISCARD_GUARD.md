# Deferred loss memo — episode 88819392

Status:

`ROOT_VERIFIED_KNOWN_ACCESS_TRANSITION__CAUSAL_WIN_UNPROVED__DEFER_SEPARATE_SIBLING`

This loss is not Hero's Cape causal evidence. Hero and exact
historical-Silver were identical across all 72 correct-seat callbacks, with
zero starts, action differences, invalid actions, exceptions, or stale
transactions.

- shadow SHA-256:
  `63968CF2B2CB5454288074D99D23B00D370E1CB8EEDCC278A114CB99A693CD23`
- replay SHA-256:
  `4D625ADF892F1D0DC1453E31219025A96C4474D509E5B1E36819225A22F22698`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_last_boss_discard_88819392_20260730/verify_last_boss_discard_state.py`
- verifier SHA-256:
  `64291670E06A3865ED6EA99B062045402474F900D2D49F4432AC45AA5CE35122`
- output:
  `root_verification/archaludon_last_boss_discard_88819392_20260730/root_verification.json`
- output SHA-256:
  `FF33866BAFF5A7F55093B6C5DF73A436DC3906B28C5A8BC1063CC22BA32C7740`

## Root-verified public transition

At row `120`, turn `10`, the Ultra Ball mandatory two-card discard offered:

| Position | Card | Parent score |
|---:|---|---:|
| 0 | Boss's Orders `1182#39` | `8500` |
| 1 | non-ex Archaludon `840#31` | `1000` |
| 2 | Basic Metal `8#57` | `8000` |
| 3 | Archaludon ex `190#9` | `-5000` |

The parent selected positions `[0,2]`, discarding Boss plus Metal.

Public access accounting at that callback was exact:

- three Boss copies `#41/#40/#38` were already in discard;
- the fourth Boss `#39` was the option in hand;
- discarding `#39` changed publicly accessible Boss count from one to zero;
- legal alternative `[1,2]` preserved the same Metal discard and the retained
  Archaludon ex backup while discarding the matchup-inactive non-ex
  Archaludon;
- opposing Bench exposed one-Prize Froslass and Munkidori targets;
- a Supporter had already been played, so retaining Boss was a future-access
  decision rather than a same-turn Boss line.

## Potential later hypothesis

`LAST_PUBLIC_BOSS_DISCARD_GUARD_WITH_PLAN_EQUIVALENCE`

At a mandatory discard callback, protect the last publicly accounted Boss
only when:

1. the deck's exact Boss count and every public Boss zone are supported;
2. the proposed discard changes deterministic accessible count from one to
   zero;
3. a legal alternate discard pair preserves the current search, Energy
   discard, attacker, backup, payment, and exact same-turn attack plan;
4. at least one visible opposing target supplies future Boss value;
5. the alternate card is not required by the current matchup, terminal route,
   Prize wall, forced defense, or reserved transaction;
6. unknown zones, duplicate serials, unsupported recovery, or any plan change
   fail closed.

## Causal limitation

This episode does not prove a win. The opponent later used Unfair Stamp, which
would have shuffled a preserved Boss back into the deck, and later access was
not deterministic. This is evidence for known-hand/public-access bookkeeping
and resource preservation, not evidence that keeping Boss changes the match
result.

Do not stack this rule into Hero or generalize it to “never discard the last
Boss.”

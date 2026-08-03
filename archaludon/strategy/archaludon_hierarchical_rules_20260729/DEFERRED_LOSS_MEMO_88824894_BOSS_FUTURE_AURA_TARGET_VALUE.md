# Deferred loss memo — episode 88824894

Status:

`ROOT_VERIFIED_PUBLIC_TIED_BOSS_TARGET__FUTURE_BOARD_CAUSALITY_UNPROVED__DEFER_SEPARATE_SIBLING`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
the exact historical-Silver parent were identical across all 54 correct-seat
callbacks, with zero Hero starts, action differences, invalid actions,
exceptions, or stale transactions.

- replay SHA-256:
  `330650CEE9D1BE07F759245325982E8810777775F56A336622D721697F5FF6A0`
- Hero shadow SHA-256:
  `F7D9F2AD55A0F719B5C1EC7BA1B5204435A15116F2F8D9CE155AE7356828369A`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_boss_aura_target_88824894_20260730/verify_boss_aura_target_state.py`
- verifier SHA-256:
  `D696B3BAB7BC0FCBF8514F494AAF0D85BBE9385F765D9EF5FE3CF45DFE9E998B`
- output:
  `root_verification/archaludon_boss_aura_target_88824894_20260730/verification_output.json`
- output SHA-256:
  `DF316673F450CFA503A8CA09A45A86159C64D371136E2015D5E3E3C7EE44FC6A`

## Root-verified public transition

At row `79`, turn `6`, Boss's Orders offered four one-Prize Bench targets:

| Position | Target | HP | Parent score |
|---:|---|---:|---:|
| 0 | Gabite | 100 | 23000 |
| 1 | Roserade | 130 | 23000 |
| 2 | Roserade | 130 | 23000 |
| 3 | Roserade | 130 | 23000 |

Our Active Archaludon ex had four Metal Energy, so Metal Defender could KO
every option. Full Metal Lab was in play. Because the parent assigned all four
targets the same score, deterministic tie-breaking selected Gabite.

Later, with all three Roserade still public, the opponent's Draconic Buster
dealt `320` to a fresh `300` HP Archaludon ex:

`260 base + 90 from three Roserade - 30 from Full Metal Lab = 320`.

Removing one Roserade would project that same public modifier to `290`.

## Potential later hypothesis

`BOSS_EQUAL_PRIZE_FUTURE_BOARD_THREAT_TARGET_VALUE`

When Boss targets are equal in immediate Prize value and all are guaranteed
KOs, use a bounded future-board tie-break:

1. first preserve any exact terminal Prize conversion;
2. otherwise value a target's persistent public damage, acceleration,
   switching, draw, spread, or lock effect;
3. apply the adjustment only when the effect is already active from public
   board state and removing one copy changes a known threshold;
4. retain evolution-route and successor-threat checks so removing a support
   Pokemon does not expose a stronger deterministic attacker;
5. fail closed to the parent choice when future attacker identity, hidden
   access, or the threshold is not public.

## Causal limitation

This episode proves a tied Boss decision, the legal Roserade alternatives, and
the observed three-Roserade `320` damage. It does not prove that selecting
Roserade wins: the future fresh Archaludon ex was not public at row `79`, and
leaving Gabite could preserve another Garchomp route. This is evidence for
future-board target valuation, not for a certified match-level counterfactual.

Do not stack this rule into Hero's Cape. It must be tested as its own
direct-parent sibling.

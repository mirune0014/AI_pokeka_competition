# Deferred loss memo — episode 88826155

Status:

`ROOT_VERIFIED_PUBLIC_GUST_LIABILITY__HIDDEN_BOSS_ACCESS__DEFER_MODE_RULE`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
the exact historical-Silver parent were identical across all 89 correct-seat
callbacks, with zero Hero starts, action differences, invalid actions,
exceptions, or stale transactions.

- replay SHA-256:
  `3E294511D4AB0AE0E443EF7D14D33BF115D1C7AB072E433D57A53370B32F6935`
- Hero shadow SHA-256:
  `F1EA985B0A805C56C0F936D7FD8F1163C5CDD68FB6E74F6F65378658032C1012`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_mirror_final_prize_bench_gust_liability_88826155_20260730/verify_mirror_bench_gust_liability.py`
- verifier SHA-256:
  `7EF15E331B6C8EAD628E3C5D952C2FE4ACA1900B668A18B456EF03A97BC78CBD`
- output:
  `root_verification/archaludon_mirror_final_prize_bench_gust_liability_88826155_20260730/root_verification.json`
- output SHA-256:
  `6979BE060261BFD7463B8503B8D8B2E89FBCDE63E8F93F332107080B9732C624`

## Root-verified public transitions

At row `132`, turn `17`:

- the opponent had one Prize remaining; we had two;
- our Bench was empty;
- our sole Active Archaludon ex was `300/300` with three Metal;
- Full Metal Lab was public;
- opposing Active was a `100` HP Relicanth;
- opposing Bench contained an attack-ready Archaludon ex with three Metal.

The visible mirror Metal Defender damage was `190` after Full Metal Lab, so
our sole Active would survive at `110` HP. The parent nevertheless selected
Ultra Ball, score `300` for `bench empty (donk risk)`, over the already legal
Metal Defender, score `220`.

The search fetched Duraludon `169#64`. At row `135`, the parent scored playing
that Duraludon `18000` and benched it before taking the Relicanth Prize.

At row `146`, now at one Prize each, the parent played Poke Pad for `20000`;
at row `148` it scored and benched a second Duraludon `169#66` for `18000`.
The first Duraludon was already the lower-HP terminal gust liability, so the
second copy did not remove that weakness.

The opponent later revealed hidden Boss's Orders `1182#47`, gusted the first
Duraludon `#64`, and used Metal Defender for the observed `190` terminal
damage and final Prize.

## Potential later hypothesis

`MIRROR_FINAL_PRIZE_GUST_LIABILITY_MODE`

Suppress generic empty-Bench search/play priority only when:

1. the opponent has exactly one Prize remaining;
2. our sole Active is a unique attack-ready Archaludon ex;
3. its current HP deterministically survives every currently payable visible
   opposing attack after public modifiers;
4. the proposed Basic Bench Pokemon is worth the opponent's final Prize and
   is deterministically KO'd by a visible ready attacker;
5. no public spread, board-out, forced promotion, retreat, attack-continuity,
   or exact terminal route requires the backup;
6. first execute any exact heal, protection, draw, attack, or terminal route
   whose ordering changes the survival certificate;
7. unsupported matchup, hidden modifier, or ambiguous readiness fails closed.

This is a winning/normal-mode arbitration rule: generic anti-donk setup should
not automatically create the opponent's only easy final-Prize route when the
large Active is already the safer board.

## Causal limitation

Boss access was hidden at the first search and bench decisions. The replay
proves the public Prize liability and visible damage thresholds, plus the
eventual Boss punishment, but it does not prove the no-Bench counterfactual
wins or that the opponent could not choose a different line.

A full-engine branch or repeated public recurrence is required before treating
this as a hard deterministic rule. Do not stack it into Hero's Cape and do not
generalize it to a blanket no-Bench policy.

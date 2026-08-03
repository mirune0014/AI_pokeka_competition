# Deferred loss memo — episode 88824363

Status:

`ROOT_VERIFIED_PUBLIC_FORCED_DISCARD__COMPLETE_COUNTERFACTUAL_UNPROVED__DEFER_SEPARATE_SIBLING`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
the exact historical-Silver parent were identical across all 70 correct-seat
callbacks, with zero Hero starts, action differences, invalid actions,
exceptions, or stale transactions.

- replay SHA-256:
  `3ED067AE3FF43C3696939E9673DF23C74CE52CD584E3E2272179F4B7E5CC0FF6`
- Hero shadow SHA-256:
  `4DB2FEB12414EB23D473B124307C9F983E6CFFC6E9F3C95A4273BE12B04A857E`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_xerosic_terminal_preservation_88824363_20260730/verify_xerosic_discard_state.py`
- verifier SHA-256:
  `9C2EBB252BF7179DBA1A1E4E123A218E7E8557C4F8FF0FA5226CE3BEFBBFEB57`
- output:
  `root_verification/archaludon_xerosic_terminal_preservation_88824363_20260730/root_verification.json`
- output SHA-256:
  `F9DB34FD4FEA6A2837578B5331CE15ADE3042490BC195832D217B044092C5B08`

## Root-verified public transition

At row `112`, turn `11`, the opponent forced an exact two-card discard. We
had two Prizes remaining. The five legal hand options were two Ultra Balls,
Ice Cream, Boss's Orders, and Hero's Cape.

The parent selected Boss plus one Ultra Ball, positions `[3,0]`. The legal
structural alternative `[2,4]` discarded Ice Cream plus Hero's Cape and
preserved both Boss and the second Ultra Ball.

The public board made that distinction strategically relevant:

- opposing Active was Alakazam with one Psychic Energy;
- opposing Bench contained Fezandipiti ex at `160/210`, worth the final two
  Prizes;
- our Bench contained one-Energy Duraludon and one-Energy Cinderace ex;
- preserving Ultra Ball plus Boss could support a later
  search/evolve/Alloy/retreat/Boss transaction after surviving the opponent's
  turn.

## Potential later hypothesis

`OPPONENT_FORCED_DISCARD_TERMINAL_TURN_PLAN_PRESERVATION`

At an opponent-forced discard callback, compare complete public next-turn
transactions rather than independent card discard scores. Preserve a unique
two-Prize Boss conversion package only when:

1. exactly two Prizes remain and a visible two-Prize target is Boss-accessible;
2. the retained cards are all necessary for a public, ordered
   attacker-readiness and Boss transaction;
3. the alternative discard cards are not required for survival, retreat,
   Energy payment, attacker setup, or another higher-certainty line;
4. every step is legal under the visible board and exact card accounting;
5. hidden draw, unknown recovery, or an incomplete transaction fails closed.

## Causal limitation

This replay proves the forced-discard choice, the legal preservation
alternative, and the visible final-two-Prize target. It does not prove that
the complete post-KO search, evolution, Alloy Building, retreat, Boss, and
attack transaction succeeds. A checked full-engine counterfactual is required
before implementation or submission.

Do not stack this rule into Hero's Cape or generalize it to always preserve
Boss under forced discard.

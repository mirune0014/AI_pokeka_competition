# Deferred loss memo — episode 88814136

Status:

`ROOT_VERIFIED_PUBLIC_SEARCH_MISS__DEFERRED_SEPARATE_SIBLING__DO_NOT_STACK_INTO_HERO`

This episode is not Hero's Cape causal evidence. The submitted Hero candidate
and exact historical-Silver parent were identical across all 76 correct-seat
callbacks:

- Hero starts / clears:
  `0 / 0`
- semantic action differences:
  `0`
- invalid actions / exceptions / stale transactions:
  `0 / 0 / 0`
- shadow SHA-256:
  `60B0420F4922893671608F29F6859B51381D07E58ACDE13CB552FB946BBCCC97`

The loss exposes a separate exact-win search/turn-plan hypothesis. It must not
be added to the live Hero source.

## Bound evidence

- replay:
  `live/55083165/refresh_20260729_2325/episode_88814136_replay.json`
- replay SHA-256:
  `147B531CC74A14C1809CA1A762E8A9E739D7BB1F48E8F7CCCBFF5F787770770B`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Root verifier:
  `root_verification/archaludon_terminal_pokegear_boss_88814136_20260729/verify_parent_search_state.py`
- verifier SHA-256:
  `CA0B4617B346FBB53F3AC9CE14987F96DC4D5C12512CED38C589D97805003C74`
- Root output:
  `root_verification/archaludon_terminal_pokegear_boss_88814136_20260729/root_verification.json`
- Root output SHA-256:
  `25432CE4DE99A2317FEFF9739901CB9C889F67776F50A82725C90CD1CEB2F659`

## Root-verified public state

At row `151`, turn `14`, ordinary Main:

- both players had exactly one Prize remaining;
- our Active was Archaludon ex `190#8`, `260/300`, with three Basic Metal;
- opposing Active was Marnie's Grimmsnarl ex `648#88`, `310/320`;
- opposing Bench contained Munkidori `112#76/#75/#77` at `100` HP and
  Froslass `104#74` at `90` HP;
- no Supporter had been played;
- Metal Defender `253` was legal and scored `220`, but could not KO the
  `310`-HP Active;
- Pokégear 3.0 `1122#27` was legal and the parent selected it.

At row `152`, Pokégear's public `TO_HAND` selection:

- Lillie's Determination `1227#48` was visible and scored `6500`;
- Boss's Orders `1182#38/#40` was visible twice and each scored `2500`;
- the parent selected Lillie solely because the generic search score was
  higher;
- the same-turn attacker, Energy payment, opposing Bench HP, remaining Prize,
  and unspent Supporter window were all public.

The parent therefore recognized the value of playing Pokégear but did not
carry its exact terminal objective into the search-choice callback.

## Candidate hypothesis for a later sibling

`POKEGEAR_EXACT_TERMINAL_BOSS_SELECTION_AND_CONVERSION`

Potential transaction:

`Pokégear -> visible Boss -> exact lethal Bench target -> stored Metal Defender`.

The later contract must require all of the following:

1. exact ordinary Main and a unique legal Pokégear play;
2. no Supporter already played;
3. our remaining Prizes are covered by one publicly targetable opposing Bench
   Pokémon;
4. a currently legal stored attack cannot cover the Active but can cover that
   Bench target after exact public damage, prevention, Weakness, Resistance,
   Tool, Stadium, and Prize calculations;
5. Boss is actually present among the public Pokégear choices;
6. the chosen Boss serial is confirmed in hand;
7. Boss, the exact target, and the exact stored attack remain legal and
   unchanged at every continuation;
8. exact terminal, forced-defense, and transaction precedence is explicit;
9. duplicates, retries, unexpected option sets, target disappearance, payment
   change, or unsupported effects fail closed to the parent snapshot.

## Mandatory limitation

Root has verified the missed public search state, not the counterfactual
engine branch. Before implementation or submission, a checked both-seat engine
transaction must prove:

`Boss selection -> Boss play -> target switch -> Metal Defender -> final Prize`.

Until that gate passes, this is a high-quality implementation hypothesis, not
a proven match conversion.

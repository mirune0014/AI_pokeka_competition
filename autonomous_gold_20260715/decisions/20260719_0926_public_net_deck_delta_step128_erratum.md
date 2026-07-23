# Erratum: episode 86778139 step-128 Psychic Draw fixture

- Recorded: 2026-07-19 09:26 JST
- Owner: root
- Governing decision:
  `20260719_0910_fez_exposure_reject_and_public_net_deck_delta_select.md`
- Scope: this file supersedes only the step-128 positive fixture; every other
  contract, parent, deck, non-goal and gate remains frozen
- Kaggle write: none

## Exact replay fact

Replay `86778139` remains SHA-256
`E81761637DE5281CFB03345F3E1C5576400ED5353334E7AB907C905A98B5271F`.
At target step 128:

- own deck count `10`, own hidden Prizes `4`;
- Active Alakazam serial `11` has no Energy;
- Bench Alakazam serial `12`, the exact Psychic Draw context card, has no
  Energy;
- Hilda is visible in hand, but no Psychic Energy is visible there;
- the fixed deck began with two Basic Psychic and four Telepath Psychic;
- public zones expose only Basic Psychic serial `56` and Telepath serials
  `60,61` in discard; Enriching Energy serial `62` is attached to Dudunsparce;
- therefore exactly three searchable Psychic Energy cards remain across the
  ten-card hidden deck and four hidden Prizes.

Because `3 <= 4`, every remaining Psychic Energy can legally be Prized. Hilda
does not certify an Energy target by public pigeonhole reasoning. Treating one
as available would assign a hidden identity and violate the governing
no-hidden-card contract.

## Authoritative correction

- Steps 108 and 110 remain positive Psychic Draw-NO fixtures because the
  current attack and a separate backup are already public and Energy-ready.
- Step 128 is a **negative fail-closed fixture**: delegate to exact-v3 YES
  unless a different reconstructed state supplies a fully public or
  mathematically forced current-attack route without the unknown draw.
- Do not add or force Hilda, search, attachment or attack ranking to make this
  fixture pass.
- Step 131 Helmet suppression and steps 141/143 positive-net Run Away Draw
  fixtures remain unchanged.

This correction narrows the candidate and removes an invalid hidden-card
assumption. It does not weaken the frozen requirement for two natural changed
keys, one conservation-class activation, one positive-net Run Away activation,
zero regressions, and at least one gain beginning with the intended mechanism.

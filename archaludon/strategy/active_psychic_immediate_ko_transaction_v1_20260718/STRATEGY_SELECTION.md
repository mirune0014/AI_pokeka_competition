# Strategy selection: Active Psychic immediate-KO transaction v1

## Evidence and parent

- Parent: `alakazam_fez_public_retaliation_guard_v2`, source SHA-256
  `A776D74ECE4C08B9FA71225E81C444F5C39134863C884CF44C704CE52F55F122`.
- Live submission: `54790261`; first completed public episode score `497.2`.
- Qualitative report SHA-256:
  `5ABF983DF3609DD2C02AD49B2E690A91B4C2810F2EAFC6DEC6D99427554A27B8`.
- The submitted Fez bridge/retaliation rule was eligible zero times and fired
  zero times in the validation win and first public loss. Neither outcome is
  attributed to it.

## Selected broad mechanism

The agent currently treats Energy attachment as an ordinary scored action.
Consequently, unrelated setup actions can shrink the hand or spend the turn
before an already certified attack is enabled. Replace that failure mode with
a state transaction over the full public-state class:

`Active Alakazam has no Psychic + a legal exact hand Psychic attachment exists
+ conservative post-attachment hand damage KOs the current Active + public
post-KO deck/prize clock is viable -> attach exact Energy -> suppress optional
Telepath bench search -> immediately use Powerful Hand -> Prize`.

This is deliberately not an episode-ID patch. It applies to every legal card
serial, turn, seat, opponent and target satisfying the same public certificate.
It also has an exact adjacent fail-closed boundary when the post-attachment
hand no longer KOs.

## Live anchors

- Public episode `86544355`, `S134`: hand/deck/Prizes `8/7/3`, unenergized
  Active Alakazam versus 140-HP Alakazam. Telepath attachment leaves seven
  cards and exactly 140 damage. Parent instead plays Dunsparce.
- `S135`: after that play, hand seven becomes six after attachment and only
  120 damage; the rule must not fire against the same 140-HP target.
- `S143`: hand/deck/Prizes `7/4/3`, two legal Telepaths, unenergized Active
  Alakazam versus Bossed 80-HP Kadabra. Parent selects END; the transaction
  certifies 120 damage, a one-Prize KO, and post-KO clock `4 > 2`.

## Retention and submission threshold

Before any next Kaggle write require compile/import, exact legal 60 cards,
deterministic source/runtime parity, reconstructed S134/S135/S143 engine
boundaries, packaged both-seat smoke, and a fixed paired schedule with no
known action errors or material adjacent-matchup regression. Because the user
explicitly requested practice-first three-hour probes, broad 1,440-game proof
is not required before the first live test; a short identical-seed both-seat
comparison plus direct changed-position inspection is sufficient if the
candidate converts the live mechanism and remains valid.

# Root-verified Fez immediate-KO live anchors

This is public board/mechanics evidence, not an action-label dataset or a
counterfactual win claim. Replay report label `Sx` equals raw `steps[x+1]`.

## Qualifying earliest states

| Episode | Replay SHA-256 | State | Frozen transaction certificate |
| ---: | --- | --- | --- |
| 86386369 | `5AFA8B11237C2F0F9E34D0F2957E52FCA4360942555A853F369750247FFD25DB` | raw 49 / S48, turn 5, P0 | Active Fez `s19`, Telepath `19/s60` as payment; Bench[0] Alakazam `s11`, Telepath `19/s61`; hand/deck/Prizes `12/26/6`; Solrock `676/s71`, HP `110`, Energy `6/s111`, no Tool/status; Powerful Hand `240`; post-KO `26 > 5`. |
| 86430395 | `847D5E1F0710385F20560821AC462D63BEBAF48473B4E7C008075B3F6676FFB3` | raw 91 / S90, turn 10, P1 | Fez `s79`, Telepath `19/s118`; Bench[1] Alakazam `s71`, Telepath `19/s120`; `13/15/6`; Crustle `345/s20`, HP `150`, Dwebble `344/s17`, Grass `1/s5`, no Tool/status; Powerful Hand `260`; post-KO `15 > 5`. Crustle's visible prevention is ex-only and Alakazam is non-ex. |
| 86387293 | `8EC3C588A866AA7D32A96DD75F666275E788583932265153720329F4C97AA1B3` | raw 73 / S72, turn 6, P1 | Fez `s79`, Enriching `13/s122`; Bench[0] Alakazam `s73`, Telepath `19/s119`; `12/24/6`; Kadabra `742/s27`, HP `80`, Abra `741/s23`, Telepath `19/s7`, no Tool/status; Powerful Hand `240`; post-KO `24 > 5`. |

## Mandatory winning boundaries

- `86387405`, replay SHA-256
  `19C0221B261C91677A39F7850D3D6E726ACA51432BE7898AB30EC6E3F6D8FF20`:
  raw 55 / **S54**, turn 6 P1 is the earliest exact certificate. Fez `s79`
  pays Enriching `13/s122`; Bench[0] Alakazam `s72` has Telepath `19/s121`;
  hand/deck/Prizes `10/21/6`; Roserade `342/s51` has HP `200` after Power
  Weight `1173/s10`; Powerful Hand is exactly `200`, and `21 > 5`.
  Earlier S49/S50 damage `180/160` fails closed.
- `86381796`, replay SHA-256
  `2F3A9C5E2B36F6D638C35E11B6A472FD1254C00BB572CB281A081502203978EB`:
  raw 58 / S57, turn 5 P0. Fez `s19` pays Telepath `19/s59`; Bench[0]
  Alakazam `s12` has Basic Psychic `5/s57`; `17/18/6`; Cinderace `666/s73`
  HP `160`, Energy `8/s118`, no Tool/status; Powerful Hand `340`; `18 > 5`.

## Required fail-closed boundary

`86385015`, replay SHA-256
`E49D289735BE47ACF14407442E8C55C5EDD5491E51A3652BA653D79B31FA7DC5`,
has no certificate. At S84, hand 6 yields only 120 against 140-HP Great Tusk,
which also carries Mist Energy. Later states remain below 140; deck count falls
to 4, 2, then 0 while five Prizes would remain, and Rock Fighting Energy is
present on the printed Fighting Pokemon. Damage, post-KO clock, and protection
predicates independently fail.

## Checked retreat callback sequence

The actual engine sequence in these histories is:

`MAIN(0) RETREAT -> DISCARD_ENERGY(30) OptionType.ENERGY -> SWITCH(3)
OptionType.CARD from BENCH -> MAIN(0)`.

`TO_ACTIVE(4)` is not the observed retreat-promotion callback. Directed engine
tests must prove the exact frozen payment serial, exact frozen Alakazam serial
under `SWITCH`, unchanged target/hand/deck/Prize fingerprint, and immediate
attack `1072` before Phase 0 promotion.

# Deferred loss memo — episode 88814688

Status:

`ROOT_VERIFIED_PUBLIC_DEFENSE_STATE__INSUFFICIENT_WIN_CAUSALITY__DEFER_ONLY__DO_NOT_STACK`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
exact historical-Silver parent were identical across all 53 correct-seat
callbacks:

- Hero starts / clears:
  `0 / 0`
- semantic action differences:
  `0`
- invalid actions / exceptions / stale transactions:
  `0 / 0 / 0`
- shadow SHA-256:
  `25AEA8A0BA55C7636498689104F933A91B0F56625ADC58DA3501944DC811374B`

The state exposes a possible forced-defense Boss mode, but the replay does not
prove that it converts the loss. It must remain separate from the live Hero
candidate and from the exact-terminal Pokégear/Boss hypothesis in episode
`88814136`.

## Bound evidence

- replay:
  `live/55083165/refresh_20260729_2325/episode_88814688_replay.json`
- replay SHA-256:
  `859A887084258D61DCAF372658FA2A20FC1D3A36B537DC004215CEBF24823F80`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Root verifier:
  `root_verification/archaludon_terminal_defense_boss_88814688_20260729/verify_parent_boss_stall_state.py`
- verifier SHA-256:
  `86206EB43D5B4B37BC2CE047F3D83BFD3FBEF9004F8BE0905BBA8B8C0E94258C`
- Root output:
  `root_verification/archaludon_terminal_defense_boss_88814688_20260729/root_verification.json`
- Root output SHA-256:
  `57A4007FFE6ECC366D009FEDE4D2364F49B7F9FEF2BA0B5829EB235C5404DBAE`

## Root-verified public state

At row `88`, turn `12`, ordinary Main:

- the opponent had one Prize remaining;
- our only Pokémon was Active Duraludon `169#63`, `130/130`, with one Metal;
- opposing Active was attack-ready Alakazam `743#26`, `140/140`, with one
  Psychic;
- the only opposing Bench Pokémon was zero-Energy Abra `741#20`, `50/50`;
- no Supporter had been played;
- Boss's Orders `1182#98` was legal but scored `-500`,
  `save Boss: no attacker`;
- Lillie's Determination `1227#107/#108` scored `5000`;
- the parent selected Lillie;
- Hammer In `223` was legal for `30`, but the exposed Duraludon remained below
  the publicly visible Powerful Hand damage floor.

Playing Boss and selecting Abra would move the ready Alakazam out of the
Active and leave the opponent needing attachment, retreat, switch, or another
route before the terminal attack.

## Why this is not a hard rule yet

Public state proves the immediate threat and the extra access burden, but it
does not prove that the opponent lacks the required hidden attachment or
switch access. Therefore:

- Boss is a legal defensive alternative;
- the parent has no score mode for this defense;
- this replay does not prove Boss wins or even improves the realized outcome;
- a broad `opponent at one Prize -> Boss an unenergized Bench` rule may waste
  the Supporter window and Lillie rebuild.

Potential later hypothesis:

`VISIBLE_TERMINAL_ATTACKER_BOSS_ACCESS_BURDEN_MODE`

It should be considered only after a card-count/effect-based access bound can
quantify the opponent's public escape routes. Until then this replay is a
positive state-local example for generating alternatives and a negative
control against claiming a deterministic forced win.

## Independent recurrence — episode 88820060

Episode `88820060` is a second parent-identical loss in the same rule family:

- replay SHA-256:
  `A8D809345105B9856C39CB6156655AA4E392C2578C7B73F70F781DCBC6B83985`
- Hero shadow:
  15 callbacks, zero starts, action differences, invalid actions, exceptions,
  or stale transactions
- Hero shadow SHA-256:
  `A6D39F3D79A74E6F8B6DE8CA7A8FFA62CBFAAB65F07A9D01B0571DB3A49D9327`
- Root verifier:
  `root_verification/archaludon_terminal_boss_stall_88820060_20260730/verify_visible_board_wipe_boss_state.py`
- verifier SHA-256:
  `AE1E021EEA97768628E3A487969151D10BACACA4E38C1A02C894F0069BBF1D13`
- Root output SHA-256:
  `7B8C574B99F1DDDB7A50DA88CD707FD1A19973145DF94C7373CBF7E756F6DAEB`

At row `53`, our only Pokémon was newly evolved non-ex Archaludon
`840#31`, `180/180`, with one Metal. Full Metal Lab was public. Opposing
Active Mega Lucario ex `678#93` had two Fighting Energy, making Mega Brave
`983` publicly payable. Its observed `270` became `240` through the Stadium
and still produced board-out. Boss `1182#39` was legal but scored `-500`,
`save Boss: no attacker`; End scored `0` and the parent ended.

Opposing Bench contained zero-Energy Makuhita `673#80`. Boss could expose that
target and turn the visible board wipe into an attachment/retreat/switch
access problem. Root verified the public threat, Boss option, zero-Energy
target, parent End, and observed `240` terminal attack.

This recurrence strengthens the claim that the parent lacks an Active-centric
forced-defense mode. It still does not prove victory: hidden switch,
attachment, acceleration, evolution, or later recovery cannot be excluded
from public state. The eventual rule therefore needs a public access bound or
a clearly labeled comeback mode, not a deterministic-win label.

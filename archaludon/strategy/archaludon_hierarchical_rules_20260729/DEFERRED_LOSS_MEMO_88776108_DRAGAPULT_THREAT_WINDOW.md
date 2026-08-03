# Deferred loss memo — episode 88776108

Status: `DEFER_ONLY__DO_NOT_STACK_INTO_H6`

Replay:
`autonomous_gold_20260715/live/55077607/refresh_20260729_182911/episode_88776108_replay.json`

Replay SHA-256:
`4A3DBF7BC27EA49B84236BE96497E1FDAD5381C92171C357C3A36294ED8EDB87`

The target was seat 1 and lost. Root shadowed all 26 actionable callbacks:
H6 v2 was exactly parent-identical with zero invalid actions, exceptions, or
stale transactions. This episode is not H6 causal evidence and does not
authorize an H6 repair.

## Root-verified public path

- At row 41, turn 5, the target had Active Duraludon `s65` at 130 HP with
  exactly two Metal, Bench Duraludon `s63`, Archaludon ex `s67` and Poke Pad
  `s76` in hand. Both Active and Bench evolution routes were legal.
- Poke Pad found Duraludon `s66`, which was benched. At row 44 the legal main
  actions were evolve Active, evolve the older Bench, Hammer In, concede, or
  end. The inherited policy chose Hammer In for 30.
- The opponent's public board already showed a mature Dragapult line and
  Duskull. On the next opposing turn, Dusknoir's Cursed Blast placed 130 damage
  on Active Duraludon and KOd it. Dragapult ex then used Phantom Dive, KOd the
  promoted Duraludon through Full Metal Lab, and placed 60 damage on the final
  Duraludon.
- At row 78 the target's only Pokémon was Duraludon `s66` at 70 HP. It evolved
  to Archaludon ex at 240/300 HP and Assemble Alloy attached the only two
  discarded Metal. No third Metal was available, so no attack was legal.
- Hero's Cape later raised the damaged Archaludon from 70/300 to 170/400, but
  the next 170-damage Phantom Dive still produced board-out.

## Deferred hypothesis A — threat-window defensive evolution

Potential trigger:

- Active Duraludon has two Metal;
- Archaludon ex is legally available;
- no discarded Metal makes Assemble Alloy immediately productive;
- the opponent publicly shows Duskull plus a mature Dragapult line;
- the inherited attack cannot take a Prize;
- at least two backup Pokémon are already in play.

Potential change: evolve the Active before ending the turn, even though the
current evolution attaches no Energy and temporarily forgoes Hammer In.

Why it may help here: the public `130 + 170` damage sequence would need both
effects on the 300-HP Archaludon rather than using Cursed Blast to force a
promotion and Phantom Dive to take a second KO. This preserves another backup
and may improve the following attack-continuity window.

Required falsifiers:

- the lost chip crosses a real Prize or later lethal boundary;
- the two-Prize evolution exposes a worse Prize exchange;
- the opponent lacks a sufficiently mature, publicly reachable threat;
- exact continuation does not improve survival or attack readiness.

This is only a future source for the broader 1–2-turn public-threat mechanism.
It must not become an episode-specific rule.

## Deferred hypothesis B — Ultra Ball draw-continuity guard

Earlier, the target discarded Lillie plus Explorer to Ultra Ball and then
played mostly from top-decks. Preserving one draw supporter could improve access
to the third Metal. However, the redundant Full Metal Lab was later required
after the opponent replaced the first Stadium, so this episode does not prove a
safe alternative discard. Keep this lower-confidence hypothesis separate until
a positive public-state source exists.

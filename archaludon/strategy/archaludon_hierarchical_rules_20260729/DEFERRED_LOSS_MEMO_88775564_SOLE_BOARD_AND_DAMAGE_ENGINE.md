# Deferred loss memo — episode 88775564

Status: `DEFER_ONLY__DO_NOT_STACK_INTO_H6`

This memo is not a selected implementation hypothesis.

## Evidence identity

- replay:
  `live/55077607/refresh_20260729_182435/episode_88775564_replay.json`
- replay SHA-256:
  `F3995E067637F813345AFAD1DC9F9D1C43FAEACB37C7EC8EAC548DC6F929C1B4`
- target seat/result: `0 / loss`
- H6 correct-seat shadow: 22 callbacks, zero action differences, invalid
  actions, exceptions, or stale transactions

The loss is parent-path evidence and cannot justify an H6 repair.

## Root-verified public path

- Rows 13–18, turn 2: Active Duraludon plus a newly benched Duraludon were
  publicly established. The Active received one Metal and Hero's Cape, then
  used Hammer In `223`.
- Row 42: the Active was gone; the only remaining Pokémon was a 100/130-HP
  zero-Energy Duraludon. Cape was no longer attached.
- Rows 43–48, turn 4: the lone Duraludon received one manual Metal, evolved
  into Archaludon ex, and Assemble Alloy placed one discarded Metal. The
  resulting benchless Active had 270/300 HP and exactly two Metal. The only
  ordinary MAIN options at row 48 were Full Metal Lab and END; no attack was
  legal.
- Row 52, turn 6: the same benchless Archaludon had 60/300 HP and two Metal.
  Hand was Archaludon ex, Boss's Orders, Metal, and Full Metal Lab.
- Rows 52–54: the agent played Full Metal Lab, attached the third Metal, then
  chose Boss rather than immediate Metal Defender.
- Row 55: legal Boss targets were three Impidimp and two Froslass. The agent
  selected a 40-HP Impidimp.
- Rows 56–57: Metal Defender `253` KO'd that target; a later Prize reveal
  supplied the Ultra Ball, only after the attack had already ended the turn.
- The subsequent opponent turn ended the game by board-out. H6 never armed.

The public sequence proves sole-board attack discontinuity. It does not prove
that any alternate earlier action would win, because future draws, Prize
identity, hidden opponent cards, and opponent responses were unknown at the
relevant decisions.

## Deferred hypothesis A — sole-board backup transaction

Potential scope:

> Before a nonterminal attack from the only Pokémon in play, prefer one
> deterministic visible route that benches a Basic without consuming the
> unique resource required for the same attack.

Expected benefit: avoid immediate board-out and preserve a successor.

Required trigger:

- currently benchless board;
- attack is nonterminal;
- a visible legal search/bench route is guaranteed to produce a Basic;
- the same attack remains payable after that route;
- no exact terminal, Prize, forced-defense, or setup conversion is displaced.

Mandatory negatives:

- no visible backup access;
- backup depends on a future draw or unknown Prize;
- the route discards/uses the sole attack-critical resource;
- attack is terminal;
- a ready successor already exists.

This replay is a negative control, not a positive source: Ultra Ball became
known only as the post-attack Prize. No deterministic visible backup route
existed at the row-52 decision.

## Deferred hypothesis B — damage-engine Boss target override

Potential scope:

> Prefer removing a persistent between-turn damage engine only when exact
> public arithmetic crosses a survival or next-attack-continuity boundary
> relative to the inherited Boss target.

Mandatory proof:

- exact target damage engine and tick count;
- exact post-KO Active HP;
- exact remaining public return attacks;
- removing the engine changes survival or preserves another attack;
- no higher-Prize or terminal line is displaced.

This replay must be a parent-identical negative. Removing one Froslass would
leave one damage tick, while the public ready Grimmsnarl attack still exceeded
the remaining 60 HP through Full Metal Lab. The target change therefore does
not cross a survival boundary and must not fire.

## Decision

Do not implement either idea from this single loss. Preserve this replay as:

1. a negative for any hidden/future-access backup rule; and
2. a negative for damage-engine targeting without a proven survival boundary.

Require a separate positive replay or fixed engine source before Sol-Ultra
strategy selection.

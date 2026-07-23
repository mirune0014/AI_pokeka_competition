# Strategy selection: Alakazam visible mill-clock minimum draw v1

- Selection time: 2026-07-16 22:16:22 +09:00
- Parent: exact public Best-5 Alakazam
- Deck change: none
- Implementation target: `alakazam_visible_mill_clock_minimum_draw_v1`
- Kaggle action: none at selection time

## Selected hypothesis

When a public Great Tusk deck-out route is visible and the remaining deck is
no longer safely ahead of the prize clock, the agent should stop maximizing
hand size. It should take only the minimum deck-consuming action needed for a
current attack or one known successor, then attack. The rule is a public-state,
deterministic `PRIZE_RACE -> DECKOUT_CONTROL` transition, not an opponent-policy
model.

The read-only Sol-Ultra strategy judge selected this hypothesis before source
implementation. The exact deck, target selection, damage formula, and all
non-Great-Tusk behavior remain outside its scope.

## Root-verified target evidence

The root recomputed the four historical exact-parent summary files directly.

| block | policy seat | wins | losses | losses ending with own deck 0 |
| --- | ---: | ---: | ---: | ---: |
| 2026071501-1540 | 0 | 7 | 33 | 32 |
| 2026071501-1540 | 1 | 9 | 31 | 31 |
| 2026071541-1580 | 0 | 12 | 28 | 26 |
| 2026071541-1580 | 1 | 8 | 32 | 32 |
| **total** | both | **36** | **124** | **121** |

Every row was started, every action-error total was zero, and no row hit the
maximum-step limit. Terminal deck zero is an association, not by itself proof
that optional draw caused every loss; trace conversion remains mandatory.

Bound raw SHA256 values:

- block 1 seat 0: `069B942A586A48701C3B9B909A01653D41E5565F542943EEE0D304DCAC179146`
- block 1 seat 1: `EE77635B1D1632CC41463221D1E44A88F4D680C23F1232FA130E80E9B40F818C`
- block 2 seat 0: `819D09B3DEE99BBED321A1D714DDAFE8D1298B09F23DCD66757EC8744AC911A2`
- block 2 seat 1: `E726FCCBAFFEE02D77D7F627DD6F11BC005235B9E2671FE254E077A8550D111E`

## Parent binding

- parent source SHA256: `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4`
- parent runtime-wrapper SHA256: `D37DBBE7933F939266D1D1DEEFEEC666CF908A910F56539AFF37936E30CBCBA9`
- exact 60-card deck SHA256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

The exact implementation contract is frozen in
`implementation/alakazam_visible_mill_clock_minimum_draw_v1/IMPLEMENTATION_SPEC.md`.

## Decision boundary

This selection authorizes one isolated implementation and local comparison.
It does not authorize packaging or submission. Promotion requires target gains,
fresh-seed replication, exact non-target retention, trace conversion, root
recomputation, and a final read-only Sol-Ultra judgment.

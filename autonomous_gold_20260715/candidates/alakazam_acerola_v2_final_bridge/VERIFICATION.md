# Alakazam Acerola v2 final bridge

## Immutable parent and exact deck change

Parent: `../alakazam_neutralization_v0_public_best5_exact`.
The parent files were read-only and retain these SHA256 values:

- parent `main.py`: `DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4`
- parent `deck.csv`: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

The candidate has exactly 60 cards. Its only multiset difference is
Battle Cage 1264 from four to three copies and Acerola's Mischief 1228 from
zero to one copy. Enriching Energy 13 remains the sole ACE SPEC and every
other count is unchanged.

## Bounded deterministic rule

`acerola_final_bridge` scores Acerola at 3300, immediately above the
baseline's other Supporters, only when every requested public-state gate is
true. Powerful Hand legality is certified by the current legal ATTACK option.
Projected damage is the immediate public Powerful Hand value at the Acerola
PLAY decision: with current hand size `n` and `h` visible special-defense
energies on the opponent Active, `D=max(0,n-1-h)*20`. If fewer than `h`
Enhanced Hammers are currently in hand, the bridge hard-fails. Future ability,
evolution, Supporter, or other maximum-hand draws are not credited to `D`.
Immediate winning KO still uses the baseline's existing target, maximum-hand,
draw/evolution, Hammer, Boss, and prize calculations.

Acerola target selection is recognized through public `select.effect` or
`select.contextCard` card 1228 and assigns the unique highest score only to
our Active Alakazam. All non-Acerola scoring branches retain the parent logic.

KO readiness is deliberately fail-closed. A threat is certified only for an
attack with an empty public attack-text field and positive fixed base damage.
The opponent's Active ex may have a visible energy deficit of at most one
attachment; a non-ex safety veto requires zero missing energy and therefore
must be currently ready. Rainbow Energy is a typed wildcard. Weakness is
ignored as a conservative lower bound; public
Resistance is subtracted. Dynamic, conditional, coin-based, text-modified,
or otherwise non-fixed attacks never activate this bridge. No hidden card,
opponent identity, future switch, learned ranking, replay label, randomness,
or search is used.

## Focused verification

Command:

`py -3.11 -m py_compile <candidate/main.py> <candidate/runtime/main.py> <candidate/tests/test_acerola_final_bridge.py>`
followed by
`py -3.11 <candidate/tests/test_acerola_final_bridge.py>`.

Exit 0; output `acerola final bridge focused tests: PASS`.
The tests cover legal 60-card counts, exact deck delta, ACE legality, runtime
deck identity, fixed ready-or-one-attachment ex KO certification, rejection
of dynamic attacks, the regression that a one-energy-short non-ex does not
veto while the same non-ex at zero missing energy does, the positive
predicate, exact `n-1` damage without defense, the `n-1-h` Hammer-paid case,
hard failure when `h` exceeds the Hammer count, rejection of an otherwise
passing maximum-hand-only future draw, every bounded negative gate,
deterministic repeated action, active-target selection, a shared-card fallback
observation identical to the parent action, and repository-root runtime import
plus deterministic initial deck return.

A one-game checked-engine execution smoke was run only after the focused tests:
candidate runtime versus the exact parent runtime, seed 1228001, maximum 1200
steps. Exit 0; 145 steps, `action_errors=0`, `hit_max_steps=false`.
This is an execution check, not matchup evidence or a promotion claim.

## SHA256

- candidate `main.py`: `F71FBB59D2B789B3D76246B94A2396B3674A313399E04E4FBA109B4C297B9888`
- candidate `deck.csv`: `B3409FBB5C9A4F71D6F4B3DAF7C64FDF0943BA2918D263CE4F17A3B0B470F8E2`
- runtime `main.py`: `364DB6CD4D347A10F966313F10E0ECCBEE0AF79D76B274401B2458926EC8B345`
- runtime `deck.csv`: `B3409FBB5C9A4F71D6F4B3DAF7C64FDF0943BA2918D263CE4F17A3B0B470F8E2`
- `tests/test_acerola_final_bridge.py`: `F800A0712085358822D4A7335AAA65C2E285047EDBD47B0AC9F8EB459A9B72BF`
- `smoke_summary.json`: `9762B249B913171701E670679365B9ADBAC0BC90ED4C054816C1AD49669D58EA`
- `smoke_trace/game_0000.jsonl`: `33DE1057026CCEA4880FC7DB168CAB8BA38B31AB5E16029735F96203BD9CD94C`

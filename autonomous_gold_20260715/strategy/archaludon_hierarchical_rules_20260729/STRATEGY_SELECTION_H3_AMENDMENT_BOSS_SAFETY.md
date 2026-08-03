# Controlling H3 amendment — Boss safe-discard certificate

This amendment controls over the conflicting Boss-discard sentence in
`STRATEGY_SELECTION_H3.md`. All other H3 requirements remain unchanged.

## Root-verified contradiction

At positive `88684114:20`, seat `0`, the opposing board is:

- Active `675#65`, `110/110` HP;
- Bench `673#63`, `80/80` HP;
- Bench `676#68`, `110/110` HP;
- Bench `677#72`, `80/80` HP;
- Bench `677#73`, `80/80` HP.

The opposing Bench is therefore not empty. The original item 10 incorrectly
described the positive as having an empty opposing Bench.

Turbo Flare `965` deals `50` before public modifiers and KOs none of these
targets. Both players have six Prizes. No legal Boss choice creates an exact
same-turn KO, match win, Prize conversion, or higher-precedence parent
finishing route.

## Controlling rule

Replace the positive's Boss-safe wording with:

> Boss is a certified safe discard only when no opposing Active or Bench
> target creates an exact same-turn KO, match win, Prize conversion, or
> already-certified historical-parent finishing route with any currently
> legal attack after applying all public modifiers.

The opposing Bench may be empty or nonempty. A nonempty Bench never makes Boss
safe by itself; every legal target must be checked. Any exact conversion, any
unknown public modifier, or any ambiguous target fails closed.

At `88684114:20`, the only certified H3 discard pair remains:

1. Ice Cream while the full-HP Active cannot benefit from it;
2. Boss because all five opposing targets fail the exact current conversion
   test above.

This amendment does not authorize generic Boss discard scoring, future-turn
opponent prediction, matchup markers, hidden-card inference, or any H1/H2
behavior.

## Required tests

- The exact positive must arm despite four opposing Bench Pokémon.
- A synthetic otherwise-identical state where one Bench target is a public
  Turbo Flare KO must not discard Boss and must not arm H3.
- A synthetic state with an exact current Boss terminal route must remain the
  historical parent action.
- Empty opposing Bench remains eligible only when every other H3 certificate
  condition holds.

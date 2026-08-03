# Controlling amendment: H1 Prize predicate

This amendment supersedes every contrary Prize statement in
`STRATEGY_SELECTION.md`. All non-Prize trigger, precedence, target, transaction,
rollback, duplicate, forbidden-generalization, shadow, engine, evaluation, and
conditional live-probe provisions remain unchanged.

## Verified correction

- `ROOT_PRIZE_STATE_CORRECTION.md` SHA-256:
  `AC87B1C5D17E28116968C9C385BECA8ED2E6DB0EB3D0BC9D5F34969F9DB4B712`.
- `episode_88457867_replay.json` SHA-256:
  `17FACDE22AFDF51F203F6100C76593AF100AF04619EEF8561E1DED21749E5879`.
- Raw row `steps[144].observation[1]`: our remaining Prizes `3`, opponent
  remaining Prizes `2`, with all cited board, hand, Energy, and legal-Attack
  facts confirmed.

## Controlling decision

H1 must require exactly `3/2`. Do not use a semantic range in the first
candidate.

The same-Prize threat-removal logic plausibly extends elsewhere, but no
root-verified state establishes its Supporter and prize-tempo tradeoffs at
`2/1`, `2/2`, or earlier prize counts. Exact `3/2` is the minimum
evidence-backed public phase and minimizes callback and regression surface
without using an episode-ID exception.

## Replacement trigger clauses

1. Our remaining Prize count is exactly `3`.
2. Opponent remaining Prize count is exactly `2`.
3. The current opposing Active yields exactly one Prize.
4. The certified Bench Alakazam target yields exactly one Prize.
5. Metal Defender KO of either target is nonterminal and leaves our Prize
   count exactly `2`.
6. Neither KO is a board-out or other terminal win; any certified current
   terminal win retains higher precedence.
7. Our Active Archaludon ex yields exactly two Prizes.
8. The certified public Powerful Hand KO therefore changes the opponent's Prize
   count from `2` to `0` and is terminal.
9. The target still must be the unique visible ready terminal response threat,
   and no visible ready terminal successor may remain after its KO.

The transaction snapshot must store and revalidate the exact initial Prize
tuple `(our=3, opponent=2)`. Any mismatch before Boss confirmation fails
closed; any post-confirmation mismatch uses the existing logical rollback
contract.

## Positive tests

- Primary positive is reconstructed `88457867:144` with exact `3/2`: Boss
  `1182` -> Alakazam `743`, serial `12` -> Metal Defender `253`.
- Repeat the same semantic `3/2` state with changed serials and permuted option
  order.
- Repeated callbacks and duplicate semantic options remain positive only while
  the snapshot still validates exact `3/2`.

Remove the previous synthetic positive for other opponent Prize counts. No
`2/1` or ranged-Prize case is positive.

## Negative tests

H1 must not arm when:

- our remaining Prizes are anything other than `3`;
- opponent remaining Prizes are anything other than `2`;
- specifically, the erroneous `2/1` state is supplied;
- either KO yields anything other than one Prize;
- either current KO wins immediately or causes board-out;
- either KO would leave our Prize count other than `2`;
- KOing our Archaludon ex would not take the opponent from exactly `2` to `0`;
- any original non-Prize certificate fails.

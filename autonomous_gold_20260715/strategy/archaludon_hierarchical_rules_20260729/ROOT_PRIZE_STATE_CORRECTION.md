# Root correction: episode 88457867 prize state

This correction supersedes the prize-count statements in
`ROOT_CANDIDATE_SELECTION_EVIDENCE.md` and the corresponding immutable trigger
in `STRATEGY_SELECTION.md`. No candidate source had been created when the
contradiction was found.

## Direct raw verification

Source:

`autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88457867_replay.json`

At replay-array row `144`, the historical-Silver Archaludon observation is
`observation[1]`:

- `current.yourIndex = 1`;
- `current.turn = 12`;
- `len(current.players[1].prize) = 3`: our remaining Prizes are `3`;
- `len(current.players[0].prize) = 2`: opponent remaining Prizes are `2`;
- our Active is Archaludon ex `190`, serial `70`, HP `300`, with three Metal;
- opponent Active is Dunsparce `305`, serial `16`, HP `70`;
- unique ready Bench Alakazam is `743`, serial `12`, HP `140`, with one
  Psychic and full visible Abra/Kadabra lineage;
- opponent `handCount = 21`, `deckCount = 7`;
- our hand includes Boss's Orders `1182`, serial `101`;
- Metal Defender `253` is a current legal Attack option.

The later public consequence is consistent with the corrected count:
Archaludon KOed the one-Prize Dunsparce, so the opponent's remaining Prizes
became `1`; Alakazam then KOed the two-Prize Archaludon ex and ended the game.

## Nature of the error

The Alakazam audit table recorded the state as our/opponent `3-2`, but its prose
later described the attack as taking the opponent's “last Prize.” The root
candidate-selection synthesis incorrectly converted the state to `2-1`, and
the first Sol-Ultra contract inherited that error.

The implementation worker checked the frozen positive against raw fields before
editing, reported the contradiction, and made zero source changes.

## Required amended decision

The strategy judge must decide the narrow public prize predicate. The minimum
directly evidenced predicate is:

- our remaining Prizes exactly `3`;
- opponent remaining Prizes exactly `2`;
- both the current Active and certified Bench Alakazam yield exactly one Prize;
- either KO is nonterminal for us;
- a Powerful Hand KO of our two-Prize Active is terminal for the opponent.

Any broader predicate such as our Prizes `2` or `3` must be justified from the
same public prize-exchange logic, not from the erroneous first contract. All
other mechanism boundaries remain unchanged.

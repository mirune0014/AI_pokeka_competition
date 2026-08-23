# Archaludon Alakazam Lillie survival v1

## Base
- source branch: `codex/archaludon-replay-repair-v1-clean-origin`
- source HEAD: `0277c3bd2c87638238791f0ce1db35a0415ddf3b`
- source candidate: `archaludon/candidates/archaludon_historical_silver_replay_repair_v1/`
- new branch: `codex/archaludon-alakazam-lillie-survival-v1`
- new candidate: `archaludon/candidates/archaludon_historical_silver_replay_repair_alakazam_lillie_v1/`

## Problem
- Episode 91850626
- opponent Active Alakazam
- opponent handCount 15
- own lone Active Duraludon HP230
- next-turn minimum Powerful Hand 320
- previous route: Cape -> Boss Kadabra -> Raging Hammer -> board out
- intended route: Cape -> Lillie's Determination

## Changed tracked files
- candidate `_historical_silver_parent.py`: exact Alakazam Powerful Hand readiness and lone-Active Lillie survival gate; Lillie/Boss score branches.
- candidate `main.py`, `deck.csv`, `requirements.txt`, and `cg/`: copied from the source candidate without behavioral edits.
- implementation `tests/`: four source focused-test files copied with the new candidate path, plus `test_alakazam_lillie_survival.py` (15 tests).

## Exact trigger
- Active Alakazam id 743
- Powerful Hand id 1072 payable from the visible Psychic energy state
- opponent handCount + 1 floor
- own Bench empty
- opponent Bench non-empty
- own remaining Prize 4-6
- current attack cannot KO Active Alakazam
- Lillie legal and draw pool sufficient

## Priority
- items / backup / evolution remain before Lillie
- Hero's Cape 8000 remains before Lillie 7000
- nonlethal Boss is suppressed
- non-KO attack and End remain after Lillie

## Deck and identity checks
- main.py source/new SHA-256: `506E1A75062EE22BEE550C303C74D44A141EF6F8A6AD0DB6AEADBD9211085CB6` (identical)
- deck.csv source/new SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` (identical)
- requirements.txt source/new SHA-256: `9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47` (identical)
- new parent SHA-256: `643369455FCE3BF417041E9FABB8CFFAB51DA01D01B29B4FF9F3976B0CBA627D`

## Episode 91850626 fixture
- opponent hand: 15
- minimum Powerful Hand: 320 damage
- own Active HP: 230
- previous selected action: Cape -> Boss Kadabra -> Raging Hammer
- new selected action: Lillie's Determination

## Priority checks
- Pokégear before Lillie: PASS
- Hero's Cape before Lillie: PASS
- backup Duraludon before Lillie: PASS
- evolution before Lillie: PASS
- Lillie before nonlethal Boss: PASS
- Lillie before non-KO attack: PASS
- Lillie before End: PASS

## Negative gates
- current Alakazam KO: PASS (no trigger)
- own Bench present: PASS (no trigger)
- floor below HP: PASS (no trigger)
- Alakazam Bench only: PASS (no trigger)
- attack unpayable: PASS (no trigger)
- status: PASS for asleep / paralyzed / confused (no trigger)
- Prize <= 3: PASS (no trigger)
- Lillie unusable: PASS (legal fallback action)

## Verification
- py_compile: PASS
- focused unittest: `56/56 PASS`
- git diff --check: PASS
- archaludon/final diff: none
- tracked cg.dll: no (`cg.dll` remains ignored)
- paired evaluation: not executed in this implementation task
- package: not created
- Kaggle: not accessed
- Push: none

## Execution status
- COMPLETE

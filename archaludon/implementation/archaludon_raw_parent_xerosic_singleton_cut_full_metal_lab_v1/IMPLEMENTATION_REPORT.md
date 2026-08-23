# Archaludon Xerosic singleton / Full Metal Lab cut

## Scope

This branch contains one deck-slot challenger for field evaluation. The
accepted Archaludon policy and runtime are byte-identical; no resolver,
wrapper, scorer, engine, or matchup rule was changed.

- Candidate: `archaludon_raw_parent_xerosic_singleton_cut_full_metal_lab_v1`
- Parent policy SHA-256: `506E1A75062EE22BEE550C303C74D44A141EF6F8A6AD0DB6AEADBD9211085CB6`
- Runtime SHA-256: `643369455FCE3BF417041E9FABB8CFFAB51DA01D01B29B4FF9F3976B0CBA627D`
- Candidate deck SHA-256: `674C28C6C0742F2222408F1788C2700BBA55A6B655C8636F90FC6CECFD0B4E39`

The only deck change is a singleton substitution:

| Card | Parent | Candidate |
| --- | ---: | ---: |
| Full Metal Lab (1244) | 3 | 2 |
| Xerosic Machinations (1197) | 0 | 1 |

No other card count changed.

## Local confirmation

The immutable final confirmation run covered the same global 1,280-game
schedule for accepted control, Boss challenger, and this candidate, plus a
320-game Alakazam-targeted schedule. The candidate result was:

- global delta: `+11` wins (`938` candidate vs `927` control)
- targeted Alakazam delta: `+8`
- seat deltas: `+15 / -4`
- worst non-Alakazam delta: `-4`
- runtime faults, action errors, and duplicate mismatches: `0`
- bootstrap interval: included zero

This is promising evidence, not formal adoption evidence. The package gate
passed with package-gate hash
`E6EC89A4F1C16FA00775FAB9B5F8FB693EA5B002C2A6A2A3C055C99AD9C15969`:
compile/import, loader-last callable, legal 60-card deck, one Hero Cape,
one ACE SPEC, and both-seat smoke all passed.

## Status

`FIELD_PROBE_READY_NOT_ACCEPTED`. The old Silver-preservation gate remains
rejected; no accepted policy or final deck was replaced. The next permitted
step is an alternating live field probe against the formal accepted control,
subject to the current Kaggle quota policy. No Kaggle submission is made by
this commit.

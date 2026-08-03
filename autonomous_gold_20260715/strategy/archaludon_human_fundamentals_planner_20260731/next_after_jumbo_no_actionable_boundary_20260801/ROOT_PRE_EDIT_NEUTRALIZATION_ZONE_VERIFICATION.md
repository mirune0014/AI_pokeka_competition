# Root verification — Neutralization Zone pre-edit census

## Frozen inputs and execution

- Strategy SHA-256:
  `7E4863D0B02F5F1B379D0EFEAF5D92F9D02484815E05A589BAF3B26106E5AD7C`
- Runner SHA-256:
  `02D7903428EED9410CC444801A855CDBF5F17803A39596C384302EE7E50034CC`
- Exact parent SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`

The deterministic runner verified that the destination did not exist, then
made the fixed pass with bundled Python and bytecode disabled.  It exited `1`
only after closing all three output files: the final stdout `print` tried to
encode a Pokemon name through the Windows CP932 console and raised
`UnicodeEncodeError`.  This is a reporting defect, not an interrupted census.

Frozen output evidence:

- `gap_identity_rows.csv`: 423 data rows, SHA-256
  `9C96B147F9C341E409602B004E76996ABA2D9948864FA474C87C8AB4AE8D7FE7`;
- `opportunity_rows.csv`: 40 data rows, SHA-256
  `FD8E4CC64FE295C77B7B66AA89EBC277BE8FE506BBB7A1943032A612DF25A0B6`;
- `summary.json`: SHA-256
  `C1D2511A57B707DF89901F56E37AE359D4335A946E167553E8540DB93A05A5F7`.

All files parse to EOF.  Every emitted row retains replay, seat, step, turn,
snapshot, and replay-hash provenance.  The independent Sol-Ultra audit is
`NEUTRALIZATION_ZONE_NUMERICAL_AUDIT_SOL_ULTRA.md`, SHA-256
`0335738B6EF85238143E834BFF62BFA66ABEE1072DFD413742E913FCC7941C39`.

## Root recomputation

Root independently parsed both CSVs rather than accepting the generated
summary.

- gap rows: `423`;
- `RETURN_UNKNOWN`: `225`;
- `UNSUPPORTED_STADIUM`: `128`;
- `UNSUPPORTED_SKILL_TOOL`: `70`;
- opportunity rows and unique opportunity turns: `40 / 40`;
- hard plan-ranking differences: `0`;
- predicted first-action differences: `0`;
- affected certificate keys: `10`, over only `6` turns and `3` replays;
- affected seats: both;
- blocked source identities: only card `190` Archaludon ex;
- protected target identities: only cards `741` Abra and `743` Kadabra;
- prevented ex/Mega-ex examples: `10`;
- positive non-ex-damage examples: `73`;
- Rule-Box-target-unprotected examples: `0`.

The summary's six public-return examples are optimistic: their recorded scope
is `CURRENT_OR_RETURN`, not an explicit `RETURN`.  Collapsing scope duplicates
also reduces ten affected keys to six.  Both corrections make coverage weaker.

The corpus and parent integrity values are exact: `207` replays, `209` target
seats, `25,880` calls and unique raw keys, zero manifest mismatch, duplicate
raw key, or invalid parent action.

## Exact unsupported-Stadium partition

| Stadium | ID | rows |
|---|---:|---:|
| Spikemuth Gym | 1259 | 60 |
| Neutralization Zone | 1247 | 36 |
| Team Rocket's Factory | 1257 | 17 |
| Gravity Mountain | 1252 | 6 |
| Nighttime Mine | 1266 | 5 |
| Team Rocket's Watchtower | 1256 | 2 |
| Levincia | 1254 | 1 |
| Risky Ruins | 1260 | 1 |

Neutralization Zone metadata is exact: card and skill ID `1247`, exact name,
one skill, and normalized text SHA-256
`CF3FB44117E74C1FC5AC792A4721CD1EA345A1CAA0A861931A59A46A842FD877`.

## Next-gap facts, not a selection

Within the 70 unsupported-skill/tool rows, exact per-row presence counts begin
with:

- Mega Kangaskhan ex / Run Errand: `25`;
- Cornerstone Mask Ogerpon ex / Cornerstone Stance: `20`;
- Chandelure / Alluring Light: `9`;
- Fezandipiti ex / Flip the Script: `9`;
- Kadabra / Psychic Draw: `6`;
- Team Rocket's Spidops / Charging Up: `6`;
- Lunatone / Lunar Cycle: `5`;
- Hariyama / Heave-Ho Catcher: `5`;
- Team Rocket's Mewtwo ex / Power Saver: `4`.

These are row-presence counts and may overlap; they are not causal gains.
Run Errand is a public draw action but does not itself supply an exact combat
transition.  Cornerstone Stance and Power Saver directly change visible
damage or attack readiness and therefore remain plausible subjects for a new,
separately frozen hypothesis.

## Decision

`STOP__INSUFFICIENT_NATURAL_SEMANTIC_COVERAGE`

Neutralization Zone fails the precommitted affected-certificate, hard-plan,
predicted-action, example-class, and identity-diversity gates.  No source
candidate, package, fixed schedule, or Kaggle submission is authorized for
this hypothesis.  Thresholds are not relaxed.


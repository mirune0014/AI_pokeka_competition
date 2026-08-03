# Root verification — pre-edit Jumbo Ice Cream census

## Frozen evidence

- Parent:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Manifest:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Strategy:
  `53E50964F76F2CB16A6F67D1276D93DEE86991CFB07C1464D6EC9E1B3F3DEADF`
- Runner:
  `3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B`
- CSV:
  `093573F0C9D5E47EF6EA5E8277E6DD137078D06C07FC20BF8241606B14CCB1D9`
- Summary:
  `BB38450572DD285FEDAD3B79616CDEE22A0A32AC626111038605CE2239EF085C`
- Independent Sol-Ultra audit:
  `1AD2E6036CCD988D478E2D6138E323D41712978FF5E564B158FAB6FEAF52C48D`

## Integrity and root recomputation

The frozen run has 207 replays, 209 target seats, 25,880 parent calls, zero
invalid parent actions, zero manifest mismatches, and 483 unique opportunity
rows.  It reproduces 92 physical Jumbo plays over 82 turns in both seats.

Root's initial any-callback recomputation matched the runner summary, but that
summary did not apply the frozen earliest-independent-callback rule.  The
independent audit corrected this without changing raw evidence:

| Scope | Any-callback union | Earliest independent callback |
|---|---:|---:|
| Strict two-world turns | 20 | 19 |
| Actionable turns | 1 | 0 |
| Predicted differences | 1 | 0 |
| PLAY_ICE | 1 | 0 |
| HOLD_ICE | 0 | 0 |

The one later raw PLAY belonged to a turn whose earlier independent callback
was EQUAL.  It is not independent gate evidence.

The observed Raging Hammer KO-preservation boundary was real: no-heal won
immediately while healing lost the KO.  The exact parent already selected
Raging Hammer there, so it creates no candidate difference.  The only later
heal-favored raw callback likewise supplies no earliest-independent gain.

## Exact-coverage diagnosis

The 423 `no_fully_rankable_plan` rejections are not a `plan_layers` coding
error:

- 225 rows have deterministic `RETURN_UNKNOWN` with five uncertified
  return/backup fields;
- 128 rows fail on an unsupported public stadium;
- 70 rows fail in the current combat oracle because of unsupported public
  skills/tools.

Unknowns were not converted to zero.  This missing semantic coverage is kept
as a separate future fundamentals defect; it cannot be used to relax this
hypothesis after observing the result.

## Decision

`STOP_BEFORE_IMPLEMENTATION__RARE_NARROW_NO_ACTIONABLE_BOUNDARY`

The frozen floors require at least 24 strict turns, 16 actionable turns, 10
predicted changes, 3 PLAY and 3 HOLD in both seats, and three examples of each
named purpose.  The contract-correct result is 19/0/0/0/0.  Do not edit a
candidate, run fixed760, package, or submit this Jumbo Ice Cream hypothesis.

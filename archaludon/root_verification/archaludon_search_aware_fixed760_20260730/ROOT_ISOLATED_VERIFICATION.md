# Root isolated verification — search-aware Active terminal

Date: 2026-07-30 JST

Rule:
`SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1`

This report verifies the isolated direct child of exact Historical-Silver. It
does not authorize a Kaggle write or make the candidate the formal parent.

## Frozen identity

- Historical-Silver `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Candidate `main.py`:
  `6B71FC078BC2F4B26B4D5509B49DAE960968D1EE71D0C805FD9F6DB9EAC0AC08`
- Shared `deck.csv`:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Parent diff:
  `AC0B2DA83966A0A3DCD78C70745D940D0CEE805663C3CE3C8818FC38A7473A45`
- Strategy contract:
  `DE30DBA76E39DC0F6FF922E24727A3A9013C266DCEAC5CC306E6581CE601FDB0`
- Pre-edit engine report:
  `50A1D576A4F0D6AFEFA27DCD1A901535A9C64AD80905B4A1A49311AE7B70BF3A`
- Worker verification:
  `AC6A8E42C58A0E4BDD39F315FF1933598F095D4EB563133B9EACDBA37CB4704F`

Root recomputed each listed hash. Only candidate `main.py` differs from the
parent runtime; the other 11 runtime files are byte-identical.

## Root rerun

Root independently reran:

- the complete focused exact-engine test;
- the 261-replay stateful shadow;
- compile/import/deck request and structural validation;
- cache and runtime inventory.

Results:

- eight successful terminal transactions and 80 owned callbacks across both
  logical seats;
- identity, mirror, serial remap, option reversal, equivalent duplicates, and
  repeated-callback determinism pass;
- two both-seat all-in-Prize search misses clear and delegate to the exact
  parent from the actual irreversible state;
- 21 synthetic initial negatives, 13 frozen replay negatives, and seven
  rollback/retry/reset cases pass;
- action errors, invalid actions, exceptions, nondeterminism, stale
  transactions, and max-step hits are all zero in represented focused fields;
- compile, import, deck request, loader-last, and loader-only pass;
- exact 60 cards, one ACE SPEC (`1159`), 12 runtime files, zero cache entries.

The public count-only access certificate is `164/165 = 0.993939...`, above
the frozen `0.99` threshold. The policy does not inspect facedown Prize
identities.

## Replay shadow

Frozen shadow:

- 261 replay files;
- 14,464 correct-seat callbacks;
- 217 historical files / 11,967 callbacks;
- 44 current Hero files / 2,497 callbacks;
- exact seat coverage: historical `113/104`, current `21/23`.

There is exactly one semantic action difference:

- episode `88827776`, callback row `134`, seat `1`;
- parent: Boss's Orders `1182#101`;
- candidate: Ultra Ball `1121#81`.

The full engine route is:

`Ultra Ball -> safe Cinderace/Boss discard -> Archaludon ex search -> evolve
the established Active Duraludon -> Assemble Alloy two Basic Metal -> Metal
Defender 220 -> take the remaining three Prizes`.

There are zero later or certificate-external differences, action errors,
exceptions, or stale transactions. The two newest losses, `88831792` seat 0
and `88835861` seat 1, have zero candidate-parent differences and are
separated into unrelated future memos.

## Fixed-760 execution

The first execution specification was mechanically ambiguous about the
checked runner's required `NAME=PATH` opponent argument. The runner stopped
with exit `2` before producing a paired row. Root preserved that attempt and
froze corrected R1 specification:

- R1 spec:
  `83A26F42B264E63C8D58B923C7B50875F0C3EDD8B530360D12164A2988029BDC`
- complete raw/execution hash manifest:
  `E0E07CBEBD039309DF1EAA8F68F50313B77B25339C9E89364349D2DC359027EF`

All eight corrected commands exited zero. Root independently recomputed:

- 760 rows and 760 unique `(panel, opponent, seat, seed)` keys;
- exact expected seed schedules and both seats;
- zero stored-versus-recomputed win mismatch;
- zero nonbinary row, max-step row, failed inner command, invalid runner
  report, or duplicate mismatch;
- baseline `478/760`, candidate `478/760`;
- historical `100/200`, adjacent `378/560`;
- seat 0 `243/380`, seat 1 `235/380`;
- Kangaskhan/Crustle `28/80`;
- paired gains `0`, regressions `0`.

Root recomputation:

- script SHA:
  `F62F8B9E31B8B88390C1DAB74E1F033B771C4FA6E234DA5B4150917740C7BE44`
- output SHA:
  `BA5D8375EFA3DDF2770F270D54ABC968FBA6324EEB3755977E2E0EF5B3A9274A`

Independent Sol-Ultra numerical audit:

- report:
  `0B1AAAEC3F934F8F0BF53A3C9FDB41BEDA3F9071A79896A1A0C70AEF34E08735`
- machine result:
  `EB1D54FEE6D54DF2A80772B799DB465EE21C06AA77E96C94FAEEA6C02CC26C67`
- audit hash manifest:
  `2F5EF99B4A8860E893C78F6BDCA96978598587F582A126C68723454E466A5E80`

The independent audit agrees with every Root total and finds all 760
candidate traces byte-identical to baseline. This is a destructive-safety
pass on the fixed matrix and no strength evidence. The physical per-panel
CSVs lack a `panel` column; the audit reproducibly derives it from the
manifest-committed parent directory and verifies every row's opponent.
Cumulative evaluation must write `panel` physically.

## Root conclusion before final rule judgment

The isolated rule passes represented destructive checks. It is intentionally
rare: the fixed matrix never emits the overlay, while the frozen live source
state completes the exact same-turn terminal in both logical seats. Neutral
fixed results receive no strength credit, but local neutrality alone is not a
rejection condition under the user's practical probe policy.

The rule remains conditional on the final Sol-Ultra rule-level judgment and,
if accepted, all cumulative precedence, collision, ownership, telemetry,
package, and live gates.


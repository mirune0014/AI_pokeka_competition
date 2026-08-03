# H3 v2 exploratory prewrite decision

Checked at 2026-07-29 11:55 JST.

## Candidate identity

Candidate:

`archaludon_certified_lone_cinderace_ultra_ball_turbo_flare_line_formation_explorer_veto_v2`

This is a direct, unstacked sibling of exact historical-Silver Archaludon.
H1, H2, H4, opponent identity, episode identity, and hidden card contents are
not implementation inputs.

- candidate source SHA-256:
  `9D5A2A87770FE4CC2F77599E0FDF044ECC61C3F20BA335A02E1E2650BE5036B0`
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- clean archive SHA-256:
  `5E04C79CC714144522D238E05A7C14AA3A4086E3C0258F997953F8D172598E15`
- package manifest SHA-256:
  `EA11B89DF23562F433360F5F151EF2E4A240FA4A822126E7FBD2A06522844214`
- package validation SHA-256:
  `52A5293683AF724204CD590B5CB9F9800080C1B97DA679BEA69C6653B7E17B59`

The archive contains 12 regular files, no cache artifacts, one last callable
`agent`, a legal 60-card deck with exactly one ACE SPEC, and passed both-seat
packaged smoke plus an exact duplicate control.

## Isolated hypothesis

At a lone-Cinderace board where Turbo Flare is nonterminal and no legal
Explorer's Guidance line is available, certify a count-only high-confidence
Ultra Ball route without inspecting hidden deck or Prize identities:

`Ultra Ball -> safe two-card discard -> Duraludon -> Bench -> Turbo Flare ->
maximum deterministic Basic Metal to the reserved Duraludon`.

The rule prevents an avoidable no-Pokémon loss by forming one successor before
the nonterminal attack. If Explorer is currently legal, v2 delegates the exact
parent action and does not preempt the better resource line.

Primary target: lone-Cinderace setup survival and next-attacker formation.
Retention targets: historical-Silver mirror and the complete adjacent
anti-overfitting population in both seats.

## Local evidence

- focused contract tests: `12/12`
- exact engine: six complete transactions, both seats, 54 callbacks, zero
  faults
- full replay shadow: 196 replays and 10,856 callbacks
- shadow differences: exactly one intended positive
- trigger-external differences: `0`
- fixed schedule rows / unique keys: `760 / 760`
- exact parent/candidate schedule equality: pass
- parent / candidate wins: `478 / 478`
- gains / regressions: `0 / 0`
- seat 0: `243 / 243`
- seat 1: `235 / 235`
- every panel, opponent, and opponent-seat floor: retained
- duplicate summaries and traces: `760 / 760`
- command, start, action, exception, and maximum-step faults: `0`

Important evidence hashes:

- Root recomputation:
  `F791AFD392823790697256168BCD778387AA0150489D2C8A36DF08B07E364599`
- Root changed-trace audit:
  `DCD5BFEAF7D85E9A803B5DD4AF02C5B9B6A87449C93B1C4AE52F714D935A3A95`
- independent numerical audit:
  `8A4EBFE159E341E07A54995857C644CA70BF74AB4FF837244E2224FD9B7FB69F`
- Root numerical reconciliation:
  `59C2E0FEBF67773D3BCD445ADDC21EAE98F2B2AB7A7D2DFAD458AF4FD359B869`
- final Sol-Ultra judgment:
  `B72051DD59A1E6C25794F6899DF735B39D79B6C128601FE09BCCC26B581F55FD`

Final judgment:

`ACCEPT_EXPLORATORY_AFTER_H2_MATURITY`.

The neutral fixed result is broad safety evidence, not strength evidence.

## H2 three-hour maturity review

Current live submission `55067020` was submitted at 08:51:55 JST. The
authenticated prewrite refresh occurred after its 11:51:55 JST maturity
boundary.

- status: `COMPLETE`
- CLI/API score: approximately `769.8`
- episode-service score: `769.8074705053797`
- public games: `41`
- public record: `23-17-1`
- validation games: `1`
- final genuinely new episode since the 40-public checkpoint:
  `88722418`, a loss
- H2-parent differences in that game: `0`

Complete 207-replay correct-seat shadow:

- callbacks: `11,477`
- H2-parent differences: `2`, both confined to the old certified historical
  positive `88017509`
- new public H2-owned callbacks: `0`
- trigger-external differences: `0`
- action errors / exceptions: `0 / 0`

Maturity evidence:

- episode CSV SHA-256:
  `1125847281F1B08278C63C0236840618C288E1815AE763FD857C44D6149AA8BD`
- episode JSON SHA-256:
  `EDEF82BFEDE4650CC1EC303F6471008BFD08BA58F14D238112D402261D1545A4`
- shadow summary SHA-256:
  `97EA5A0E1AED82A554C5D7B91CA863D8860485F9AF0858BA5422A9FF7CDE3C5A`
- shadow per-file SHA-256:
  `938E4E5753354794669A5ACF88F9C21648A90B13F2E28A5FF44A65738131D35E`
- shadow differences SHA-256:
  `24B2820EE74D310079546A7EB2568693EB9DCBA7DB5B2D1A71A2AF1520D11917`
- shadow source manifest SHA-256:
  `1DC61D5E3D019618CA378E882F5DE1641206D0AEB75AE34ED044E89920530788`

No destructive H2 defect is visible, but H2 did not change any live action.
Its score is exact-parent path variance and its trajectory is not a reason to
block a separately valid H3 probe.

## Kaggle state and decision

- authenticated latest submission before write: `55067020`
- UTC-day quota before write: `0/5` used, `5/5` remaining
- current and preceding mature submissions remain below `1000`
- H4 v2 is rejected from packaging because fixed traces exposed a
  same-Prize/different-attack certificate breach; it is not part of H3

Decision: use one daily slot for exactly one H3 v2 exploratory live probe.
Do not describe the submission as a proven strength improvement. After upload,
authenticate the new submission ID/status/quota and wait approximately three
hours before replacing it unless a destructive implementation defect appears.

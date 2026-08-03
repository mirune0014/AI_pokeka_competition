# Pre-write decision: EVOLVE_ACTIVE_READY source transition v2

- Recorded: 2026-07-19 22:10 JST
- Owner and Kaggle writer: root
- Decision: submit exactly once
- Purpose: exploratory live measurement, not permanent adoption

## Frozen candidate and package

- source:
  `305A6C597609E82E8611DBF83DA8C8845E70BD5B89781988E74C720BD6B53267`;
- runtime wrapper:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- legal 60-card deck:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- clean archive:
  `packages/alakazam_evolve_active_ready_source_transition_v2_clean_20260719/submission_alakazam_evolve_active_ready_source_transition_v2_20260719.tar.gz`;
- archive bytes: `2,015,198`;
- archive SHA-256:
  `A0AE2878E1226DAA3CE6C0138A399930C592A7C19801E3BCF60F25861AA6D58C`;
- package manifest:
  `ED0E0AA79C6CC1592AC149FC5D205FD8EB93ECCFE1C54E105BC36844ABC65B4B`.

Archive membership is exact and clean. Package-local import, legal deck, one
ACE SPEC, deterministic initial request, 10/10 packaged focused tests,
current-42 shadow, and checked Historical-Silver smoke in both seats all pass.
There are zero package caches, invalid actions, or max-step hits.

## Paired justification and limits

The fixed exact comparison is exact-v3 `86/144` versus candidate `88/144`,
`3G/1R`. Exactly 17 traces change at EVOLVE_ACTIVE_READY; all 17 complete
Active evolve, ACTIVATE/YES, post-draw exact-v3 delegation and a legal
same-turn attack, versus 12/17 for exact-v3. Backup readiness is keywise
non-regressing. The effect is small and unresolved (`p=0.625`), all gains are
P0, Marnie declines by one, and Great Tusk remains `4/16`. This justifies one
measurement slot, not promotion. Exact-v3 and submission `54824578` remain
rollback anchors.

## New-replay safety gate

The 22:04 authenticated refresh added exactly two public losses, episodes
`86878728` and `86889302`. Each was downloaded exactly once and validated.
Across all 47 rurumi callbacks, exact-v3 and this frozen candidate are
identical, with zero invalid actions, no candidate latch start, and empty final
latches. The root safety report is
`88124DD49890D14567304C5520E7D5CB5B3B1440BFA7649D1B32AF27D754BBCD`.
The losses neither invalidate nor support the new rule.

## Immediate authenticated near-write refresh

At 22:10 JST, both read-only commands exited zero. Kaggle still reports
submission `54824578` as `COMPLETE` at displayed score `772.5`; the preceding
submission is complete at `714.6`. Exactly one submission is present in the
current UTC day, so quota is `1/5` used and four slots remain. No submitted
filename matches this archive.

The final episode fetch still has exactly 52 unique IDs, with no additions or
removals from the checked 22:04 set. Its CSV hash is
`33009263B21A245F984F4835064A8F24CC34DDBCFACFBE1ACA4690191271C3F4`;
JSON hash is
`37BECD68E807A0AE81EDEC815945D827A4ED5B291F4ED5C1F33172E133B219A6`.
Current and preceding mature submissions are below 1000, cadence exceeds four
hours, a valid slot remains, and no new semantic defect is known.

## Write protocol

Root will invoke exactly one Kaggle submit command with the frozen archive and
description `EVOLVE_ACTIVE_READY source transition v2 - exploratory probe;
exact 144 88 vs 86, 3G 1R`. Do not retry after an ambiguous client result
until remote submissions are refreshed. After a successful response, refresh
remote state once, record the new submission ID/status and quota use, and
monitor verified live activations. Score movement without an activation is not
causal evidence.

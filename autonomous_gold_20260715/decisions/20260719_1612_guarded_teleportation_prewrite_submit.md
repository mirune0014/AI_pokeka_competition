# Pre-write decision: Guarded Teleportation exploratory probe

- Recorded: 2026-07-19 16:12 JST
- Owner and Kaggle writer: root
- Decision: submit exactly once
- Purpose: exploratory live measurement, not permanent adoption

## Candidate and package

- source:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`;
- runtime wrapper:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- legal 60-card deck:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- clean archive:
  `packages/alakazam_guarded_teleportation_attack_continuity_v1_clean_20260719/submission_alakazam_guarded_teleportation_attack_continuity_v1_20260719.tar.gz`;
- archive bytes: `2,013,147`;
- archive SHA-256:
  `2C6552D31CE781084E71E460A786A1DD09CD3CABD8EEFAAA3B82A6CB97FD69E0`;
- package manifest:
  `D3AECCC858B2EE0EFA991FC924AA8D47B6DD66CC9E38312C73F7816DFE11BA19`.

Clean validation, 14/14 packaged-focused tests, the complete checked
Teleportation-to-recorded-switch transaction, and packaged P0/P1 smoke all
pass. Archive traversal, absolute, cache and compiled-Python entries are zero.

## Paired justification

The exact 144-key comparison is exact-v3 `86/144` versus candidate `89/144`,
`3G/0R`. P0 improves `45 -> 48`; P1 is unchanged; known improves `44 -> 47`;
fresh is unchanged; no opponent bucket declines. Exactly six traces change,
all at intended finalized manual-RETREAT versus Teleportation-Attack choices,
and every recorded switch transaction completes without semantic error.

The old frozen permanent-promotion gate failed Silver/fresh/P1/Kangaskhan
coverage. Those scopes did not regress. Under the user's current practical
live-probe preference, they are uncertainty conditions, not known-broken
behavior. Exact-v3 remains rollback and this upload is not adopted on score
alone.

## New replay gate

The 15:59 authenticated refresh added exactly episode `86836319`. Root
re-executed exact-v3 and the candidate at all 94 rurumi callbacks: zero action
differences, zero candidate-specific guarded starts, empty final latch and no
semantic failure. The ordinary Teleportation at step 46 is selected identically
by both policies. Root safety report:
`analysis/guarded_teleport_prewrite_86836319_20260719/ROOT_PREWRITE_SAFETY_VERIFICATION.md`.

## Immediate authenticated refresh

Final read-only refresh:
`live/54802782/refresh_20260719_1610_prewrite`.

- both fetch commands: exit `0`;
- incumbent `54802782`: `SubmissionStatus.COMPLETE`, displayed score `730.3`;
- UTC-day quota: `0/5` used, `5` remaining;
- prior/current public episode IDs: `62/62` unique;
- added IDs: `[]`; removed IDs: `[]`; downloads: `[]`;
- authenticated submissions CSV:
  `6C6D630FA0DC159AB5CDCDE74B5087475BD0FFC3A85116C057A9CD6BCAF92397`;
- current episode CSV:
  `45B78717B074B26E3A22153C760B9A5D687FC6313C708E6F13D4286997A4E3D8`;
- command ledger:
  `30742B40F34E0C9E8164013352CC75943D277C0135CF97621C054EF17AD31E54`.

No authenticated submission row matches the guarded-Teleportation filename,
source hash, or archive hash. The incumbent is complete and below 1000. The
last submission is more than one four-hour cadence interval old.

## Write protocol

Root will invoke one Kaggle submission command with the frozen archive and an
ASCII description. Do not retry after any ambiguous client error until remote
submissions are refreshed. After a successful client response, refresh remote
state once, record the new submission ID/status, decrement quota from 5 to 4,
and begin activation-aware live monitoring. Games without a guarded activation
and score movement by itself are not causal evidence.

# Root cumulative-v2 shadow over the ten new Hero episodes

Decision:
`PASS_PARENT_IDENTICAL_DORMANT`

This is a pre-submit safety refresh for the already frozen eight-rule
cumulative candidate. It is not strength evidence.

## Frozen inputs

- cumulative candidate:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
- exact historical-Silver:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- old episode CSV:
  `5B9176809A98FA2B8AE258DCECEBE97A56AD9DBA1E9BB3F51270EEEB86CCF682`
- refreshed episode CSV:
  `D63E9921C8CADC926F05ACA0E6F662E8A1EA4181BC938FCD8C9A04D51EED9081`
- checked union-shadow runner:
  `9912B36D166FED9314CDCF4778C2950950E32F13D764E1ADA2545D24688AC9E9`
- bounded new-set wrapper:
  `E4F827E1260C38891E1044A29A91BEAD6E604B87F2E234704A10D81B48D08AC9`

The wrapper verifies the exact ten-ID set difference, derives the tested seat
from the replay's `TeamNames`, verifies the target reward, hashes every replay,
and then delegates callback semantics and collision checks to the frozen
union-shadow runner.

## Recomputed result

- source replays: 10
- correct-seat callbacks: 601
- seat files: nine seat 0, one seat 1
- parent/candidate action differences: 0
- eligible-rule collision size: zero on all 601 callbacks
- attribution: exact historical-Silver on all 601 callbacks
- transaction starts/clears/rollbacks: `0/0/0`
- action errors, outer/component exceptions, emergency fallbacks,
  unknown-collision rollbacks, dual/stale owners, owner switches,
  retry-parent errors, and isolated-component mismatches: all zero

Summary SHA-256:
`0AC27BC3F8A23BBA4DFEB0112D5E685B9429119EC6081CBEE81AFEB9CE31E084`.

The absence of a trigger is neutral. All eight valid rules remain in the
cumulative package, and this new block adds no safety reason to delay its
single authorized live probe.


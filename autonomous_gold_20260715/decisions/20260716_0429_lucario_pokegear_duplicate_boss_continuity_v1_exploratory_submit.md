# 2026-07-16 04:29 JST - Lucario Pokegear continuity exploratory submission

## Decision

Use the fourth `2026-07-15` UTC submission slot for the exact deterministic
candidate
`historical_silver_lucario_pokegear_duplicate_boss_continuity_v1`, as a
**user-authorized live exploratory probe**.

This decision does not reverse the frozen strength judgment and does not call
the candidate a proven improvement.  The original evaluation correctly
rejected it for promotion because its small aggregate gain did not meet the
required effect, confidence, fresh-seed, or variant floors.  After that result
was explained, the user explicitly requested live submission before the 09:00
JST quota reset so that future losses can provide deck-theory, public-state,
resource, and prize-sequencing evidence.

## Current live replacement state

- Outgoing submission: `54710399`.
- API/CLI status: `COMPLETE`.
- Displayed score: `752.6`; exact terminal score:
  `752.6612472233784`.
- Public record: `31-31`.
- Exact new sequence at the pre-package checkpoint: `L,W,L`, net
  `-6.9236607829568584`; terminal result `L`.
- Recovery label: no.
- UTC `2026-07-15` quota evidence: API `3/5`, CLI `3/5`.
- Root refresh verification SHA256:
  `7380C85B28E42CD4CB784941571B85228FD5FD64C30DF243BE0577670BFADA63`.

The current and preceding mature submissions remain below 1000, the current
submission is weak and not recovering, and two slots remain.  The user has
accepted the exploratory uncertainty.  A final read-only Kaggle refresh is
still required immediately before the write.

## Exact hypothesis and public-state rule

Against detected Lucario, while resolving Pokegear after the turn's Supporter
has already been played:

- Boss's Orders is already in hand;
- no Explorer's Guidance or Lillie's Determination is already in hand; and
- Pokegear offers both another Boss and at least one draw Supporter.

Keep the held Boss and take the draw Supporter for next-turn hand continuity;
prefer Explorer over Lillie if both are offered.  All other Pokegear, Supporter,
Boss, search, matchup, and deck behavior remains unchanged.

The target matchup is the repeated Mega Lucario family.  Replays are used to
identify the public continuity mechanism and later diagnose failures, not as
action labels or opponent-policy proxies.

## Frozen paired evidence

- Candidate `main.py` SHA256:
  `A69E2C5915355D402B314AA4BC66D933B68A5C0E2976A86905238A97EB6093AE`.
- Unchanged deck SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Frozen evaluation specification SHA256:
  `57CA609E3A2B0911E32770D942BC42F65AA26B00E8F2808C4E4CDF229417DB1D`.
- Execution log SHA256:
  `9D07A88A6088491DB16BC7248E06E32DD7ECF7434673E40FFCF20A24495041C8`.
- Sol-Ultra numerical evaluation SHA256:
  `5E8421FBDE25F2A64D0B0EF0CAC93E8AF8EBAEB573F798E010ADD3A4F4EDBF1A`.
- Root numerical verification SHA256:
  `8D6E9A89C0F4C0106A130250561AB432608BB9E6B6A6ED423AB051769D6F3919`.

Frozen schedule and result facts:

- reference: parent `450/480`, candidate `453/480`, delta `+3`, gains `3`,
  regressions `0`; confidence interval crosses zero;
- fresh: parent `890/960`, candidate `890/960`, delta `0`, gains `0`,
  regressions `0`;
- combined: parent `1340/1440`, candidate `1343/1440`, delta `+3`, gains `3`,
  regressions `0`;
- exact paired keys: `1440`; raw execution rows: `4320`; comparator rows:
  `1440`; trace rows/files: `2880`;
- schedule equality, duplicate controls, action errors, max-step hits, invalid
  results, and frozen-hash mismatches: all zero;
- unique rule-hit games: `41`; qualifying selections: `42`; completed
  next-turn Supporter chains: `25`; off-predicate divergences: zero.

The evidence supports runtime safety and absence of observed paired
regressions.  It does not support a promotion claim; live feedback is the sole
reason for consuming the exploratory slot.

## Exact package

- Archive:
  `autonomous_gold_20260715/packages/historical_silver_lucario_pokegear_duplicate_boss_continuity_v1_20260716/submission_archaludon_lucario_pokegear_continuity_v1_20260716.tar.gz`.
- Archive SHA256:
  `BC06807015A1E185D94A016D968DCA7769ABFE1C0D44B43F66A5286E0A4545B1`.
- Package manifest SHA256:
  `FFD339B0B44928284182B4541023D7548B09480AC4449A0C70E6C55E3A7A7D9D`.
- Archive entries / extracted files: `13 / 12`.
- Unsafe/cache entries and source-identity mismatches: zero.
- Corrected isolated import exit: `0`; deck length: `60`.
- Package-runtime smoke: four games across both seats, four valid results,
  zero action errors, zero max-step hits.

The first isolated import invocation exited `1` because the check was run from
the repository directory and `read_deck_csv()` correctly could not find its
relative runtime deck.  The archive was not changed.  The corrected check ran
from the extracted runtime directory and passed; this harness discrepancy is
recorded explicitly.

## Planned Kaggle write

- File:
  `submission_archaludon_lucario_pokegear_continuity_v1_20260716.tar.gz`.
- Description:
  `Exploratory Lucario Pokegear continuity v1; +3/1440, regressions 0; live probe`.
- Expected UTC-day slot after acceptance: `4/5`.

Only root may perform and verify the external write.  Submission ID, upload
exit, status, post-write quota, and validation evidence will be appended after
the operation.

## Kaggle write result

- Upload started from the exact package directory at `2026-07-16 04:35:43 JST`
  (`2026-07-15 19:35:43 UTC`).
- The CLI transferred all `1.90 MiB`, then exited `1` only while printing the
  server response because the Windows `cp932` output codec could not encode
  `é`.  No retry was made.
- A UTF-8 CLI listing independently confirmed exactly one new row with the
  bound filename and description, status `PENDING`.
- The authenticated Kaggle API independently confirmed submission ID
  `54738887`, archive bytes `1993992`, the exact filename, description,
  submitter/team, and timestamp.
- Accepted UTC-day slot: `4/5`; one slot remains before the 09:00 JST reset.
- Initial score: unavailable while pending.

The nonzero upload-process exit is therefore a response-rendering error after
successful server acceptance, not an upload failure.  Resubmission would have
created a duplicate and was deliberately avoided.  Validation and the first
public episodes will be monitored under `autonomous_gold_20260715/live/54738887`.

## Validation result

- Submission `54738887` reached `COMPLETE` with an empty error description.
- Initial displayed score: `600.0`.
- Validation episode: `86159432`, `COMPLETED`, reward `1/-1`, both agents the
  same submitted team/ID.
- Replay terminal statuses: `DONE/DONE`; literal action-error indicators: zero.
- Both extracted ordered 60-card lists exactly match the candidate deck.
- Validation replay SHA256:
  `54012653CA8831895A796FFAF08EF859F67ECF69DF7626530443266408388B48`.
- Root validation record:
  `autonomous_gold_20260715/live/54738887/validation_20260716_0438/ROOT_VALIDATION.md`.

This establishes successful execution and exact deck deployment.  The
validation self-play and its `600.0` baseline do not establish live strength.
The exploratory learning phase begins with genuinely new public episodes on
submission `54738887`; no public result was available at this checkpoint.

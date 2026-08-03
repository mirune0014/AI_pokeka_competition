# Final strategy judgment: certified three-prize pre-KO setup transaction v2

## Verdict

**REJECT** for adoption, packaging, and live Kaggle submission. Preserve the
exact submitted parent as the executable baseline. Do not run the precommitted
Historical-Silver plus Mega-Lucario extension as an adoption-rescue experiment:
the exact candidate has already failed two immutable compact-72 strength floors,
and an extension cannot change either result.

This is a final rule-level judgment, not a claim that the uninstrumented outer
mechanism was disproved. Mechanism coverage remains failed/unproved.

## Immutable inputs checked

- Exact parent source:
  `CB52F1737417EAEEAEF226CFF79ABD4FA58119E3F2AF1D448DFBE5D68722E213`.
- Exact candidate source:
  `723A6B2E5F391D05F69B762CFB4595F45D210EA3A9C14BF3EF84DACFB0DA215E`.
- Frozen behavioral contract:
  `autonomous_gold_20260715/strategy/refine_three_prize_preko_setup_20260720/STRATEGY_SELECTION.md`,
  SHA-256 `2EFAF12BD3DB7A39E06EA3AFFCF45F083C3DE166B06F5382CC97B3CDF6705B1D`.
- Frozen compact comparison:
  `autonomous_gold_20260715/evaluations/alakazam_certified_three_prize_pre_ko_setup_transaction_v2/compact72_20260720/COMPACT72_FREEZE.md`,
  SHA-256 `59CA9A7DE06476FB80B5FA0D5E270963B8E97E5FE7568E2CE4A6717A255280B5`.
- Root implementation audit:
  SHA-256 `4FFD63E3095703B296C03F17B255BB7A4658D842CAC145DDBBBE024A2F516459`.
- Independent qualitative audit, verdict PASS:
  SHA-256 `710EA63A9E28B15D035B0F87D6726272B4E06B0CDA0B702CD497955E6432CC12`.
- Execution completion and command ledger:
  SHA-256 `953A0A2DAD1EEF68319B471E14099C8DD5D33E6FBAF6883493D318AA2F8A36AC`
  and `351695849A443D2234C2DA59B5CD989404EB7ECF0E53F16A0A2A336C609B3956`.
- Independent numerical audit and machine result, verdict FAIL:
  SHA-256 `159525D48EC2F1AD2B64359B5DEB7C7521B4B9D27DA06B1A254695C4F9943AB7`
  and `0FBF7D7F17891E9031A27CCDBA8C9BCEC9EB6AD0051289917EF7921E0D588996`.
- Root recomputation:
  SHA-256 `9874CF65BB18055FD1AF21BB6C5FE422F04EBA88E4EAA3C2E59717AF3AB76331`.
- Exact paired rows and first-action differences:
  SHA-256 `7A60BF7A1F91ABBDC3AB647E0AB1678958940ADD9CB6E8894F7EE1EA415049D3`
  and `736BBE40830111663C0F6752E86D7DEDACBC64C5D0A7AB4404A39F230F63D403`.

The judge independently regrouped the 72 exact paired CSV rows: there are 72
unique schedule keys, parent and candidate are both 38/72, seats are 20/36 and
18/36, Historical-Silver is 3/8, gains are 0, regressions are 0, and all 72
candidate duplicate controls match in summary, trace bytes, and decision count.

## Gate disposition

| Frozen gate | Evidence | Result |
| --- | --- | --- |
| Execution validity | 216/216 exits zero; 72 unique schedules; zero action errors, max-step hits, raw mismatches, or duplicate mismatches | PASS |
| Candidate at least 40/72 | 38/72, identical to parent | **FAIL** |
| Zero paired regressions | 0 gains and 0 regressions | PASS, retention only |
| Historical-Silver at least 4/8 | 3/8, identical to parent | **FAIL** |
| Historical-Silver no seat regression | p0 1->1; p1 2->2 | PASS, retention only |
| Two full-engine mechanisms spanning both seats and setup plus guard | 0 certified setup routes and 0 independently proved guards; no stage/certificate telemetry | **FAIL** |

Even under the more permissive reading that the four `attackId=1072` first
differences are immediate guards, the mechanism gate still fails because no
full-engine setup transaction was observed. All four outcomes were unchanged.

## Reasoning and regression risk

The rule is implementation-safe and qualitatively coherent, but it supplies no
measured absolute-strength movement: every opponent, seat, seed, and paired
outcome is unchanged. The 95% paired-delta interval remains approximately
[-5.1%, +5.1%], so zero observed discordance is not evidence of population
equivalence or improvement. Absolute adjacent floors also remain poor at 1/8
versus Great Tusk and 2/8 versus Alakazam oselcoun. These facts do not show a
new regression, but they do show that the candidate has not repaired the
baseline's practical weaknesses or moved the primary Historical-Silver anchor.

The frozen extension could resolve only the missing mechanism-coverage
question. It cannot revise the already completed compact-72 score from 38/72
to 40/72 or Historical-Silver from 3/8 to 4/8. Because the adoption rule is
conjunctive, the candidate is already irreversibly ineligible. Therefore stop
the extension for this candidate rather than spend more evaluation time on a
result that cannot authorize packaging or submission. If this exact candidate
were ever reconsidered, the extension would still be mandatory; this judgment
instead closes it as rejected.

## Evidence reusable after rejection

- Reuse the exact public-state certificate, fail-closed state handling,
  last-callable/legality checks, focused route fixtures, and qualitative anchor
  audit as implementation knowledge. Do not promote or stack this rejected
  source as the new baseline.
- Reuse the clean 216-command structural result as evidence that the candidate
  is deterministic and valid, not as strength evidence.
- Reuse the four full-engine first differences only as examples for designing
  explicit telemetry. They prove a public Powerful Hand and three-card prize
  resolution, but not the route classifier, conservative floor, frozen target,
  one-route completion, or latch clear required by the contract.
- Reuse the Great Tusk and Alakazam-oselcoun floors as broad matchup evidence,
  not as opponent-policy labels or action-imitation targets.

## Exact evidence needed next

Before any later multi-step hypothesis can be promoted, freeze telemetry that
records the base certificate, route/guard classification, conservative hand
floor, committed attacker and target/prize fingerprint, stage transitions,
one-route limit, attack resolution, and latch clear in the full engine. The
next independently selected hypothesis must start from the exact retained
parent and again demonstrate practical compact-panel movement, both-seat
safety, Historical-Silver improvement, adjacent-population retention, zero
execution faults, and observed intended mechanism. No next rule is selected by
this judgment.

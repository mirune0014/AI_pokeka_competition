# Decision: reject pre-first-attack reserve rule

- Decision time: 2026-07-15 09:34:58 +09:00
- Result: `NO VALID HYPOTHESIS`
- Source edit: NO
- Package or Kaggle submission: NO

The corrected Bench-only signature is statistically concentrated in losses:
22/120 losses versus 33/520 wins, prevalence ratio 2.8889 and difference
11.9872 percentage points, with 11 cases in each policy seat and seven
opponents.  Distribution alone is not sufficient.

Root-verified evidence:

- immutable spec:
  `autonomous_gold_20260715/evaluations/historical_silver_pre_attack_reserve_v1/DIAGNOSIS_SPEC.md`
  (`3C1A8172EB3CC103F8572B1905924414D66CDA784BD9FA42B0D01ED30EA3BCEA`)
- root verification:
  `autonomous_gold_20260715/evaluations/historical_silver_pre_attack_reserve_v1/ROOT_VERIFICATION.md`
  (`16D901B6905F5CD04BAEE891FDD2FACAC2D921E1213FBFA430A819B282D0583F`)
- analysis A:
  `E16B54A13BEC1C452F16D00D72409D4202B107DDCE32069644EB8B43306E0857`
- analysis B:
  `AF5774A3843102BAC283484298C6F93A3FA46CD1F7842AADDEB085E40A117366`

Across all 22 losses, the only exact option classes common to the frozen
window were END and Metal Energy attachment to the Active.  END loses the
current attack.  Attachment was already selected in 18/22 losses; in the
remaining four it does not create a reserve and is redundant for the current
attack.  Exact Duraludon search was present in only 3/22 losses.  Matching
wins include immediate-KO, later-safe-reserve, no-reserve-win, resource-safety,
and Cornerstone non-ex Archaludon counterexamples.

The read-only Sol-Ultra strategy judge confirmed `NO VALID HYPOTHESIS`.
No reserve rule is implemented.


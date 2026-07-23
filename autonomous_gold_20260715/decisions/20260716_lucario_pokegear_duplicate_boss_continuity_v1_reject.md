# Reject - Lucario Pokegear duplicate-Boss continuity v1

Decision time: 2026-07-16 JST.

## Bound evidence

- candidate `main.py` SHA256:
  `A69E2C5915355D402B314AA4BC66D933B68A5C0E2976A86905238A97EB6093AE`;
- frozen evaluation specification SHA256:
  `57CA609E3A2B0911E32770D942BC42F65AA26B00E8F2808C4E4CDF229417DB1D`;
- Phase A execution log SHA256:
  `9D07A88A6088491DB16BC7248E06E32DD7ECF7434673E40FFCF20A24495041C8`;
- independent numerical/semantic evaluation SHA256:
  `5E8421FBDE25F2A64D0B0EF0CAC93E8AF8EBAEB573F798E010ADD3A4F4EDBF1A`;
- root Phase A verification SHA256:
  `8D6E9A89C0F4C0106A130250561AB432608BB9E6B6A6ED423AB051769D6F3919`.

## Decision

**REJECT AND RETIRE** the exact candidate
`historical_silver_lucario_pokegear_duplicate_boss_continuity_v1`.

The rule is correctly isolated: 41 unique hit games, 42 qualifying selections,
25 completed next-turn Supporter chains, zero off-predicate divergences, and
zero target regressions.  It nevertheless fails every frozen strength gate:

- reference: `+3/480`, three gains, CI lower bound below zero;
- fresh: `0/960`, zero gains, CI `[0,0]`;
- combined: `+3/1440`, versus required `+12`;
- aib4 combined delta `+2`, public delta `0`, so variant floors also fail.

The final read-only Sol-Ultra judge independently returned **REJECT / RETIRE**
on the same evidence binding.  Phase B, threshold loosening, a broader
in-place Supporter/search variant, packaging, and Kaggle submission are
prohibited.  No Kaggle slot was consumed.

The retained strongest parent remains
`autonomous_gold_20260715/candidates/historical_silver_kc_lone_nonex_v1`,
`main.py` SHA256
`44B846604C8A627BF9A1162BF1ADED3923976FAB1D200A333093347057790138` and
deck SHA256
`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

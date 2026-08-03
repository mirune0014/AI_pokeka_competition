# Decision: retain Historical-Silver; select Snotted Up diagnosis

- Decision time: 2026-07-15 09:34:58 +09:00
- Great Tusk reopening: REJECT
- Development parent: exact Historical-Silver Archaludon
- Next direction: Snotted Up lock escape trace diagnosis
- Source edit or Kaggle submission: NO

Root-verified supplemental outcomes:

- Historical-Silver: 185/320
- Great Tusk: 201/320
- paired delta: +16/320 for Great Tusk
- paired normal 95% interval: [-0.0264243228, 0.1264243228]
- unweighted prior-plus-supplement total: Historical-Silver 705/960 versus
  Great Tusk 577/960
- Great Tusk reopening threshold: +128/320; observed +16, FAIL
- Historical-Silver priority weakness: Cubchoo/Articuno 13/80, triggered

Evidence:

- screen spec:
  `autonomous_gold_20260715/evaluations/control_meta_supplement_seed2026071621/SCREEN_SPEC.md`
  (`EF9A9CF4F04E4BD556DC534F936FD2A64A7C6E552CB7E3F300ED2C998A07F7A8`)
- root verification:
  `autonomous_gold_20260715/evaluations/control_meta_supplement_seed2026071621/ROOT_VERIFICATION.md`
  (`C6ED05495780ABC9FB7B4F034696FE53C31BDA75B2CFFDDF1BDBC8D15F5A256A`)
- independent numerical audit:
  `0DF0905398DF2E5CA38D4D64FCA970D0060548B0E102157A7214CDD6B2A65399`

Cubchoo's Snotted Up attack (716) prevents the Defending Pokémon from using
attacks on its next turn.  The exact parent already records the opponent's
last attack, but has no rule for attack 716 and normally rejects retreating an
HP400 Active.  The read-only Sol-Ultra judge selected one next direction:
diagnose whether a legal, resource-safe manual retreat after attack 716 can
promote an already attack-ready Bench Pokémon and preserve a positive
same-turn attack.

The exact parent deck contains zero Switch (1123), so Switch is not a legal
baseline alternative and is not mixed into this diagnosis.  Adding Switch is
a separate deck-change hypothesis that requires separate evidence.


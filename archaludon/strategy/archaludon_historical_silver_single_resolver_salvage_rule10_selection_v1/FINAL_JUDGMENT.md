# Rule 10 final judgment

## Verdict

`DEFER-DORMANT`.

- Rule 10 is not integrated or widened.
- Accepted Rule 5 (`D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`)
  remains the parent.
- Rule 10 fixed760 is forbidden. It cannot substitute for the failed
  mechanism-activity gate.

## Evidence

- Focused plus inherited tests: 35/35.
- Structure and both-seat smoke: pass.
- Replay shadow: 30,977 callbacks; starts, completions, aborts, faults, and
  differences all zero.
- Fixed160: Rule 5 = Rule 10 = 100/160; G/R/T 0/0/160; seats 47/80 and 53/80;
  Historical-Silver anchor 20/40; every cell delta zero.
- Execution faults, action errors, max-step hits, and duplicate mismatches:
  zero.
- All 160 candidate traces are byte-identical to Rule 5. Rule 10 entry
  necessarily changes ATTACK to FML PLAY, so fixed160 starts and completions
  are proven zero.

## Reasoning

Observed setup, board formation, attacker and backup readiness, resource use,
attack continuity, Prize exchange, finishing, and disruption are unchanged
Rule 5 behavior. This proves fallback neutrality on the sampled states, not
safety or strength after Rule 10 activates.

The frozen minimum of one complete non-fixture
`FML PLAY -> same registered ATTACK` transaction fails at zero. Latent risks
include irreversible Stadium spend, accidental opponent protection, later
Prize or backup-continuity damage outside the bounded reply, and post-spend
owner/receipt faults. Conditions remain frozen and the candidate remains a
separate dormant record.

## Controlling reports

- Independent numerical audit SHA-256:
  `DCB908B411CCCAACA57F73D21636972284EF95254BBBBA5BAF7ED5E023549DA5`.
- Root fixed160 recomputation SHA-256:
  `9001FC773F822815AFAE79652237641C5D1EADC13783497FD3C050FBE09423AB`.


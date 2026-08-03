# Root verification: Rule 7 Turbo Flare concentration

## Frozen inputs

- Accepted parent: Rule 5 `main.py`
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 7 strategy:
  `7F39297030D9DD83978FBCF5C7887B67E6C7455604B5A9E3B0D2D130447860E4`.
- Controlling final-target amendment:
  `13376C2D6D7808446E4EBC869E7F696BBAC22EA226C3A866237A02D26554FE34`.
- Candidate `main.py`:
  `9C2D5935364C0940967D48D85E2690EC386569143CD922186A31C716C5391BC1`.
- Candidate deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

## Independent structural and focused verification

Root reran the complete inherited and Rule 7 focused suite with Python 3.11
and bytecode disabled.  All 37 tests passed.  The verifier independently
confirmed compile/import, one top-level `agent`, one top-level `_resolve`, one
static parent call, 13 package files, 12 byte-identical non-main files, legal
60-card deck, one Hero's Cape ACE SPEC, and zero cache artifacts.

The parent diff changes only `main.py`.  Root inspected the Rule 7 helpers and
resolver insertion.  They are limited to exact Turbo Flare `ATTACH_TO` and
`ATTACH_FROM`, the three current printed roles `190/253`, `840/1212`, and
`169/224`, Basic Metal deficits, physical serial rebinding, one primary, at
most one backup, and the shared owner.  No future evolution, hidden-card
inference, opponent threat model, generic effect simulator, new score, or
additional wrapper was added.

The original lifecycle retained ownership after the final target and could
suppress the next callback.  Root identified this before evaluation.  The
controlling amendment now releases the owner on the last exact target and
records `UNCONFIRMED_ENGINE_TERMINAL_BOUNDARY`; it does not claim completion.
The passive duplicate token is order-independent, clears on the first
nonmatching callback, and allows that same callback through the normal
resolver.  The zero-selection path also clears without suppressing that
callback.

## Independent replay shadow verification

Root reran the frozen shadow runner.

- Corpus SHA: `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`.
- 78 source paths, 77 readable replays, one previously known malformed file.
- 4,262 callbacks; 46 Rule 7 starts; 65 intermediate target emissions; 23
  final unconfirmed target emissions.
- 23 first differences and 23 explicit counterfactual rollbacks.
- Difference classes: 12 exact primary fills, 4 one-backup remainders, 3
  useful-count reductions, and 4 empty-Bench zero selections.
- Zero invalid actions, exceptions, faults, owner-release violations,
  prohibited final-status labels, or passive nonmatch suppressions.
- 23 passive nonmatching callbacks continued through the ordinary resolver.

Every first difference is within the frozen Rule 7 mechanism.  None uses a
third recipient, exceeds three Basic Metal, projects an evolution, or occurs
outside Turbo Flare.  Changed replay suffixes cannot prove the candidate's
counterfactual board and are not treated as outcome evidence.

Evidence hashes:

- implementation report:
  `473A9C9EED55C2AACAF708AF8CA4CBCAD8D94F5185259E54951EFE0FFCDF8AAC`;
- shadow summary:
  `9995A4BA526826E60BC723C172543F6D3B646F253EE2C9B0E462CFCAB53C8DB9`;
- shadow differences:
  `0A9B27256067D87C3835E98235BACAF0C9EA3E7E6A867647E1F4609254E7C72D`;
- Rule 7 focused fixture:
  `7635F4CCA0B927E8C1F799E74AC485B706F55F13A65B622C524F4F15BEF88D0A`;
- verifier:
  `797D4D1E1F4CA616A24442F12EA8592FADC9BFBE070E1CF5C8087B8088326A44`.

## Gate to fixed160

Implementation, structure, focused, shadow, and both-seat loader smoke gates
pass.  This is permission to run the frozen fixed160 only, not acceptance.
The evaluation must verify actual final attachments from engine traces, caps,
primary readiness, at most one backup, no third recipient, no stale-owner
suppression, schedule equality, duplicate controls, faults, and the numerical
retention gates.

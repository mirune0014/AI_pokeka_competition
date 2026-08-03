# PBNS native-engine contract correction

## Authority

This correction supersedes the positive-completion requirement for
`88035562 / seat 0 / step 62` in
`ROOT_ATTACK_LEGALITY_REPAIR_AMENDMENT_20260801.md`.

It does **not** authorize a broader implementation.  It records that the
required positive and the controlling v1 parent-deference rule cannot both hold
under the native engine.

## Newly verified contradiction

The conditional route certificate describes:

`Night Stretcher 28 -> Metal 58 -> Active Duraludon 4 -> Hammer In 223`.

The first two operations are legal.  At the first MAIN callback after recovery,
however, the exact direct parent chooses a productive manual Metal attachment
to benched Duraludon `5`, not the saved Active attachment to serial `4`.

The controlling v1 rule in the frozen source requires every legal non-END
parent continuation after the same Stretcher/recovery to be preserved unless a
complete exact strict-dominance proof exists.  It therefore delegates to the
parent, clears the saved PBNS queue, and never reaches Hammer In.  The same
native behavior reproduces at the later counterfactual duplicate rows and the
evolution positives hand off before their saved ATTACK step as well.

The previous focused fixture manufactured later ATTACK options and was not a
native proof of the final policy lifecycle.

## Decision

- Do not weaken the native-engine gate.
- Do not add a second ownership/parent-override hypothesis to the legality
  repair.
- Freeze the attack-legality successor only as diagnostic safety work.
- Classify PBNS as `PRIMARY_MECHANISM_INOPERATIVE` in addition to its existing
  `RARE_NARROW_FAIL` and first-turn safety defect.
- Skip full successor shadow, fixed-760, packaging, and Kaggle submission.
- Move directly to the independently selected symmetric Full Metal Lab rule.


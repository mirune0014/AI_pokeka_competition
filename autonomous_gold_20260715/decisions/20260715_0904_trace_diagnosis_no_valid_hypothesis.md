# 2026-07-15 09:04 JST — Trace Diagnosis: No Valid Hypothesis

## Decision

Do not change the exact Historical-Silver source after this 640-game trace
pass. Keep it as the development parent.

## Verified basis

- The trace rerun matched the prior fixed evaluation on all 640 unique
  `(opponent, seat, seed)` keys and on `game/result/steps/action_errors/`
  `hit_max_steps/started`.
- Parent result: `520/640`; seats `258/320`, `262/320`; action errors and
  max-step hits `0`.
- Replay analysis A report SHA256:
  `A38BD91BA817A32821D6DD55E8397D4F1097BAB39CF63CCD45DEF3B7C1D5A4B0`
- Replay analysis B report SHA256:
  `E38935B385242EFD11B35E1DB6F1AD497D2F78C9FCC2F59BBEF90474CBD90062`
- Root independently reproduced the three analysis-B game/event counts and
  checked representative continuity, board-formation, and Cornerstone
  counterexamples directly in the raw traces.

Every high-correlation signature either missed a predeclared floor, lacked one
beneficial legal alternative shared by the matching losses, or had repeated
matching-win counterexamples that would lose a same-turn attack or needed board
formation. Replay actions were not treated as labels.

## Next single diagnosis direction

For losses whose first attack begins without a reserve Archaludon line, trace
back exactly one own turn and inspect the earliest public legal branch that
could form a bench line without giving up the current attack. Compare the
parent's actually available Poké Pad, Ultra Ball, Explorer, Night Stretcher,
and direct Duraludon-placement branches in matched loss/win strata. No patch is
authorized until one common, safe alternative
passes the same thresholds.

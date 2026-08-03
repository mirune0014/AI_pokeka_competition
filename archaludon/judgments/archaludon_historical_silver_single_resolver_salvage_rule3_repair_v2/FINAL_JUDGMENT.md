# Final judgment: Rule 3 Ultra Ball transaction repair v2

Date: 2026-08-03 JST

## Verdict

**ACCEPTED AS NON-DESTRUCTIVE**

The candidate may replace the prior single-resolver salvage candidate as the
accepted development parent. It must not be described as stronger than the
parent.

## Basis

- Focused Rule 3 tests: `276/276`.
- Inherited Rule 1/4/5 tests: `28/28`.
- Natural Active and Turbo transactions complete under one owner, including
  the Historical-Silver setup prefix and the declared terminal attack.
- Fixed160: parent/candidate `100/160`, `G/R/T 0/0/160`, all traces identical.
- Fixed760: parent/candidate `480/760`, `G/R/T 0/0/760`; both seats, mirror,
  every adjacent opponent, and every opponent-seat cell are equal.
- Fixed760 execution and duplicate controls have zero faults.
- Lifecycle scan: 10 committed starts, 10 completions, zero aborts. One
  additional provisional start releases to the exact parent before commitment
  and leaves the full game trace identical.
- The five candidate-parent trace differences are four safe same-turn
  evolution/setup reorderings with state convergence and one harmless Basic
  Metal serial permutation. None is a clear bad move in the observed state.

The only failed inherited gate is the strengthened threshold `480 < 486`.
That prevents a strength claim, but it does not invalidate non-destructive
retention. Unseen-state equivalence is not claimed.

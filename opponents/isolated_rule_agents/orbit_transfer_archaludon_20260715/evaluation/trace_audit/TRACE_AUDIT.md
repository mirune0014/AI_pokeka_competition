# First-divergence trace audit

## Scope

Baseline and candidate were rerun on all 680 frozen paired schedule keys with
full scored traces: 200 historical-Silver mirror games and 480 games against
the six-agent adjacent population.  This produced 1,360 traces from 28 commands.
All commands exited 0; all 1,360 summaries have zero action errors and zero
max-step hits.

The checked repository comparator
`tools/compare_local_trace_first_divergences.py` produced 680 comparison rows.
The combined CSV is `first_divergences.csv`, SHA256
`3B9730299B35834DF16828B0D3937FD51B94729C065E273D337592B11063A6C9`.

## Root-verified first divergences

- 206/680 traces diverged, exactly matching the 206 paired rows with a step
  difference.  The other 474 traces were action-identical.
- Every divergence was an action by the candidate's seat in MAIN.
- Every candidate choice was an ATTACK with reason `terminal conversion`:
  Metal Defender `253` in 204 traces and Raging Hammer `224` in two traces.
- Every baseline choice was nonterminal: PLAY in 146 traces, ATTACH in 38, and
  EVOLVE in 22.
- Every divergent pair was a win for both baseline and candidate.  Candidate
  used fewer steps in all 206 and more steps in zero.  Paired losses had zero
  action or step divergence.
- A matching candidate attack log exists after all 206 first divergences.
- No trace returned to MAIN after the certified attack.
- In 204 traces the only later recorded selection was the candidate's Prize
  selection.  In two Marnie/Tonakai traces, an opposing post-KO Tool effect
  produced two forced effect-target selections before the candidate's Prize
  selection.  Both still ended in a candidate win.

The numerical audit independently measured 773 total saved decisions across
the 206 shared wins.  There were zero outcome gains and zero outcome losses.

## Precommit wording discrepancy

The immutable trace gate said that the candidate divergence must be its final
*recorded decision*.  This literal condition is false in all 206 divergences:
the engine records Prize selection after a KO, and in two games it also records
a forced opposing Tool effect.  The intended semantic condition--the certified
attack is the final strategic MAIN action and proceeds through KO/Prize handling
to a win--holds in all 206 traces, with zero later MAIN choices.

This discrepancy is recorded rather than silently redefining the frozen gate.
The artifact therefore cannot be called a gate-passing strength improvement.
The trace evidence supports retaining it only as an outcome-neutral, safely
scoped Orbit-transfer experiment unless a later frozen schedule produces an
actual baseline-loss/candidate-win conversion.


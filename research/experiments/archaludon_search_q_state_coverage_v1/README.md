# Archaludon Search-Q Large State Coverage v1

This experiment keeps the existing complete-action bridge, hidden sampler,
paired determinization runtime, semantic encoder, expected-Q model, losses,
and single-override contract unchanged. It changes only source-game coverage
and assigns each branch group to exactly one fixed search stage.

The frozen specification is `specs/state_coverage_v1.json`. The bounded Pilot
uses 64 training, 16 calibration, and 16 offline-test source games. It selects
the minimum coverage needed by the technical gate (six training groups and two
evaluation groups per opponent/seat cell), performs the three one-step model
checks, writes a projection, and stops. It never starts the 20,000-game source
collection, full supervisor, or final paired evaluation.

Run the bounded Pilot with:

```powershell
python -m research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.cli pilot
```

Long-running production execution is separate and requires an explicit
`supervise` invocation. Generated data belongs under `_local_generated/` and
is intentionally not part of the experiment commit.

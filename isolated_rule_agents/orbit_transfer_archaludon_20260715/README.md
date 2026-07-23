# Orbit-transfer Archaludon terminal-conversion variant

## Status

This is a complete, runnable, pure deterministic rule-based agent built in an
isolated directory.  It is retained as an **outcome-neutral experimental
variant** and is **not** promoted over the historical-Silver baseline.

No existing agent was edited, and this variant was not submitted to Kaggle.

## Strength anchor

The baseline is the exact sustained historical-Silver Archaludon package:

- archive:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`;
- archive SHA256:
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`;
- exact baseline `main.py` SHA256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- documented public run: peak `1045.58`, `12-1` start, and `18-8` after 26
  games;
- historical direct local selected-bucket result: `0.7604`, versus `0.7361`
  for the older transient-1072 rule policy.

The baseline remains the strongest anchor because the new variant produced no
paired win gain.

## Orbit Wars transfer

The transferred idea is semantic intent plus short-horizon, public-state
projection:

1. Generate a terminal-attack intent only from a currently legal attack.
2. Prove from public information that it takes every remaining Prize.
3. Fail closed for status, prevention, reduction, unknown effects, types, or an
   unmodelled attack.
4. Rank only that certified terminal attack ahead of ordinary utility actions.
5. Recompute the proof at every observation; store no policy state.

The implementation does not use RL, imitation, replay action labels, learned
rankers, or opponent-policy proxies.

## Artifact layout

- `baseline_exact/`: untouched extraction of the historical-Silver anchor.
- `candidate_terminal_conversion/`: runnable candidate and focused tests.
- `evaluation/`: raw paired results, numerical audit, and full trace audit.
- `EVALUATION_SPEC.md`: frozen hashes, schedules, gates, and trace contract.
- `orbit_archaludon_terminal_conversion_experimental_20260715.tar.gz`:
  runtime package.

Candidate receipts:

- `main.py` SHA256:
  `5382920827F0159D847741B494C8ADD19E0A4C840AEB0697D6ADBBD9D27C3277`;
- `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`;
- package SHA256:
  `C31B7DDDFC59D1182B54E2501093C2FC86D271586481E2398D24D59D0565A061`;
- package size: `2,005,049` bytes, 18 members.

Fresh archive extraction reproduced the candidate source/deck hashes, compiled,
imported normally, and loaded exactly 60 cards.

## Verification result

Focused implementation tests: `9/9` passed.

| panel | paired rows | baseline wins | candidate wins | gains | losses |
|---|---:|---:|---:|---:|---:|
| historical-Silver mirror | 200 | 100 | 100 | 0 | 0 |
| six-agent adjacent population | 480 | 317 | 317 | 0 | 0 |
| total | 680 | 417 | 417 | 0 | 0 |

All schedule keys were exact and unique.  All 42 paired-run subprocesses and 28
trace-run subprocesses exited 0.  Duplicate controls were exact, and action
errors and max-step hits were zero.

The candidate differed in 206 shared wins and saved 773 decisions.  It never
changed a loss.  Every first divergence was the intended terminal attack:

- Metal Defender: 204;
- Raging Hammer: 2;
- baseline action displaced: PLAY 146, ATTACH 38, EVOLVE 22;
- trigger-external divergence: 0;
- later MAIN decision after the attack: 0.

The frozen trace wording required the attack to be the final *recorded*
decision.  This literal condition did not pass because the engine records Prize
selection after KO; two games also recorded a forced opposing Tool effect first.
The discrepancy is documented in `evaluation/trace_audit/TRACE_AUDIT.md` and was
not silently redefined.

## Adoption decision

Keep and package the variant as a deterministic terminal-conversion experiment.
Do not call it a stronger agent, do not replace the historical-Silver anchor,
and do not submit it to Kaggle without a future frozen schedule that produces
at least one baseline-loss/candidate-win conversion with zero regression.


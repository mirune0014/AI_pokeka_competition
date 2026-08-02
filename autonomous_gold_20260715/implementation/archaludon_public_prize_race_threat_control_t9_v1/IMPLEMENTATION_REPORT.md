# Task 9 implementation report

## Frozen inputs

- Parent candidate: `archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1`
- Parent `main.py` SHA-256: `74C20CCA851E6BCADB62382314656AE7506BD964C29DCE38A80BB5F665A0E971`
- Parent/candidate `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Strategy contract SHA-256: `1FABEADC8883981E36F318138EF04A58A4CE6D2E06F026E47B6955932A974351`
- Root evidence SHA-256: `816DC0A3690ACE09AF617A47E2AD4844743D205511704F59B3670253CCF3BF7D`

## Behavioral intent

The candidate appends one final deterministic Task 9 planner around the exact Task 8 parent. It compares complete, public-state plans conditionally rather than adding action scores. The six exhaustive internal purposes are:

1. `EXACT_LOSS_AVOIDANCE`
2. `HARMFUL_KO_VETO`
3. `RESET_WALL_ONE_SHOT_OR_BYPASS`
4. `NONTERMINAL_BOSS_PRIZE_CONVERSION`
5. `READY_THREAT_OR_ENGINE_REMOVAL`
6. `COMEBACK_RESOURCE_REQUIREMENT`

Plans cover exact current attacks, END, Boss target plus attack, inherited PCRD setup plans, and certified one-step successor preparation. Boss is a three-callback transaction (`BOSS_PLAY_EMITTED -> BOSS_TARGET_EMITTED -> ATTACK_EMITTED`) with seat/turn/action-count, physical movement, supporter-use, target, board, attack-certificate, duplicate, stale, and ownership checks. While that owner is live, the actual late-bound PCRD and Pokégear inherited-owner boundaries suppress new lower transactions; owners already present before Task 9 starts keep precedence. Route threat/evolution/engine identity uses schema-declared serial fields and exact integer equality, never substring matching. Task 7 terminal Boss retains precedence. Unknown public effects fail closed to the exact parent.

## Files and hashes

- Candidate `main.py`: `0A9F0052095257B08CC5C5ABACAA0E912D7E02A9842145B48E2192A6F50ED4AE`
- Candidate `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- `run_focused_fixtures.py`: `8397F95AD42FF0ECF1D035585DCD61B609875F38C00C431F7C036E90E27E8B01`
- `focused_fixture_results.json`: `4D1FCCE12B49914A270DA0EDBC257E6199AF61C3CCEB31A56BF6530522BCC9BC`
- `test_inherited_effect_registry.py`: `5968967907194020CD34DC7021F090EDBC103453740766BB9072F23A473F4CA5`
- `run_replay_shadow.py`: `E12E23BCEA792EFC65FD7D0862C61AB1D6C6DC1D289B53953B856F203D09F27E`
- `replay_shadow_results.json`: `81EA74F57CCC90AC75FFE89A8AA3B7E1780C1B16BC101EFED20C5C740A4A8C14`
- `engine_smoke_seat0.jsonl`: `EE80220134919A93C6413D8E879C852F06E605E921398CAD35F5DABBD4CA81EF`
- `engine_smoke_seat1.jsonl`: `435EA0A5B645E2195B2AE32A990FB0745F7198610A1C9ED84A978F249619E9E8`
- `verify_structure.py`: `9878035C6AC2D28538F171E69600E8CD5BCB25CEBFED8B83261FF4BD487169CA`
- `structural_results.json`: `AE0D3029227A5842CDF74492A22BA12CE1FCBDC0F21F94D59CB119E78FEE03EC`

## Verification

- Python compile:
  - Command: `.\.venv-rl\Scripts\python.exe -m py_compile <candidate main and owned test scripts>`
  - Outcome: PASS, exit 0.
- Focused fixtures:
  - Command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_prize_race_threat_control_t9_v1\run_focused_fixtures.py`
  - Outcome: PASS, 52/52.
  - Coverage includes both-seat Boss lifecycle, duplicates, stale/owner aborts, Task 7 precedence, harmful-KO positive/negative, reset-wall one-shot/bypass/fallback, bench-wipe avoidance, nonterminal Boss conversion, ready-threat positive/negative, all-losing comeback, unknown-effect fail-close, exact bench attachment, exact Archaludon evolution plus forced Assemble Alloy, and PCRD handoff.
  - Accepted-parent-through-final-wrapper coverage includes both seats and both Turbo Flare/Metal Defender across Boss play, target, post-gust MAIN, and bound attack. T9 remained the sole owner, lower PCRD/Pokégear/DPER owners did not start, the attack emitted, T9 released, and the following Turbo Flare callback became owned by DPER.
  - Structured serial regression produced exactly `{13, 30, 39}` and rejected collision values `3`, attack id `253`, and `139`; no substring serial inference remains.
- Inherited public-effect registry:
  - Command: `.\.venv-rl\Scripts\python.exe -B -m unittest autonomous_gold_20260715.implementation.archaludon_public_prize_race_threat_control_t9_v1.test_inherited_effect_registry`
  - Outcome: PASS, 32/32.
- Replay shadow:
  - Command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_prize_race_threat_control_t9_v1\run_replay_shadow.py`
  - Coverage: all 46 current paths plus deterministic first 32 of 207 historical paths by SHA-256(filename); 77 readable, one malformed/truncated current JSON unreadable.
  - Outcome: zero invalid actions; five first differences spanning both seats.
  - `episode_89277462`, seat 0, step 45: `EXACT_LOSS_AVOIDANCE`; changed an exact next-turn board-wipe line into Boss plus durable 70 damage with no exact reply loss/wipe.
  - `episode_89279601`, seat 0, step 112: `NONTERMINAL_BOSS_PRIZE_CONVERSION`; changed 190 non-KO damage into an exact one-Prize KO while retaining two ready successors.
  - `episode_89282820`, seat 1, step 118: same purpose; changed 190 non-KO damage into an exact one-Prize 220-damage KO.
  - `episode_89284977`, seat 0, step 49: same purpose; changed 190 non-KO damage into an exact one-Prize 220-damage KO.
  - `episode_89285518`, seat 1, step 83: same purpose; changed 190 non-KO damage into an exact one-Prize 220-damage KO while retaining a ready successor.
  - Exact embedded-parent semantics matched the separately loaded Task 8 parent in all five positions. The five prior good boundaries remained unchanged. No observed first difference was destructive; exceptions, invalid fallbacks, and owner collisions were all zero.
- Exact-engine native smoke:
  - Candidate seat 0, seed `2026080212`: 87 steps, target result win, action errors 0, max-step false.
  - Candidate seat 1, seed `2026080211`: 26 steps, target result win, action errors 0, max-step false.
- Structure/package-layout gate:
  - Command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_prize_race_threat_control_t9_v1\verify_structure.py`
  - Outcome: PASS. Parent prefix byte-identical; deck count 60; ACE SPEC count 1; final top-level node is the only effective last `agent`; expected entries exactly `deck.csv`, `main.py`, `requirements.txt`; cache count 0.

## Known tradeoffs

- The planner uses public exact state only and deliberately declines unknown-effect or hidden-reply inference.
- Full alternative-plan population is performed for certified danger/reset states; an otherwise safe durable parent is changed only by exact Boss prize conversion or certified threat removal.
- Replay shadow is callback-complete only until each first counterfactual difference; the suffix after a changed action cannot be treated as the same factual game.
- The historical shadow is a frozen bounded sample of 32/207 because the full corpus was operationally too slow. This is adequate for the requested destructive-defect screen, not a strength estimate.

## Evaluator requirements

- Compare this exact source against Task 8 on identical seeds in both seats.
- Inspect every Task 9 first difference and report results by the six purpose labels.
- Exercise completed Boss lifecycle and successor-PCRD/Turbo-Flare handoff transactions, not merely planner starts.
- Treat absent natural starts for any rare purpose as missing coverage, not as evidence of benefit or permission to widen the rule.
- Preserve the exact Task 8 parent as rollback; do not stack another hypothesis before judging this one.

No archive was created. No commit, push, or Kaggle write was performed.

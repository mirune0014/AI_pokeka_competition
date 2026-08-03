# Rule 3 Implementation Report

## Changed files

- `candidates/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/main.py`
  - SHA-256: `3F05F353B868307E91A38FA62ED460D4BFB9A82B85400E2D98B3DBB5CE67A0FC`
- `candidates/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/_rule3_ultra.py`
  - SHA-256: `2015A4E589D2AE428A151AF50520C160CED7E1B1926D5599A2B35EB0CC6CEA61`
- `implementation/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/run_focused.py`
  - SHA-256: `9979080BD42F7C56799C3417958EBABB4BB1C9A84F5F9C5EDD6D32711B265490`
- `implementation/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/focused_results.json`
  - SHA-256: `E6629A850A837A9FCF8E28605F97E76BA7BEA03BC438567C4B4C1FCBE9792FEE`
- `implementation/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/shadow_89280661.json`
  - SHA-256: `67AE2958B121C3D0D4D50B50CF7F8BE9E6074F0990CF17346E68E062E270D03E`
- `implementation/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/smoke/seat0_summary.jsonl`
  - SHA-256: `02FED9509DC448CE443D8CB7F4215AD2A11C7C67FEF0C95ED469C918D72DC8D7`
- `implementation/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/smoke/seat1_summary.jsonl`
  - SHA-256: `42C92EF3128A3A8FCFF95D4C09B7F026F1963DC671313446678DF6D5F0D55F34`

The frozen parent and deck were not changed.

- `_historical_silver_parent.py`: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Behavioral intent

Rule 3 owns exactly one of the following complete transactions, and only when the parent already selected Ultra Ball.

1. Search and bench Duraludon from Cinderace, preserve the parent-equal Turbo Flare attack, and concentrate the revealed Basic Metal Energy on that Duraludon.
2. Search Archaludon ex from an Active Duraludon, evolve it, use Assemble Alloy and a manual attachment when required, and preserve the parent-equal Metal Defender attack.

Discard candidates are restricted to the surplus cards allowed by the frozen contract. Rule 3 does not start, or releases its owner and returns to the parent action obtained once for the callback, when Boss is legal or when the discard, search, placement, evolution, Energy, or attack route cannot be completed from public information. It does the same for an owner conflict, prompt mismatch, or search whiff. Rule 2 is not included.

## Verification results

- `py -3.11 -B .../run_focused.py`
  - 80/80 PASS.
  - Both seats covered the two complete routes, zero through three Turbo Flare target Energy, source retry, Boss veto, search whiff, and parent-prefix mismatch.
  - For Active with one Energy, discard with one Metal Energy, and hand with one Metal Energy, the hand Energy is retained when two safe surplus costs exist. When there is no safe second cost, the hand Energy may be used only when Assemble Alloy immediately reattaches it.
  - With at least two Metal Energy in discard, the destructive route that discards hand Metal Energy is rejected.
- Existing Rule 1 focused suite rerun against the candidate
  - 13/13 PASS.
- Compile, import, and structural checks
  - `main.py`, `_rule3_ultra.py`, and the frozen parent compiled and imported successfully.
  - Exactly one final `agent`, one resolver, and one static parent `agent` call. No local changes to `score_option` or `choose_options`.
  - The Rule 3 proposal has only `rule_id`, `action`, `category`, `purpose`, `exact_proof`, and `transaction`.
  - Deck has 60 cards and one ACE SPEC. There are zero `__pycache__` directories.
- Checked-engine smoke
  - Seat 0, seed `803203001`: 73 steps, zero action errors, no max-step hit.
  - Seat 1, seed `803203002`: 164 steps, zero action errors, no max-step hit.
- Frozen replay shadow
  - Episode `89280661`, target seat 1, 58 callbacks.
  - Zero action differences from the accepted Rule 1 parent and zero invalid actions.
  - Zero natural Rule 3 starts. This one replay does not establish natural activation.

## Known tradeoffs and evaluator handoff

- Focused fixtures establish transaction correctness, not natural activation frequency or a win-rate gain.
- The only shadow replay had zero natural starts. If fixed160 also has zero natural starts, retain the implementation record but classify it as `DEFER-DORMANT` without widening the conditions, and do not integrate it into the final candidate.
- Fixed160 must compare against the Rule 1 parent with identical seeds and both seats. Inspect natural starts, completed transactions, owner releases, every first difference, paired gains and regressions, and opponent and seat floors.
- No archive, fixed160/760 evaluation, commit, push, or Kaggle submission was performed.

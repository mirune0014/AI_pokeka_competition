# Task 6 implementation report: hard-protected complete-route revision

## Files changed

- Candidate `main.py`: hard-protection implementation. SHA-256
  `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`.
- `run_focused_fixtures.py`: both-seat binding, readiness-order, and accounting
  fixtures. SHA-256
  `F825D4A1453E3D89170040716CA15DDB1E13F0A55A8E47CDE86CB84C0F64FECE`.
- Regenerated assigned verification outputs:
  `focused_fixture_results.json`, `replay_shadow_results.json`, the three
  `replay_*_parent_vs_candidate.json` files, `structural_results.json`, and
  `engine_smoke_seat{0,1}.jsonl`.
- This report was updated. No deck or other candidate-package file changed.

Frozen parent `main.py` SHA-256 remains
`2B23D3AFC63A5BDC4BC7765CE1656725ED01890D161E3D23DCC672BE7FCCCFF4`.
Parent/candidate deck SHA-256 remains
`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
The candidate has 12 package entries; `main.py` is the only byte difference
from the parent. `git diff --no-index --stat` reports one file changed, 1,868
insertions and 278 deletions.

## Behavioral intent

`PUBLIC_ULTRA_BALL_DECLARED_COMPLETE_ROUTE_TRANSACTION_V1` still declares one
complete Ultra Ball route and exhaustively compares physical discard pairs and
energy variants. Before energy enumeration it now derives public route
bindings and rejects any pair that violates them.

Bindings use exact serials for a concrete current/manual or Turbo-completion
Metal, and minimum retained counts for a concrete Boss target, executable Night
Stretcher recovery, exact evolution or Duraludon-successor route,
parent-declared Supporter, required Stadium or Tool, manual/evolution Metal,
and one certified next attacker. Copies above a route's retained minimum remain
discardable. These gates are independent of the opportunity-level identity
score.

Energy enumeration now records and exposes rejected overattachments, wasted
manual variants, and otherwise legal but readiness-wasting Alloy assignments.
Chosen certificates retain the existing lexicographic readiness ordering and
carry the route-binding and enumeration-accounting evidence. The prior
purposeless-Ultra amendment and all callback behavior remain unchanged.

## Verification results

1. Compile and import:

   `py -3.11 -B -c "... compile(candidate main.py and run_focused_fixtures.py) ..."`

   Outcome: exit 0, `compile_changed_ok 2`.

   `py -3.11 -B -c "import main; ..."` from the candidate directory.

   Outcome: exit 0, `import_ok True
   PUBLIC_ULTRA_BALL_DECLARED_COMPLETE_ROUTE_TRANSACTION_V1`.

2. Focused fixtures:

   `py -3.11 -B autonomous_gold_20260715/implementation/archaludon_public_ultra_ball_declared_complete_route_transaction_v1/run_focused_fixtures.py`

   Outcome: exit 0, 210/210 passed in each of two consecutive runs. Both
   generated SHA-256
   `D3D8D71A00EBE5D23203FD8C89B67B7850911867500BB1DEBA4435D5ED65802C`.

   New controlling evidence passes in both seats:

   - hard-bound Boss/evolution/recovery state selects Metal 111 plus expendable
     Ultra 114 and retains all three bound routes;
   - Metal plus two bound cards has no safe pair and declines Task 6 ownership;
   - with two Boss copies and a one-copy minimum, one Boss is discarded and
     one retained;
   - the Cinderace no-Energy state binds Metal 133 exactly for Turbo Flare and
     discards Ultra serials 128 and 129;
   - competing recipients expose the chosen readiness result of two ready
     attackers and zero backup deficit, matching complete-plan ordering;
   - the accounting state records 2 wasted-action variants, 19 wasted-manual
     variants, and 64 rejected overattachment variants, while the chosen plan
     has zero wasted actions.

3. Stateful replay shadow:

   `py -3.11 -B autonomous_gold_20260715/implementation/archaludon_public_ultra_ball_declared_complete_route_transaction_v1/run_replay_shadow.py`

   Outcome: exit 0. Episode 89280661: 58 decisions, one difference; episode
   89291523: 59 decisions, one difference; episode 89347400: 11 decisions,
   zero parent/candidate differences. Output SHA-256
   `5D041D28386A1AD5CF4ABF7FD20E1A989C314657BE10D70520A916F0D7076893`.

4. Checked replay comparators:

   `py -3.11 -B tools/compare_replay_agent_actions.py --engine-dir <candidate> --replay <replay> --left <parent> --right <candidate> --output <assigned-output>`

   All three commands exited 0:

   - 89280661: 58 decisions, one difference at step 8; candidate discards the
     two redundant Ultra Ball copies. Output SHA-256
     `524F055DF4B383F9C40CE39799B2EE38FDCD13A111833E1C528B9BE4210BC8B6`.
   - 89291523: 59 decisions, one difference at step 104; candidate makes the
     required Bench Metal attachment with no Task 6 owner. Output SHA-256
     `B8C1BD5DC27BB6FAB070049BBBD44B7E361F9361CFDE7398CD229807064DC04F`.
   - 89347400: 11 decisions, zero parent/candidate differences. Output SHA-256
     `6AB3F5EBD69F6AC1D6F47CEBD10D43321E44E506A605F166730D7A6BE6C018BE`.

5. Structure and deck:

   `py -3.11 -B autonomous_gold_20260715/implementation/archaludon_public_ultra_ball_declared_complete_route_transaction_v1/verify_structure.py`

   Outcome: exit 0; final callable `agent`; imported callable true; 12 package
   entries; no non-main byte mismatches; deck count 60; ACE SPEC count 1; no
   cache entries. Output SHA-256
   `B2417652C90B3030B3BD48ACB4933BB7FEDEE7183ABE8F540B8242BCBDC2D37B`.

6. Both-seat checked-engine smoke against historical Silver:

   `py -3.11 -B tools/run_local_battle.py --engine-dir <candidate> ... --games 1 --max-steps 1000 --seed-base 20260804 --no-trace --summary <seat0-output>`

   Outcome: exit 0; 122 steps; action errors 0; max-step hit false. Output
   SHA-256
   `CB2F40767D1CC55527A3407A5614750C0D8BE3931FFB525D3FD1B2A48EDE8F74`.

   The seat-reversed command with seed base 20260805 exited 0; 99 steps;
   action errors 0; max-step hit false. Output SHA-256
   `E77153E356B4BC05449EDF199AD484E743C1E0DC9247795854206611CD9B0001`.

## Known tradeoffs and evaluator checks

- Hard protections are public and route-specific. They intentionally do not
  reserve every Boss, recovery card, evolution, Supporter, Stadium, Tool, or
  Metal by identity.
- Equivalent copies may substitute above a minimum binding; exact current or
  Turbo attachment bindings retain the canonical physical Metal serial.
- Static replay suffixes cannot execute a counterfactual callback after the
  first changed action; callback completion remains covered by the both-seat
  focused fixtures.
- The evaluator should inspect the six new both-seat fixture groups, especially
  the exact `(Metal 111, Ultra 114)` cost, no-safe-pair decline, Boss redundancy,
  readiness certificate, and nonzero accounting fields. It should also rerun
  all 210 focused fixtures, the three replay comparisons, structure check, and
  both smoke seats.
- No archive was created. No Kaggle, upload, Notebook, Discussion, Git, or
  Codex-configuration action was performed.

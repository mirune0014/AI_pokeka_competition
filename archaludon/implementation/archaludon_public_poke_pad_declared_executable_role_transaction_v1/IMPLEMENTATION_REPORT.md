# Task 5 implementation report

## Candidate

- Parent `main.py`: `CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD`
- Candidate `main.py`: `2B23D3AFC63A5BDC4BC7765CE1656725ED01890D161E3D23DCC672BE7FCCCFF4`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Only candidate `main.py` differs. The other 11 package entries are byte-identical.

## Behavioral intent

`PUBLIC_POKE_PAD_DECLARED_EXECUTABLE_ROLE_TRANSACTION_V1` replaces the old
PFC Pad watch. It declares either `DURALUDON_EXECUTABLE_SUCCESSOR` or the
narrow exact-KO form of `NONEX_COATED_ATTACK_CONVERSION` before emitting the
parent-selected Pad. The physical target serial is bound only on the reveal.
Absent targets choose `[]` only when legal and rebind the frozen exact attack
on the next MAIN. Cinderace is explicitly setup-only and never substituted.

## Exact verification commands and outcomes

1. `py -3.11 -B -c "from pathlib import Path;p=Path('main.py');compile(p.read_text(encoding='utf-8'),str(p),'exec');print('compile_ok')"`
   - Exit `0`, `compile_ok`.
2. `py -3.11 -B run_focused_fixtures.py`
   - Exit `0`, `69/69` passed.
   - Both seats complete Pad/Duraludon/Turbo/Energy/target/completion and
     Pad/840/hand/evolve/Coated/completion lifecycles.
   - Covers duplicate/permutation, lowest serial, equivalent and conflicting
     duplicates, legal whiff, Cinderace-only whiff, terminal/unknown terminal,
     existing and callback owners, full/capacity loss, effect/source,
     seat/turn/result/action-count, malformed reveal, no-purpose nonex, and
     double-owner cleanup.
3. `py -3.11 -B run_replay_shadow.py`
   - Exit `0`; episode `89347400`, correct seat `1`, 11 decisions, 0 invalid
     actions, 0 parent-candidate differences, 0 Task-5-specific differences.
4. `py -3.11 -B verify_structure.py`
   - Exit `0`; AST final callable `agent`, import callable, 12 entries,
     legal 60, ACE SPEC 1, other-file mismatches 0, cache entries 0.
5. `py -3.11 -B tools\run_local_battle.py --engine-dir <candidate> --agent-a <candidate> --deck-a <candidate>\deck.csv --agent-b <historical-silver> --deck-b <historical-silver>\deck.csv --games 1 --max-steps 1000 --seed-base 20260802 --no-trace --summary <implementation>\engine_smoke_seat0.jsonl`
   - Exit `0`; 128 steps, action errors 0, max-step hit false.
6. `py -3.11 -B tools\run_local_battle.py --engine-dir <candidate> --agent-a <historical-silver> --deck-a <historical-silver>\deck.csv --agent-b <candidate> --deck-b <candidate>\deck.csv --games 1 --max-steps 1000 --seed-base 20260803 --no-trace --summary <implementation>\engine_smoke_seat1.jsonl`
   - Exit `0`; 140 steps, action errors 0, max-step hit false.

The first smoke attempts included `--engine-seed`; both exited `1` because the
checked package's existing `battle_start` wrapper does not accept `seed=`.
The successful commands above retain Python-side seed labeling and omit the
unsupported engine-seed switch.

## Replay coverage and known tradeoffs

- Root later located and checked episodes `89285518` and `89282820` under the
  `55155015` analysis snapshot. The checked comparator replayed 74 and 60
  target-seat decisions respectively; parent and candidate were identical at
  every decision (`difference_count = 0`).
- Static replay snapshots do not prove multi-callback continuity. The focused
  engine-shaped fixtures provide that proof for both admitted roles and seats.
- The nonex role deliberately admits only exact same-turn Coated KO conversion;
  defensive/prevention-only nonex searches remain inherited-parent behavior.
- The Cinderace Duraludon role is deliberately limited to an empty Bench; the
  nonempty case requires the exact public no-backup proof on Duraludon Active.
- No archive was created and no Kaggle operation was performed.

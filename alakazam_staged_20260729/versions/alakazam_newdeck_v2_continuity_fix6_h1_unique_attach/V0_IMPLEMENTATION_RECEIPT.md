# V0 implementation receipt

## Scope and behavioral intent

- Baseline: `autonomous_gold_20260715/candidates/alakazam_active_dudunsparce_run_away_ko_transaction_v4`.
- Destination: `alakazam_staged_20260729/versions/alakazam_newdeck_v0_port` only.
- Port the exact v4 deterministic policy from normalized deck hash `f2e179fb82cb91504ccd207d707ca5e7be8afc7228df26a7b287c6205064507c` to normalized deck hash `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` without adding a new setup, energy, Hand Power, attacker, matchup, or tactical rule.
- `1184`, `1197`, and `1266` are registered in `V0_GENERIC_HOLD`. Their voluntary MAIN `PLAY` score is explicitly `-1` with reason `V0_GENERIC_HOLD`, so they are not mistaken for the old unknown-Trainer score of `10000`.
- If one of those held cards is exposed as a legal `CARD` option in a forced `DISCARD` prompt, it receives score `1` with reason `V0_GENERIC_FORCED_DISCARD`. All other prompts and cards keep the inherited ordering.
- The sole `main.agent` wrapper records callback-visible evidence in `LAST_V0_PORT_TRACE` only after the inherited policy returns. It tags legal added-card MAIN plays as `V0_GENERIC_HOLD`, tags only selected added-card forced discards as `V0_GENERIC_FORCED_DISCARD`, copies the selected action for observation, and returns the inherited action object unchanged.
- Removed own-deck IDs remain named at count zero because opponent/public semantic checks still refer to some of them. Their strategic branches are unreachable from this deck.

## Files changed or added

- `_cumulative_parent.py`: deck-count constants plus the isolated generic hold/forced-discard scoring gate.
- `main.py`: behavior-neutral callback sidecar populated after action delegation.
- `deck.csv`: exact requested 60-card deck.
- `runtime/deck.csv`: byte-identical runtime copy required by the checked paired runner, which resolves `<policy_dir>/deck.csv`.
- `runtime/main.py`: dynamic sidecar getter and module attribute exposure.
- `test_v0_port.py`: deck/hash/metadata, policy tags, action-identity delegation, callback tagging, runtime exposure, deck parity, and unchanged-shared-source checks.
- `verification/smoke_p0/*`, `verification/smoke_p1/*`: raw local smoke summaries and traces.
- `V0_IMPLEMENTATION_RECEIPT.md`: this receipt.

Every baseline Python file other than `_cumulative_parent.py`, `main.py`, and `runtime/main.py` is byte-identical in the destination. The two entrypoint changes are sidecar-only and do not alter the delegated action.

## Verification commands and outcomes

Run from the destination with the packaged v4 `cg` directory on `PYTHONPATH`:

```powershell
@'
from pathlib import Path
paths = sorted(Path('.').glob('*.py')) + sorted(Path('runtime').glob('*.py'))
for path in paths:
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print('COMPILE_OK', len(paths))
'@ | py -3.11 -B -
```

Outcome: `COMPILE_OK 32`.

```powershell
py -3.11 -B -m unittest -v test_v0_port.py
```

Outcome: 7 tests ran and all passed. The tests verify 60 rows, exact counts, normalized hash, one ACE SPEC, the three new metadata types, explicit hold and forced-discard reasons, unchanged delegate action identity, callback trace tagging, dynamic runtime exposure, runtime-deck equality, and byte equality of all unrelated shared Python.

Smoke p0 command, run from repository root:

```powershell
py -3.11 tools/run_local_battle.py --engine-dir submission_archaludon --agent-a alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/runtime --deck-a alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/deck.csv --agent-b submission_archaludon --deck-b submission_archaludon/deck.csv --games 1 --max-steps 1000 --seed-base 2026101741 --summary alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/verification/smoke_p0/summary.jsonl --trace-dir alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/verification/smoke_p0/traces
```

Outcome: exit 0, result 1, 143 steps, 0 action errors, no max-step hit. Result is the engine winner index; this smoke is structural, not promotion evidence.

Smoke p1 command, run from repository root:

```powershell
py -3.11 tools/run_local_battle.py --engine-dir submission_archaludon --agent-a submission_archaludon --deck-a submission_archaludon/deck.csv --agent-b alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/runtime --deck-b alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/deck.csv --games 1 --max-steps 1000 --seed-base 2026101741 --summary alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/verification/smoke_p1/summary.jsonl --trace-dir alakazam_staged_20260729/versions/alakazam_newdeck_v0_port/verification/smoke_p1/traces
```

Outcome: exit 0, result 0, 146 steps, 0 action errors, no max-step hit. Result is the engine winner index; this smoke is structural, not promotion evidence.

## Final hashes

- Normalized deck SHA-256: `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`.
- `deck.csv` and `runtime/deck.csv` raw SHA-256: `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`.
- `_cumulative_parent.py`: `71D884F3545372B246AB7B7F76B9209A49C3544D3DB93496B4D3D6A1880DEFC1`.
- `main.py`: `6FD9519ED9805901F6E14C0F9D56B13E462E92A72DBE73BF878E21EB1D330ACD`.
- `runtime/main.py`: `62FDCAC6A831F0F26EE85C6D64E5C6E4924BF55AD149E2A94C673F1F2BF0E629`.
- `test_v0_port.py`: `58F723FB15C234EE27B12A677F44DC2106D5391D199123231870AC278E1C2210`.
- p0 summary: `A5E6583485DBB2D15490CCCE6D3812AB57CA2EE965E3F238CF81388D16327D3B`.
- p1 summary: `B886A5C0B90CDE02ABDE20E6982ED0BF3A4820EFEB1A411BC4F91ECCFFD5C8B0`.
- Frozen `PACKAGE_MANIFEST.json`: `24C1E8995FA0C7A64A8FEBFBEA9E422D8ACBFD5A8454A6D5F559881521978C57`.
- Frozen `build_and_verify_package.py`: `33629A00C02AD7451B91B8FB9B0429452DA569ADF7D144BDFD03E7FBF3306B67`.

No archive was created.

## Known tradeoffs and evaluator checks

- This is intentionally a behavior-preserving port. Lana's Aid, Xerosic's Machinations, and Nighttime Mine are never voluntarily played, so their strategic upside is deliberately forgone.
- A forced discard prompt prefers those unsupported held cards over inherited score-zero choices. This is deterministic and legal, but is not a strategic discard optimizer.
- `LAST_V0_PORT_TRACE` is a mutable last-callback sidecar for observability only. It is not transaction state, is never read by policy scoring, and is overwritten on each completed callback.
- The removed Genesect, Psyduck, Lucky Helmet, Handheld Fan, and Battle Cage own-deck routes cannot fire. Legacy identifiers and public semantic checks are retained so an opponent showing those cards does not become unknown.
- For the checked paired runner, pass `alakazam_newdeck_v0_port/runtime` as the policy directory. `runtime/deck.csv` is present and byte-identical to the root deck, while `runtime/main.py` changes cwd to the candidate root before importing the policy.
- The evaluator should cover both seats and identical seeds, confirm zero invalid actions/exceptions/unhandled prompts, include a state where each held card is a legal MAIN play, include a forced DISCARD prompt containing at least one held card, and verify candidate actions remain identical with sidecar observation enabled.
- Packaging, if later performed by the parent, must exclude `test_v0_port.py`, `verification/`, `runtime/`, `frozen_submission/`, and this receipt unless the package builder explicitly expects them. The inherited clean archive had 42 entries; no new package was built here.

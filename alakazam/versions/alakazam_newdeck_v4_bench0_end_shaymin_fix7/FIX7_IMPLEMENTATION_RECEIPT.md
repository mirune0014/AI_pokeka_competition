# Fix7 implementation receipt

## Scope and behavioral intent

- Baseline: `alakazam_staged_20260729/versions/alakazam_newdeck_v4_public_survival_bench0_fix5`.
- Isolated destination: `alakazam_staged_20260729/versions/alakazam_newdeck_v4_bench0_end_shaymin_fix7`.
- Rule: `BENCH0_END_SHAYMIN_EMERGENCY_FIX7`.
- The inherited broad C3 ATTACK/damage decision path is not called by the outer wrapper. The only non-parent action is the exact legal physical Shaymin `343` PLAY when the complete parent selected semantic END and every required live-MAIN, raw/parsed parity, Active/Bench, transaction, physical-card, option-uniqueness, and Prize-effectiveness guard passes.
- Every initial nonmatch returns the complete parent action object unchanged. The wrapper snapshots and restores the complete parent state before arming.
- A duplicate callback is rebound only by exact Shaymin card ID and serial. A distinct MAIN must prove the exact same-turn Hand-to-Bench movement with unchanged Active and no unrelated public mutation.
- Natural reentry END completes normally. A differing natural reentry records a semantic mismatch and may rebind saved END only if END is currently unique/legal and restoration of the saved complete-parent state is exact. Missing END, movement failure, callback-shape failure, or any parent transaction fails closed to the current complete-parent action and never reuses a stale option index.
- The rule resets on the deck handshake/game boundary.

## Files changed or added

- `planner_public_survival_bench0.py`: narrow Fix7 gate, Prize-liability allowlist, exact physical Shaymin option binding, parent-state restoration audit, and fail-closed duplicate/reentry transaction handling.
- `bench0_end_shaymin_observed_manifest.json`: all 17 root-verified END reaches classified as 4 positive, 3 transaction-negative, and 10 Prize-futile-negative rows, including source hashes and expected fire/refusal.
- `test_v4_bench0_end_shaymin_fix7.py`: 23 focused tests for the four fixed positives, Kanga/Crustle existing-win reach, the specified negatives, exact action identity, broad-C3 exclusion, duplicate/reentry behavior, and game reset.
- `test_v4_public_survival_bench0_fix5.py`: replaces the superseded broad action-change expectations with three regressions proving the old observed ATTACK action and preceding parent actions are unchanged and that the broad evaluator is not invoked.
- `test_v4_next_attacker_distance_shadow_fix4b.py`: updates three wrapper-name assertions to the destination rule constant; C2 behavior assertions are unchanged.
- `FIX7_IMPLEMENTATION_RECEIPT.md`: this receipt.

No deck, entrypoint, parent policy, runtime loader, frozen submission, or file outside the destination was edited.

## Immutable source evidence

- Reach audit SHA-256: `152F230A5E3D55C280CBA3F4A64FC8E87AC3DA1C3A741F5AF6B14FFEE93A42C2`.
- Root-verified row CSV SHA-256: `11692093A46A33FDDAEE037DBCCA193B1C4E300C59EAFA50380FDD0A19018DEB`.
- 17-row END-reach input SHA-256: `0C5F0DE8BD940A8B557C1D9C6C94B403E6DFBFE7A19EF4F67EECCB7FAAC33E7D`.
- Destination manifest SHA-256: `086BCA09DAB2B941029BBB00C947C12B711BE80152266885DCB35950A8B64E63`.
- Policy source SHA-256: `779A3F47ECBB352C688320A7D3EC1EC2FD6A9C56A11D5867D5F141BB678AFD0A`.
- Runtime policy closure SHA-256: `575B3F524AD007D0CA055B0647A03DD363C8FB06CEC028E29AA10460CBBECE5B`.

## Verification commands and raw outcomes

All Python commands used Python 3.11 with:

```powershell
$env:PYTHONPATH=(Resolve-Path '../../submissions/alakazam_newdeck_v4_c2_safe_final_20260730/runtime_smoke_extract').Path
```

Focused rule tests:

```powershell
py -3.11 -B -m unittest -v test_v4_bench0_end_shaymin_fix7.py
```

Outcome: exit `0`; `Ran 23 tests in 0.043s`; `OK`.

Full candidate regression:

```powershell
py -3.11 -B -m unittest discover -p 'test_*.py'
```

Outcome: exit `0`; `Ran 259 tests in 3.214s`; `OK`.

Compile check, including all top-level, runtime, and verification Python:

```powershell
@'
from pathlib import Path
from tokenize import open as tokenize_open
paths = sorted(Path('.').glob('*.py')) + sorted(Path('runtime').glob('*.py')) + sorted(Path('verification').glob('*.py'))
for path in paths:
    with tokenize_open(path) as handle:
        compile(handle.read(), str(path), 'exec')
print('COMPILE_OK', len(paths))
'@ | py -3.11 -B -
```

Outcome: exit `0`; `COMPILE_OK 52`.

A preliminary compile helper using `Path.read_text(encoding='utf-8')` exited `1` on the inherited BOM in `main.py` (`U+FEFF`). `tokenize.open`, which follows Python's source-encoding rules, was then used for the recorded successful 52-file compile. This was a check-harness issue, not a source edit or runtime failure.

Deck validation:

```powershell
@'
import csv, hashlib
from pathlib import Path
path = Path('deck.csv')
rows = [row for row in csv.reader(path.open(newline='', encoding='utf-8')) if row]
cards = [int(row[0]) for row in rows]
print('DECK_ROWS', len(cards))
print('DECK_COLUMNS_EXACT_ONE', all(len(row) == 1 for row in rows))
print('DECK_SHA256', hashlib.sha256(path.read_bytes()).hexdigest().upper())
print('RUNTIME_DECK_BYTE_EQUAL', path.read_bytes() == Path('runtime/deck.csv').read_bytes())
'@ | py -3.11 -B -
```

Outcome: exit `0`; `DECK_ROWS 60`; `DECK_COLUMNS_EXACT_ONE True`; deck SHA-256 `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`; `RUNTIME_DECK_BYTE_EQUAL True`.

Runtime handshake smoke:

```powershell
@'
import importlib.util
from pathlib import Path
path = Path('runtime/main.py').resolve()
spec = importlib.util.spec_from_file_location('_fix7_runtime_smoke', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
deck = module.agent({'select': None, 'current': None})
assert len(deck) == 60
assert deck == module._source_module._c3_survival.exact_deck()
print('RUNTIME_HANDSHAKE_SMOKE_OK', len(deck), module._source_module._c3_survival.RULE_VERSION)
'@ | py -3.11 -B -
```

Outcome: exit `0`; `RUNTIME_HANDSHAKE_SMOKE_OK 60 BENCH0_END_SHAYMIN_EMERGENCY_FIX7`.

Baseline/destination byte inventory, excluding caches, bytecode, and receipts:

```text
ADDED 2
  bench0_end_shaymin_observed_manifest.json
  test_v4_bench0_end_shaymin_fix7.py
REMOVED 0
CHANGED 3
  planner_public_survival_bench0.py
  test_v4_next_attacker_distance_shadow_fix4b.py
  test_v4_public_survival_bench0_fix5.py
UNCHANGED 62
BASELINE_IMPLEMENTATION_TREE_SHA256 AD91DFE6A5DFBD651505ABB6D52FB11FD58DDE819605484486C993DB5B0788E9
CANDIDATE_IMPLEMENTATION_TREE_SHA256 AC567CA4D6D40715D51C59FD94BAA57A16BEDADC0A59CA53FC0A7D4F04CE9AC4
```

The implementation-tree hashes exclude files ending in `_RECEIPT.md`, so adding this receipt does not change the recorded candidate closure.

## Archive and external writes

No archive was created. No Kaggle API, upload, submission replacement, Notebook/Discussion publication, or external write was performed.

## Known tradeoffs and evaluator obligations

- The manifest preserves the 17 observed fingerprints and their root-verified classifications without copying large raw logs. Focused fixtures reconstruct the required public state from the verified Active liability and Prize fields; they are not a claim that the unexecuted counterfactual improved the game outcome.
- The saved-END recovery intentionally restores the original complete-parent post-state when exact restoration succeeds, even if the natural parent reentry would choose another legal action; the trace records `FULL_POLICY_SEMANTIC_REENTRY_MISMATCH`.
- The evaluator must replay the four positive observed fingerprints, both seats on identical seeds, and confirm exact Shaymin Hand-to-Bench completion, no action errors, no stale-index use, and no regressions in adjacent matchups. It must separately confirm that the three parent-transaction rows and ten Prize-futile rows remain exact-parent refusals.
- No strength, promotion, or adoption conclusion is claimed.

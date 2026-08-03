# Root initial direct-parent copy verification

Verification time: 2026-07-30 05:51:55 JST.

Candidate:
`autonomous_gold_20260715/candidates/archaludon_persistent_public_boss_access_ledger_last_copy_guard_v1`

Formal parent:
`analysis_outputs/reference_agents/historical_silver_archaludon_54495224`

Before the implementation worker edited the candidate, Root recursively
enumerated every non-cache runtime file in the formal parent and candidate,
computed SHA-256 for each relative path, and compared the two inventories.

- parent runtime files: `12`
- candidate runtime files: `12`
- missing files: `0`
- extra files: `0`
- differing files: `0`
- parent/candidate `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- parent/candidate `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

The compared inventory was:

1. `deck.csv`
2. `main.py`
3. `requirements.txt`
4. `cg/api.py`
5. `cg/cg.dll`
6. `cg/game.py`
7. `cg/libcg-arm64.so`
8. `cg/libcg.dylib`
9. `cg/libcg.so`
10. `cg/sim.py`
11. `cg/utils.py`
12. `cg/__init__.py`

This proves that the isolated destination began as an exact cache-free copy
of historical-Silver. It does not validate subsequent source edits; Root must
later verify that only `main.py` changed and that every other runtime member
remains byte-identical.

# Counterfactual root-action search harness v1 (MVP)

This is an offline diagnostic harness.  It does not change, wrap, or package
the accepted Archaludon agent and it does not submit to Kaggle.

The first MVP does one thing:

1. reconstruct a recorded agent observation from a replay;
2. verify a small `ROOT_VALID` contract;
3. run the accepted parent once as a baseline and once again as a parity
   control;
4. replace one root action with one legal semantic alternative; and
5. return control to the unchanged parent agent for every later prompt.

The engine receives fixed placeholder hidden-world cards only to make the
counterfactual rollout executable.  They are never passed to the parent agent
for action selection and are recorded in the report.  The replay's
`visualize` field is never read by the extractor.

## Files

- `extract_roots.py`: choose a small root manifest from replay observations.
- `run_branch.py`: execute one root branch in a fresh process.
- `run_search.py`: run parent A/B parity and alternatives, then aggregate.
- `common.py`: hashes, action validation, and public observation helpers.

Generated outputs belong outside tracked source, for example:

```text
_local_generated/analysis_outputs/
  archaludon_counterfactual_root_action_search_mvp_v1/<run_id>/
```

No result from this harness is an instruction to modify the accepted agent.

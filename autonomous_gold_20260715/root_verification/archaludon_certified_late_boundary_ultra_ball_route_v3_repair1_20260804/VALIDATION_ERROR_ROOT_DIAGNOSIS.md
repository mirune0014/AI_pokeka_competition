# Rule3 v3 repair1 validation error diagnosis

## Outcome

The failed archive did not reach game play. Its `main.py` used `__file__` at
module startup. Kaggle Environments executes submission source with
`env = {}` and therefore does not define `__file__`.

Root reproduced the checked loader boundary exactly:

```text
NameError: name '__file__' is not defined
```

The failing statement was the candidate-directory path setup before the
Historical-Silver helper import. This is a deployment defect, not Rule3 game
logic or local strength evidence.

## Why the prior package check missed it

The previous verifier loaded `main.py` with `importlib.util`. Ordinary import
sets `__file__`, so that check could not expose Kaggle's raw-source execution
boundary. The checked Kaggle Environments 1.14.11 loader instead compiles the
raw source, appends the execution directory to `sys.path`, and executes it in
an empty dictionary.

## Minimal repair

The candidate-directory insertion now runs only when `__file__` exists:

```python
if "__file__" in globals():
    _CANDIDATE_DIR = _os.path.dirname(_os.path.abspath(__file__))
    if _CANDIDATE_DIR not in _sys.path:
        _sys.path.insert(0, _CANDIDATE_DIR)
```

Kaggle already appends the archive extraction directory, so the sibling
`_historical_silver_parent.py` import remains available there. Normal local
imports retain the guarded path setup. No rule body, resolver decision, deck,
parent, or engine file changed.

## Verification

- Exact raw execution with no `__file__`: PASS twice.
- Kaggle dictionary-order selection: final callable `agent` twice.
- Both validation-seat deck handshakes: 60 cards, identical deck, one Hero's
  Cape ACE SPEC.
- Packaged same-source mirror: two completed games, zero action errors and
  zero max-step hits.
- Stage/extracted archive hashes: 13/13 identical.

Fixed `main.py` SHA-256:
`D95D1218587FEE59BE43B433F02BB73F928E4DE9A2F7BEAA670F4CF60783A19C`.


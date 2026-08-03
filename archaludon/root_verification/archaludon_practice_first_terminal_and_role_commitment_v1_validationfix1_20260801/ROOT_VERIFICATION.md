# Root verification: validation fix 1

> Superseded and rejected after Kaggle submission `55154934`.  The named-agent
> deck request was fixed, but the package did not preserve Kaggle's required
> last-callable insertion order.  See
> `autonomous_gold_20260715/live/55154934/VALIDATION_ERROR_ROOT_DIAGNOSIS.md`.

This candidate is the exact practice-first source rejected as Kaggle
submission `55154818`, plus one deck-request boundary repair.  Gameplay logic
is unchanged.

- Rejected source SHA-256:
  `5A0F4BE26EE0AB0B05200A4640301141F58CDDDAD1750D65EA2D1986CE52E7B5`
- Repaired source SHA-256:
  `F7CFCC5C1C77E08062AC87404D2C10FF86769264EE17DD1B7F870A72D1071872`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Repair archive SHA-256:
  `3ED2B9D7460CDC1CA808F46778E48C96BB01131C639FD6A4199C3DAF79D96B0B`

The final wrapper now returns the inherited parent response immediately when
the converted observation has `current is None` or `select is None`.  The new
cache is cleared first.  Root reproduced the prior AttributeError before the
edit, then invoked the repaired source twice with the exact Kaggle step-0
shape.  Both calls returned exactly the 60 IDs in `deck.csv` and left the
cache clear.

Compile/import, parent-prefix identity, final-loader entrypoint, existing nine
focused positives/holds, four negatives, and cache-free checks still pass.
No battle or broad shadow was rerun because the edit is unreachable in a live
game state.

The clean archive contains 12 runtime files.  Extracted source/deck hashes
match the frozen values, and two exact deck-request calls on the extracted
package return the correct 60-card list.

Original prewrite decision: `PASS_FOR_VALIDATION_RETRY_AND_LIVE_PROBE`.

Controlling post-validation decision:
`REJECT__KAGGLE_LAST_CALLABLE_WAS_HELPER`.

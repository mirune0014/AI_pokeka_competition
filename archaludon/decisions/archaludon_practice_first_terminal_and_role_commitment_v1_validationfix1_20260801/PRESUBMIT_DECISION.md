# Presubmit decision: validation fix 1

Submit exactly one repaired artifact after a fresh Kaggle refresh:

`autonomous_gold_20260715/packages/archaludon_practice_first_terminal_and_role_commitment_v1_validationfix1_clean_20260801_1449/submission_archaludon_practice_first_terminal_and_role_commitment_v1_validationfix1_20260801.tar.gz`

Archive SHA-256:
`3ED2B9D7460CDC1CA808F46778E48C96BB01131C639FD6A4199C3DAF79D96B0B`.

The previous write consumed one slot but produced no game.  It failed only on
the Kaggle-specific deck-request callback, which is now reproduced and fixed.
The two gameplay hypotheses and every focused gameplay result are unchanged.
Do not resubmit the rejected archive `E8F735...F45B4E1`.

Decision: `SUBMIT_VALIDATIONFIX1_ONCE`; verify the new row before any retry.

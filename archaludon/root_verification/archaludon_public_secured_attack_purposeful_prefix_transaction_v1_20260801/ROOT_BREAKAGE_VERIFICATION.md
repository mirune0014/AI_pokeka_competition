# Root breakage verification

## Frozen sources

- Candidate: `archaludon_public_secured_attack_purposeful_prefix_transaction_v1`
- Candidate `main.py` SHA-256:
  `B1DA0A9C04205DEA4B391B861B5A0199D852AA70F7F5D2ACB3A47CEA3BE7A7F1`
- Direct live parent `main.py` SHA-256:
  `6D890336EB50CAA0E26CBD75BE5A2FA94FEB09AC131DCE2AF57200858888AFF8`
- The first `1,049,690` candidate bytes are exactly the complete parent.
- Candidate deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Deck has 60 rows and exactly one ACE SPEC.

## Rule behavior

The appended wrapper keeps the two submitted live rules and adds one unified
purpose-first turn boundary:

1. With one exact payable nonterminal attack, a direct nonattack prefix is kept
   only when it has a concrete public purpose and preserves the intended attack.
2. Purpose includes board-out prevention, first executable backup,
   attack-completing or next-attacker Energy, and exact survival/return gain.
3. Non-ex evolution is no longer accepted or rejected from its old fixed score.
   It replaces a chip attack only when transferred damage, the exact public
   reply, Prize timing, payable Coated Attack, and continuity jointly prove a
   survival or board-out improvement.
4. Existing inherited transactions remain owner-dominant. Unsupported public
   effects fail closed to the parent.

The live negative `89274803/seat1/row119` remains Hammer In. Evolving there
would still be KOed by the exact reply and would lose the 30 damage and the
evolution card. Synthetic exact KO-to-survive and payable-Coated-versus-Basic
positives do choose the non-ex evolution. Immediate-Prize conversion remains
attack-first.

## Minimal root gate

The user explicitly requested practical live probing rather than proof-heavy
local evaluation. Root therefore did not run a replay matrix or local win-rate
suite.

- Root reran the focused verifier: exit `0`.
- Six direct-prefix fixtures and four defensive-evolution fixtures passed.
- Both inherited live rule results, duplicate/reorder equivalence, and owner
  holds passed.
- Focused results SHA-256:
  `311600F0B9A1BCBC0349B8178FF87D7AF2AC985628ECD3C172B7DCC206567B36`
- Implementation report SHA-256:
  `3606FC38E4653DCDBBA07F28348B98004C36C765C34CEC9F40FEC39026F50C17`

The clean archive was extracted and loaded in isolation. Kaggle-style
insertion-order selection found exactly the last callable `agent`, signature
`(obs_dict)`, identical to `module.agent`. Two exact null-selection deck
requests returned the 60 deck IDs. The extracted tree has 12 runtime files,
zero cache directories, and zero `.pyc` files.

Packaged both-seat one-game smokes completed in 30 and 53 steps with zero
action errors and no max-step hit. Their SHA-256 values are:

- candidate as player 0:
  `E594B3AAD1A71936248335092E07EFBF8E7905C528739B60D441F8BB795710B2`
- candidate as player 1:
  `E9D8F3F82DD4623A19822569E92BA68396C1D44DB541ACDCDB353CCE32F8890F`

## Package

- Archive:
  `autonomous_gold_20260715/packages/archaludon_public_secured_attack_purposeful_prefix_transaction_v1_clean_20260801_1529/submission_archaludon_public_secured_attack_purposeful_prefix_transaction_v1_20260801.tar.gz`
- Archive SHA-256:
  `B28EBCC31C62E6FC3C5E78AF2B23634DF8B644C52C89722BAEDF537EC6E24FD7`
- Archive size: `2,177,498` bytes.

Decision: `PASS_BREAKAGE_GATE_AND_PACKAGE_READY`. Strength is deliberately left
to the practical live probe; the package must not be submitted before the
configured live-cadence and prewrite Kaggle refresh.

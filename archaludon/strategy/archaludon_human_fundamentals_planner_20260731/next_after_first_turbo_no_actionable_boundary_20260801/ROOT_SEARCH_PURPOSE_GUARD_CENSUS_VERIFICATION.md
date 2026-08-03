# Root verification: secured-attack Pokémon-search purpose guard

Decision: `STOP__PUBLIC_SECURED_ATTACK_SEARCH_GUARD_NOT_BROADLY_ACTIONABLE`

The fixed pre-edit gate failed. No candidate source, local matchup evaluation,
package, or Kaggle write follows from this hypothesis.

## Bound evidence

- strategy: `6D98BF4300BC059F1E7E7B9EA31FD98CBCE15CA68510DBF168F2DB26A2F7E69A`
- execution specification: `4D5FEEDCAA4735992445779E8368BFEE060AB7BF0AFC5DB962A0CDBC31D7EE77`
- frozen runner: `A60CDB559DBC0BC6B985654B3BCDC499F2C6D712F7795526D7DC190EE77803F8`
- independent Sol-Ultra audit: `601F450101ADB7C9DB980D025E371936B1A4A382F8E51AAB2777150B7AB7B48D`

Root recomputed these raw hashes:

- orientation rows: `87045C92E614054024FEACACAEA92E8485DF4299BC7F26C445696ECF9FE159A7`
- parent-search callback rows: `4996A46D1C221B230D99A6C0E0C21156179489E74935CB7F3A92826C8193A008`
- predicted differences: `5603076F28701487112A057D20C9FDD5FD9E149E3F83BDD3D981127B5D59AA5A`
- copied manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- summary: `76B38A7E269FE2C2C2D32091949D025B3948A127C66930A0A4BE09D2A0AA2FCC`

## Root recomputation

- manifest: 207 replay files, 209 target seats
- parent calls and unique raw keys: 25,880 / 25,880
- orientation surface: 2,017 unique snapshots, 636 turns, 180 replays,
  both seats; this exactly reproduces the prior read-only orientation
- orientation retries collapsed after semantic equality: 305
- parent-selected searches: 601 unique callbacks; Poké Pad 371 and Ultra Ball
  230; both seats
- classifiable rows: 71, representing only 54 turns and 36 replays
- predicted differences: 4 rows, 3 turns, 3 replays, both seats
- predicted families: Poké Pad 3, Ultra Ball 1
- all four predictions are a unique exact `Metal Defender` terminal attack in
  place of the selected search action
- owner holds: 41
- invalid parent actions: 0
- invalid predicted contract actions: 0
- hidden-information use in predictions: 0
- owner collisions in predictions: 0
- semantic-copy predictions: 0
- predicted errors: 0

The immutable gate required at least 80 classifiable turns over 50 replays, 24
differences over 16 replays, and at least eight differences from each search
family. The observed 54/36, 4/3, and 3/1 fail every relevant floor.

## Recorded raw-schema discrepancy

The runner classified 69 rows as `PURPOSE_HOLD`. Of these, 67 are marked
classifiable. In all 67 classifiable rows the serialized `contract_action` and
`contract_semantic` still contain the provisional attack rather than the exact
parent search, while `predicted_difference` is `False`. Therefore they are not
literal parent-equal controls in the raw file. Only two unclassifiable hold rows
happen to be semantically parent-equal, and neither may be used to satisfy the
purpose-control gate.

The runner summary's count of 67 purposeful controls is a classification count,
not a valid parent-equal-control count. The independent evaluator flagged this
discrepancy, and the root verified it directly. It is not repaired silently.
Because the prediction and eligible-surface gates already fail decisively, a
corrected rerun cannot authorize this hypothesis and would not be a justified
use of further execution time.

## Useful residue

The four differences expose a broader and cleaner defect: the parent can select
a nonessential MAIN action even when one unique public attack wins the game
immediately. That fact does not authorize this stopped search-specific rule.
It may support a new, independently frozen hypothesis covering unique terminal
attack dominance across all MAIN action families.


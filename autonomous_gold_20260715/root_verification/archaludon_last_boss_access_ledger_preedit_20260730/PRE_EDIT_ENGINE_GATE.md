# Last-public-Boss ledger pre-edit engine gate

Decision:
`PREEDIT_GATE_PASS__AUTHORIZE_ONE_ISOLATED_DIRECT_PARENT_IMPLEMENTATION`

- Rule: `PERSISTENT_PUBLIC_BOSS_ACCESS_LEDGER_WITH_PLAN_EQUIVALENT_LAST_COPY_DISCARD_GUARD_V1`
- Source: episode `88819392`, rows `119-123`, source seat `0`
- Parent SHA-256: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Replay SHA-256: `4D625ADF892F1D0DC1453E31219025A96C4474D509E5B1E36819225A22F22698`
- Engine tree SHA-256: `D92046EC9B88AF6CD7A0301DD6E7E8D158A6C8069BFB355A0436409417B3AE36`
- Runner SHA-256: `63421315C9ACC6F7A32C262E57478905EE9862F8D2785A8D04459D0B469F8111`
- Raw output SHA-256: `8B301A28F17EC258CA77F5FCC9F3E32039825E963D5A1C5540FA4227BED62014`

The exact source state was executed as two engine branches in eight
configurations: both logical seats, serial remapping, reversed discard
options, equivalent duplicate discard options, and deterministic repeated
selection. There were `16` total branch runs.

The parent branch discarded Boss `1182#39` plus Basic Metal `8#57`. The
alternate branch discarded non-ex Archaludon `840#31` plus the same Metal,
retaining Boss. After that irreversible difference, unmodified exact
historical-Silver selected the same Duraludon, Benched it, and selected Metal
Defender `253`. Search, board formation, attacker, attack target, damage,
Prize result, and turn progression were identical in every comparison.

No invalid action, action error, exception, nondeterminism, stale state, or
max-step hit occurred. This gate authorizes one isolated direct-parent
implementation of the frozen ledger/discard contract. It does not authorize
packaging, Kaggle submission, formal-parent adoption, or a claim that a later
Boss converts the source match.

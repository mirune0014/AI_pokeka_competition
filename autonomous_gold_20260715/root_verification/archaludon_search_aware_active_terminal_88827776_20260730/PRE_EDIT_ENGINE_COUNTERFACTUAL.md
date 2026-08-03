# Pre-edit engine counterfactual

Decision:
`PREEDIT_GATE_PASS__AUTHORIZE_ONE_ISOLATED_DIRECT_PARENT_IMPLEMENTATION`

- Rule: `SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1`
- Source: episode `88827776`, callback `134`, logical seat `1`
- Parent SHA-256: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Replay SHA-256: `7B3D23A6F04179A10E6B972033D8D84151FDBD81FB6D6AB47AC3D6129DBADD8A`
- Engine tree SHA-256: `D92046EC9B88AF6CD7A0301DD6E7E8D158A6C8069BFB355A0436409417B3AE36`
- Runner SHA-256: `4CBE9B8FAE4739EEF43F37B54A50BA9AA0BECCF25C841CF116C0360F7CB374E7`
- Raw output SHA-256: `0EFAB0FECAB5FFAEFE904322C79ACD762A5069E08AE6671D0FEC34E91BB03CF4`

The unchanged Mega Lucario ex received exact Metal Defender `220` and the
three remaining Prizes were taken in the same turn in all
`8` engine cases. These cover both logical seats, serial
remapping, option reversal, equivalent duplicate options, and deterministic
repeated callback selection.

Public-only access reproduced `D=8`, `P=3`, `U=3` and
`P(hit)=164/165`
(`0.993939393939`), above the frozen `0.99` threshold.

Both matched search-miss fixtures placed all three unidentified Archaludon ex
in Prizes while preserving the same public model. The route retained two Boss
copies, cleared at the public miss, delegated exact historical-Silver from the
irreversible state, and reached a legal parent Boss action in both seats.

Missing evolution, changed target, changed Prize, changed modifier, and
post-search attack illegality all produced deterministic fail-closed parent
delegation. No invalid action, action error, exception, stale state,
nondeterminism, or max-step hit occurred.

This gate authorizes one isolated direct-parent implementation. It does not
authorize packaging, live submission, or formal-parent adoption.

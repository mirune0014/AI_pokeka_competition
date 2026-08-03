# Deferred loss memo — episode 88825590

Status:

`ROOT_VERIFIED_PUBLIC_KO_CONVERSION__MATCH_CAUSALITY_UNPROVED__H5V2_COVERAGE_GAP`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
the exact historical-Silver parent were identical across all 44 correct-seat
callbacks, with zero Hero starts, action differences, invalid actions,
exceptions, or stale transactions.

- replay SHA-256:
  `E80A121C57B0CCA51C6ABBCD5070B6437145185AE41FC502C64709269280F4AC`
- Hero shadow SHA-256:
  `F293C017FA890EDBB4A8B86181D601CE2E7A5CE8C40A7D0A6E9951F81620270E`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_cape_nonex_lethal_evolution_88825590_20260730/verify_cape_nonex_lethal_evolution.py`
- verifier SHA-256:
  `8B1164A16E8F7F0118F1CF49E5F954AC4CB18899458955994D35D0FD928E503B`
- output:
  `root_verification/archaludon_cape_nonex_lethal_evolution_88825590_20260730/root_verification.json`
- output SHA-256:
  `381A69283FDAEF766E22B9CC638328E96F6EC7CDB912E99B2C3AC882AEB1DC4F`

## Root-verified public transition

At row `59`, turn `6`, our Active was Duraludon `169#3`, `230/230` through
Hero's Cape, with exactly three Basic Metal Energy. The opponent's Active
Alakazam `743#86` had `110` HP remaining.

The legal relevant choices were:

- evolve the Active with non-ex Archaludon `840#32`;
- Hammer In for `30`;
- Raging Hammer for `80`.

The parent assigned the evolution `-1000` because it categorically holds
non-ex Archaludon outside Ogerpon. It selected Raging Hammer for `80`, leaving
Alakazam at `30` HP. Evolving first would make Coated Attack `1212` payable
for `120`, a visible KO. Both the current Duraludon and evolved non-ex
Archaludon concede one Prize; the Cape maximum HP would rise from `230` to
`280`.

## Existing H5 v2 coverage gap

The completed inactive sibling
`archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2`,
source SHA
`E493C692198FE3699269F3CAFECD3010815DDE5EA2B3002321DDE109F9566798`,
was replayed at the same callback. It remained parent-identical and chose
Raging Hammer.

The reason is a deliberate H5 v2 fail-closed condition:
`current.energyAttached` was already true. This new public state is therefore
natural evidence for a real H5 v2 coverage boundary, not evidence that the
previous H5 v2 implementation fired.

## Potential later hypothesis

`POST_ATTACHMENT_NONEX_120_VISIBLE_KO_CONVERSION`

Allow the same narrow non-ex evolution transaction after this turn's Energy
attachment only when:

1. the current Active is a unique, already-existing Duraludon with exactly
   three supported Basic Metal;
2. the unique legal non-ex Archaludon evolution keeps one-Prize liability;
3. the inherited attack is a visible non-KO and Coated Attack is a visible KO;
4. current Energy payment, public damage modifiers, target HP, and evolution
   legality are exact;
5. the attached Energy is already on this same Active and no alternative
   attacker, terminal route, or reserved transaction is displaced;
6. all unknown modifiers or state mismatches fail closed.

## Causal limitation

The immediate Prize conversion is deterministic, but the match result is not.
The opponent had multiple Kadabra/Alakazam lines, so promotion, draw, and the
later game would change. Consuming the lone non-ex Archaludon may also have
future matchup cost. This must remain a strict public KO-conversion sibling,
not a general permission to evolve non-ex Archaludon outside Ogerpon.

Do not stack this rule into Hero's Cape or silently widen the existing H5 v2
candidate.

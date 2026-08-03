# Root-verified live evidence: Active Dudunsparce Run Away KO transaction v1

Timestamp: 2026-07-22 15:36 JST

## Current live state

- Kaggle submission: `54895497`, `alakazam_psychic_readiness_parent_continuation_v3`.
- Submitted policy SHA-256: `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.
- Exact direct parent v2 SHA-256: `C289127BF6457AB3A451CE17017457103013224ED6714A78E8819B90E9F22ABD`.
- Authenticated first-five public record: 2-3, score `646.700459995968`.
- Episode CSV SHA-256: `808F36C147235333E963AF61C456FB921CD154E42B713485BB15A606709D2B81`.
- API snapshot SHA-256: `9AEF3A281EFBDB0531542BA6E89AE961472913B57BC1D76FFE8447879ECA5DDD`.
- UTC date 2026-07-22 quota: 2/5 used, 3/5 remaining.

## Submitted-delta exposure

- Immutable public-five shadow spec SHA-256: `468AAC0A101D1A9DAFD1D08C6DDF266DFAAFF5613FF7EF8D8D1FB226D4AF9C92`.
- Submitted-v3 raw SHA-256: `42E3B01D45FE68D2D68A2D8B5BB7E5AC53EC0BFFB2E0AD4FA442C432496FB3C6`.
- Direct-v2 raw SHA-256: `D57AE188214CB21E54958A822C007F59C04349499F2FA4134259CA476CABC681`.
- Exact comparison SHA-256: `0A2A533CCA31995B16010FA74A9C1F62DBE3751FB66D179F0A4BC648CA7BF5F6`.
- Five rows / 241 correct-seat callbacks / exact schedule equality / zero v3-v2 action differences.
- Invalid actions, duplicate mismatches, parent-call mismatches, emergencies, and mandatory fallbacks: all zero.

Therefore neither live loss is attributable to the v3 continuation delta; both expose behavior inherited by v2 and v3.

## Recurrence 1: Alakazam mirror, episode 87411430

- Replay SHA-256: `EBD19E589EBCBB089988648CBF87CE166C424866AC9913182678CA58634141D5`.
- Turn 5: damaged Active Dudunsparce `66#18` had legal Run Away Draw.
- Benched one-prize Alakazam `743#12` already had Basic Psychic Energy and its public Powerful Hand damage KO'd the opposing 50-HP Kadabra `742#82`.
- Step 49 attached Telepath Psychic Energy `19#59` to the Active Dudunsparce instead of preserving it for a later attacker.
- Step 53 selected exact `END` while Run Away Draw was legal.
- The opposing Alakazam later KO'd Dudunsparce, discarding the misplaced Energy. The next two Alakazam attackers each reached the Active Spot unpowered and ended without attacking.
- The later Fezandipiti ex line was not a clean alternative target for a blanket ban: Flip the Script drew the only realized Energy needed to attack that turn.

## Recurrence 2: Dragapult, episode 87411965

- Replay SHA-256: `7302AD10F95AE862AF488D6D794179BFF64860988CEE3CCDCF9B6725BEEF4158`.
- Step 22 evolved Active Dunsparce into Dudunsparce `66#18`.
- Step 23 selected exact `END` while exact Run Away Draw was legal.
- Step 38 attached Telepath Psychic Energy `19#61` to the Active Dudunsparce; benched Kadabra was also a legal target.
- Step 39 again selected exact `END` while Run Away remained legal.
- Step 62 finally used Run Away; the Dudunsparce stack, Telepath Energy, and Lucky Helmet returned to the deck.
- Step 64 promoted Alakazam `743#13` with zero Energy, which could only end.
- The first target attack did not occur until step 118, after Dragapult had already taken a double KO.

This is the same public-state mechanism across two different matchups: a legal Active Run Away transition is deferred; scarce Psychic Energy is assigned to Dudunsparce rather than preserving an immediately ready bench attack line; later promotion loses attack continuity.

## Interpretation boundary

- The recurrence supports one narrow Active Dudunsparce evacuation-to-KO transaction.
- It does not support a global Run Away preference, an unconditional ban on Energy attachment to Dudunsparce, or an unconditional Fezandipiti ex ban.
- Hidden opponent hand, opponent identity, replay ID, and exact turn number are prohibited inputs.

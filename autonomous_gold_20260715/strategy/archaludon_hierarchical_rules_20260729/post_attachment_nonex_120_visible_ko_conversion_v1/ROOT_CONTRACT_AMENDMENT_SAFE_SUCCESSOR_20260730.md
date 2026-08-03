# Root contract amendment — safe-successor envelope

Decision:
`SELECT_POST_ATTACHMENT_NONEX_120_VISIBLE_KO_SAFE_SUCCESSOR_ENVELOPE_V1_FOR_SHORT_DESTRUCTIVE_GATE`.

This amendment supersedes the H5-urgency claims and clauses 14/15 in
`ROOT_FROZEN_IMPLEMENTATION_CONTRACT.md`, SHA-256
`B3C86B7FEAE106B8FC53B5300B526E62DBE013F2C6100F6EC17D373B8D07FE3D`.
All other frozen identities, action transaction, precedence, information
boundary, and short-gate requirements remain controlling.

## Root correction

At `88825590:59`:

- opposing Active Alakazam has public hand count `8`, so Powerful Hand is
  `160`, not lethal to the `230` HP Cape-bearing Duraludon;
- opposing Bench includes two Kadabra, each with one Psychic/Telepath Energy
  paying Super Psy Bolt;
- the source therefore does not satisfy H5 v2's lethal-current/no-ready-
  successor urgency envelope;
- Root source verification proved the immediate `80 -> 120` one-Prize KO
  conversion, but did not prove H5 urgency.

The old contract must not be implemented literally. The selected mechanism is
renamed:

`POST_ATTACHMENT_NONEX_120_VISIBLE_KO_SAFE_SUCCESSOR_ENVELOPE_V1`.

## Corrected public certificate

Retain the exact source evolve-to-Coated-KO certificate. Replace the erroneous
return-threat clauses with all of the following:

1. After the projected Coated KO, the public opposing Bench contains at least
   one currently ready successor. This makes the mechanism disjoint from
   H5 v2's no-ready-successor family.
2. A successor is ready when its currently attached public Energy pays at
   least one currently legal printed attack on ordinary promotion.
3. For every ready successor, enumerate every currently payable printed
   attack and compute its maximum deterministic damage from current public
   inputs.
4. The computation must include the actual projected evolved non-ex
   Archaludon HP after retained damage, Hero's Cape, Stadium, status,
   Weakness, Resistance, continuous prevention/reduction, and the supported
   next-turn Coated Attack protection.
5. Every such attack must be strictly nonlethal to the actual projected
   evolved HP.
6. Additionally, for every Basic ready successor, compute the same maximum
   deterministic public damage without crediting Coated protection. If that
   unprotected damage is lethal, veto. This preserves both known H5 v1
   harmful fixed states with a three-Metal Duraludon successor.
7. Unknown card identity, Energy identity, attack cost, legality, dynamic
   formula, chance, attack-side effect, modifier, status, damage, or
   prevention fails closed.
8. Do not project future draw, attachment, evolution, switching card,
   Supporter, Ability, hidden hand, hidden deck, Prize identity, or opponent
   action.

The source positive has two one-Energy Kadabra successors. Their supported
Super Psy Bolt damage is nonlethal to the projected `280` HP Cape-bearing
non-ex Archaludon. The rule remains an immediate safe one-Prize conversion,
not a match-win claim.

## Corrected mandatory negatives

The original negative groups remain, except original groups 14/15 are replaced
with:

14. zero ready opposing Bench successor, which delegates to existing H5 v2 or
    the exact parent;
15. incomplete successor/card/Energy/attack public information, unsupported
    dynamic/chance/side-effect damage, or any ready successor whose maximum
    deterministic effective damage is at least the projected evolved current
    HP;
16. any Basic ready successor whose maximum deterministic public damage
    without Coated protection is at least the projected evolved current HP,
    plus every higher terminal/Boss/owner/reservation/serial/option conflict.

Both historical H5 v1 harmful fixed states must be reconstructed and remain
direct-parent identical because their public three-Metal Duraludon successor
fails the unprotected Basic-successor envelope.

## Corrected short gate

The source engine transaction in both logical seats must prove:

`Raging Hammer parent -> non-ex 840 evolution -> retained Cape/Energy ->
280 maximum HP -> two ready Kadabra successors classified nonlethal ->
Coated Attack 120 -> Alakazam KO -> one Prize`.

Required negative coverage includes:

- no ready successor;
- one lethal ready successor;
- one unsupported/dynamic/chance ready successor;
- Basic successor lethal before Coated protection;
- incomplete successor/Energy identity;
- both known H5 v1 harmful fixed states;
- all original source, mutation, duplicate, reset, rollback, and higher-owner
  negatives.

No fixed-760, full replay shadow, or local win-rate run is authorized.
Package extraction and the same both-seat source smoke remain required.

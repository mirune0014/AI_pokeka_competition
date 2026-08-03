# Task 7 root-verified evidence

## Frozen parent

- Candidate: `archaludon_public_ultra_ball_declared_complete_route_transaction_v1`
- Parent `main.py` SHA-256: `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Task 7 must be an isolated child of this exact parent. Task 6 and earlier
  owners remain unchanged.

## Exact card effects

- Pokégear 3.0 (`1122`): look at the top seven cards, optionally reveal one
  Supporter, put it into hand, and shuffle the rest back.
- Boss's Orders (`1182`): switch one opposing Benched Pokémon into the Active
  Spot.
- Explorer's Guidance (`1185`): inspect the top six cards, keep two, discard
  the other four.
- Lillie's Determination (`1227`): shuffle the hand into the deck and draw six,
  or eight only with exactly six Prizes remaining.

Task 7 may use only own hand, the current Pokégear reveal, public board,
discard, counts, legal options, and exact public combat/effect certificates.
Opponent hidden hand identities are forbidden.

## Existing implementation gap

The cumulative parent contains `PF_GEAR_BOSS_TX_V1`. It can own only a narrow
`Pokégear -> Boss -> gust -> attack` transaction for `FINISH_NOW`,
`AVOID_EXACT_LOSS`, or `PRESERVE_ATTACK_CHAIN`. It does not compare all revealed
Boss, Explorer and Lillie choices by a declared executable purpose.

The prior natural audit is preserved at:

- `implementation/archaludon_purpose_first_pokegear_boss_transaction_v1/ROOT_VERIFICATION.md`
  SHA-256 `B7B158D5FE7B4D6032668CB86EF1F658D91C06964E7B5EF38187F8373962A358`
- `implementation/archaludon_purpose_first_pokegear_boss_transaction_v1/engine_smoke/natural_hard_veto_inventory.json`
  SHA-256 `C1003A1FA5F4A541D672F8B3BBD894F6CB39184C684074759281CAEB9FF84205`

Its verified 207-replay callback inventory found:

- Gear present at 815 MAIN callbacks;
- the parent selected Gear at 291 callbacks;
- positive purpose-owned Gear starts: 0;
- direct-finish Gear vetoes: 2;
- blind parent Gear passthroughs: 289.

Thus callback safety existed, but almost every real Gear choice still used the
generic parent decision and did not declare which Supporter would be useful.

## Direct Supporter failure anchor

Replay `89292594`, SHA-256
`EF9DC6A3427654A8AF1B52A72CBD30F179094DABB0E1E285D7AC24BDF74798B0`.

At step 120 / turn 12 / target seat 1:

- own remaining Prizes: one;
- own Active: Archaludon ex, 300 HP, three Metal, Metal Defender legal;
- own Bench: Duraludon, zero Energy;
- own hand: Explorer, Boss, and three Metal;
- opponent Active: Mega Lucario ex, 340 HP;
- opponent Bench HP values: 110, 80, 110 and 80;
- both Explorer and Boss were legal and no Supporter had been played.

Metal Defender deals 220, so Boss to any visible Bench target is an exact
one-Prize terminal win. The recorded policy instead played Explorer, kept
Lillie plus another Explorer, attacked the 340-HP Active for 220, and lost on
the next opposing turn. This is a public, exact, causal `Boss terminal before
draw Supporter` ordering failure.

## Required Task 7 boundary

Task 7 is the Supporter-purpose layer, not the complete Lillie valuation layer
and not the broad harmful-KO/Boss/reversal layer reserved for Tasks 8 and 9.

It must:

1. before using Pokégear, declare at least one executable Supporter purpose;
2. at Gear reveal, select among Boss, Explorer and Lillie by the declared
   complete turn route rather than fixed identity score;
3. also arbitrate direct legal Supporters when an exact higher-priority purpose
   is already visible, especially exact terminal Boss before Explorer/Lillie;
4. bind physical Supporter serials only after reveal and use deterministic
   duplicate/permutation handling;
5. permit legal Gear miss/empty selection without substituting a different
   Supporter or leaving stale ownership;
6. preserve all existing final-Prize, Task 4-6, attack, Turbo and owner
   precedence.

Task 8 will add full Lillie use/hold valuation. Task 9 will add nonterminal
harmful-KO avoidance, general Boss target selection and reversal branches.
Task 7 must expose clean purpose/certificate fields that those later layers can
reuse without stacking contradictory owners.

## Practical safety gate

- exact parent and deck hashes;
- only `main.py` differs in the candidate package;
- compile/import, final callable, legal 60 cards, one ACE SPEC, cache-free;
- both-seat, duplicate and option-permutation fixtures;
- exact 89292594 terminal-Boss positive and a one-HP-above-lethal negative;
- Gear reveal fixtures containing every Boss/Explorer/Lillie subset, a miss,
  duplicates, and reordered options;
- no Task 7 ownership when no complete purpose exists;
- current-plus-historical replay shadow with every first difference inspected;
- extracted candidate both-seat smoke with zero action errors and no max-step
  hits.

This is an implementation-safety contract. It does not claim win-rate gain.

# Selected next rule: Fez one-Prize public exchange resilience v1

Date: 2026-07-17 (JST)  
Role: root-owned handoff of the read-only Sol-Ultra strategy judgment.

## Decisions

1. `alakazam_fez_next_turn_powerful_hand_continuity_v2` remains formally
   rejected. Its Phase 0 was `22 -> 29/36`, `7G/0R`, but three frozen
   whole-game identity controls changed. Do not run its repeats, broad,
   package, or Kaggle submission.
2. Select exactly one next hypothesis:
   **one-Prize public exchange resilience**.
3. Provisional candidate name:
   `alakazam_fez_public_exchange_resilience_v1`.
4. The implementation parent is exactly accepted
   `alakazam_lone_dunsparce_enriching_reserve_v1`. Rejected Fez v1/v2 are
   read-only mechanics/evidence references, never the source parent.

The rule invariant is:

> A nonterminal one-Prize KO may spend Fez's retreat Energy and an
> Alakazam attack only when it also removes an opponent's additional public
> card investment, or preserves a public next-turn Run Away Draw recovery
> route.

This is a card-exchange and Prize-exchange rule, not an opponent, seed, turn,
target-ID, or saved-outcome filter.

## Authority

- failed-v2 Phase-0 freeze / manifest / root verification:
  `C98B86D61698E4772746AAA4BA9A638C52DE953A0D7B955593E2D41368580F88` /
  `77032A0FBC5E471FCE7740A9DCEC4592860D6889B249F48139AA4B1C8F328360` /
  `20E821DDEE37C0FBDD749538265171D3483F9DB3B565A15116D6D44EA69CBD10`;
- delayed-fire qualitative synthesis:
  `0074DBA99E837E96950D502E9FEE7327EC0F2EBF854A83241502AF7A17BABA1D`;
- failed-v2 raw tree:
  `B73B635BA2B31BFD99A48D1AF8FB7868C4791E886E11B6678375164F08DCBDFC`;
- exact reusable Phase-0 schedule:
  `4EBEF0000AC53F3C5E6913A47AF6EB40365270CEBE33A29BFCFCEC0884EC6B25`;
- accepted-parent raw tree:
  `0AFFC9C3F19CF166DA314FDBF514C95B0BEC210417FA345C75D36719AE0A02A9`.

Accepted-parent source/runtime/deck SHA-256:

`77D111B6061A9A5EF1BCCA383181E1A5EBD67DF10CA45AB0936BE0AAD275785A` /
`6AF5399EEA0B9051722D39408E02822C6D641B499BC7D578F21ED2B0692EC0C9` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Rejected-v2 source/runtime/deck SHA-256:

`1AB35BB99A0392255423E0C5300DFE3BF16E0CDF20000F1AE055AA7ADAFD9CCC` /
`B92648CF17FE70A3455BCD40043B4621CAFF6C1C5B221B8DD277C5A3977E359C` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

## Exact predicate

The complete failed-v2 base immediate-KO certificate, parent
ATTACK/RETREAT delegation, deterministic primary-Alakazam choice, strict
protection/damage/Prize-clock checks, and rank-0 through rank-3 successor
continuity remain necessary conditions.

After those conditions are true, classify the immediate target:

1. **final Prize:** `post_ko_prizes == 0`; allow;
2. **multi-Prize:** `target_prizes >= 2`; allow;
3. **nonterminal one-Prize:** require exactly one public exchange-resilience
   branch below.

### Branch 2: target public commitment

Allow iff the complete public target has at least one additional committed
card:

```text
len(target.preEvolution) + len(target.energyCards) + len(target.tools) >= 1
```

Every committed card must have positive unique serial, exact public ID and
owner, and be part of the frozen target fingerprint. Unknown or incomplete
commitment fails closed.

### Branch 3: next-turn Dudunsparce reserve

Otherwise allow iff own Bench contains a complete Dudunsparce `66` witness:

- positive unique serial and correct owner;
- exactly the ordinary public Dunsparce preEvolution stack;
- complete Pokemon/Energy/Tool/preEvolution fingerprint;
- no currently public persistent Ability lock;
- strict recovery clock:
  `current_deck_count - 4 > post_ko_prizes`.

The four cards are the next own turn's normal draw plus Run Away Draw's three
cards. Current-turn Ability-option presence is not required: once-per-turn
use resets before the next own turn. This is a public recovery witness, not a
promise that the opponent cannot remove it.

Choose the witness deterministically by ascending:

`attached Energy + Tool count -> Bench index -> positive serial`.

Branch precedence is fixed:

`final_prize > multi_prize > target_public_commitment >
next_turn_dudunsparce_reserve`.

If both one-Prize branches hold, use target commitment. Do not use opponent
name/policy, seed, turn number, target card ID, hidden hand/deck content,
future draw identities, damage-counter outcome labels, or saved results.

## Latch and fail-closed behavior

Copy the already checked immediate transaction mechanics into a fresh branch
from the accepted parent:

`RETREAT -> context 30 exact payment -> context 3 exact primary Alakazam ->
same-turn MAIN attack 1072 -> certified KO`.

Freeze all failed-v2 transaction fields plus:

- exchange branch;
- every target-commitment card fingerprint;
- Dudunsparce witness serial/full fingerprint;
- start deck/Prize recovery margin.

Re-find a Dudunsparce by serial, never by mutable Bench index. Recheck branch,
target, witness, counts, stadium, payment, primary, protection, damage, and
clock at every callback. Any disappearance, mutation, ambiguity, duplicate,
owner mismatch, unexpected context, or non-unique option clears and delegates
to the accepted parent. An abort after irreversible RETREAT is an integration
failure.

Do not add a cross-turn action latch. The witness justifies the current
exchange; future actions must re-evaluate the actual state.

## Frozen disposition of known boundaries

Expected PASS:

- retained gains: Rmy Alakazam (attached Energy), Marnie P0 Munkidori
  (Dudunsparce), Dragapult ex (multi-Prize), Oselcoun Dunsparce
  (Dudunsparce), Dragapult Dreepy (attached Energy), Kangaskhan/Crustle
  (preEvolution);
- Historical delayed Cinderace (preEvolution + Energy) and Duraludon
  (three Energy);
- live `86459487` (energized evolved Kadabra and Bench Dudunsparce);
- live `86387405` (evolved Cynthia's Roserade with Hero's Cape).

Expected suppression:

- Marnie P1 Munkidori retained-v2 gain: no target commitment and no Bench
  Dudunsparce;
- Mega delayed Riolu: bare Basic and no Bench Dudunsparce;
- the four original live suppression anchors plus `86385015` under inherited
  conditions;
- all original dangerous v1 regression boundaries under inherited successor
  continuity.

## Immutable Phase 0 after implementation

Reuse the prior 36-key schedule byte-for-byte. Run accepted parent then fresh
candidate, both seats, identical seeds, complete traces, one game/key,
Python 3.11 `-B`, explicit decks, engine seed, `max-steps 1000`, no retry.

Conjunctive PASS:

- candidate at least `28/36`, gain at least `6`, regression `0`;
- P0/P1 floors `13/18`, `15/18`;
- block floors known/fresh/new_fresh: `2/2`, `8/10`, `18/24`;
- opponent floors: Oselcoun `3/6`, Rmy `2/2`, Dragapult `5/6`, Great Tusk
  `1/2`, Historical `3/4`, Kangaskhan/Crustle `2/2`, Marnie `5/6`, Mega
  `1/2`, Starmie `6/6`;
- the 26 failed-v2 parent-identical keys remain whole-game parent-identical;
- six retained gains and both Historical delayed transactions are complete
  failed-v2-candidate-identical traces and preserve their outcomes;
- Marnie P1 and Mega delayed known boundaries suppress to parent; a later
  new fire is allowed only after a fresh full predicate certificate;
- original four regression, two rejected-gain, and Great Tusk
  promotion-first boundaries suppress state-locally. Historical later fires
  are allowed, so those two games are not whole-game identity controls;
- every first difference is RETREAT; promotion-first/unrelated differences,
  latch aborts, invalid actions, errors, max-step hits, malformed rows,
  schedule/hash/cache faults are zero;
- every changed key repeats candidate-only three times with byte-identical
  traces and summaries equal after only trace-path normalization.

Focused tests must separately cover preEvolution-only, Energy-only,
Tool-only, both exchange branches, present/absent current Dudunsparce Ability
option, next-turn reset, Dunsparce-only rejection, persistent Ability lock,
strict `deck-4 == post_ko_prizes` rejection, witness tie-breaks, every
fingerprint mutation, all four successor ranks, live anchors, and all known
delayed/suppressed states.

## Broad gate

Only after a fresh Sol-Ultra Phase-0 GO, run candidate-only on the accepted
parent's exact 1,440-key schedule.

Conjunctive PASS:

- candidate at least `839/1440`; parent-win regression `0`;
- all six retained-gain keys remain wins;
- block floors known/fresh/new_fresh: `212`, `204`, `423`;
- seat floors P0/P1: `418`, `421`;
- opponent floors: Historical `60`, Mega `134`, Starmie `105`, Dragapult
  `141`, Marnie `107`, Great Tusk `26`, Kangaskhan/Crustle `78`, Oselcoun
  `91`, Rmy `97`;
- any parent public trace on which the predicate never becomes true is
  whole-game parent-identical;
- every changed prefix is identical until a RETREAT first difference and
  has a complete public exchange branch, successor certificate, and
  same-turn payment/promotion/1072/KO chain;
- all changed broad keys repeat three times; all schema, action, hash,
  latch, cache, and command faults are zero.

Root raw verification and a fresh Sol-Ultra final adoption judgment remain
mandatory before packaging or Kaggle submission.

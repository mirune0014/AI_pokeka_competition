# Selected refinement: Fez public retaliation guard v2

Date: 2026-07-17 (JST)  
Role: root-owned handoff of the fresh read-only Sol-Ultra broad NO-GO and
next-hypothesis judgment.

## Decisions

1. `alakazam_fez_public_exchange_resilience_v1` passes its frozen numerical,
   mechanics, structure, and repeat Phase 0, but is formally **Broad NO-GO**.
   Do not broad-evaluate, package, or submit it.
2. The reason is a public two-ply exchange defect, not insufficient sample
   size: its Dudunsparce-only branch can expose Alakazam to a currently ready
   return KO even when the target is a bare nonterminal one-Prize Pokemon.
3. Select exactly one next hypothesis: **public retaliation guard**.
4. Fresh candidate name:
   `alakazam_fez_public_retaliation_guard_v2`.
5. The implementation parent is exactly accepted
   `alakazam_lone_dunsparce_enriching_reserve_v1`. Rejected Fez v1/v2 and
   exchange-resilience v1 are read-only mechanics/evidence references, never
   the source parent.

The rule invariant is:

> Dudunsparce hand recovery alone justifies a nonterminal bare one-Prize
> exchange only when no opponent Bench Pokemon can promote and immediately
> KO the promoted primary Alakazam using its currently attached public
> Energy and a fully certified printed attack.

This is a public two-ply rule:

`our target KO -> opponent's strongest currently ready public retaliation`.

It does not use opponent name, target ID, seed, turn, hidden hand, future
draw, future attachment/evolution, saved outcome, or opponent-policy proxy.

## Authority

- accepted parent source/runtime/deck:
  `77D111B6061A9A5EF1BCCA383181E1A5EBD67DF10CA45AB0936BE0AAD275785A` /
  `6AF5399EEA0B9051722D39408E02822C6D641B499BC7D578F21ED2B0692EC0C9` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- exchange-resilience v1 source/runtime/deck:
  `C07AEFEB446266C4E33A4A85F7E5F3FACA868981C0544D54B05B882C58E9973F` /
  `A0E6C997DCAB9A044A7562325B2FA94CB08306304829F66F06AAF68A195EE70B` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- exchange-resilience Phase-0 raw / repeat raw:
  `0CDB308A8869371A8EAD0F504D99E93C10EC461D0CC479466A295B436A6BA6E9` /
  `E546BDFF7BCAB174D86AD5D8C94D1591DD383FB2E367DD121781547A683B55B5`;
- execution / repeat manifests:
  `33C00E5900DDE433169B206D9B7800560E208349325A22BFF30CC79621F2E8D1` /
  `68ED02A76D66AB4B2A615639AFB338DDC3C32D9E05958418FD16D9429C451127`;
- root final Phase-0 closure:
  `DCF23B1E70C6F6991EFEA4B7736933AD85A43CD0769698F67B5612F746FFF05C`;
- exact reusable 36-key schedule:
  `4EBEF0000AC53F3C5E6913A47AF6EB40365270CEBE33A29BFCFCEC0884EC6B25`.

The parent-v1 Phase 0 was `22 -> 28/36`, `6G/0R`, with every seat, block,
and opponent floor met exactly, 26 identity controls preserved, eight
protected traces exact, and all thirty changed-key repeats byte-identical.
That result is evidence for retaining the immediate-KO and exchange branches;
it does not override the public retaliation defect below.

## Exact scope

Preserve all complete exchange-resilience-v1 mechanics as necessary
conditions:

- parent ATTACK/RETREAT delegation;
- deterministic primary-Alakazam choice;
- damage/protection/Prize/deck clocks;
- rank-0 through rank-3 successor continuity;
- exact same-turn RETREAT -> Energy payment -> Alakazam promotion -> Powerful
  Hand `1072` -> KO transaction;
- final-Prize, multi-Prize, target-public-commitment, and Dudunsparce-reserve
  branch precedence;
- all fingerprints, fail-closed checks, and no cross-turn action latch.

Change only a nonterminal one-Prize decision whose selected exchange branch is
`next_turn_dudunsparce_reserve`. Final-Prize, multi-Prize, and target-public-
commitment decisions remain byte-for-byte behaviorally unchanged.

## Public retaliation certificate

Let `primary` be the exact Alakazam that the transaction would promote and
let `primary_remaining_hp` be its exact current remaining HP. After the target
KO, conservatively allow every current opponent Bench Pokemon to promote for
free. The Dudunsparce-only branch is permitted iff:

```text
for every complete opponent Bench Pokemon b:
  for every printed attack a of b that is payable now from b's attached
  public Energy alone:
    certified_damage(a, b, primary) < primary_remaining_hp
```

The quantification is over every Bench Pokemon and every printed attack, not
the action an opponent is expected to choose.

### Completeness and Energy payment

For each Bench Pokemon, require positive unique serial, exact owner, complete
Pokemon/preEvolution/Energy/Tool fingerprint, and unambiguous card metadata.

An attack is `payable now` using only the currently attached public Energy
units. Match the engine's deterministic feasibility semantics:

1. satisfy colored requirements first;
2. allocate remaining certified Energy units to Colorless requirements;
3. do not count a future attachment, evolution, hand card, Ability, discard,
   or policy choice;
4. if an attached special Energy's provided units or restrictions cannot be
   proved exactly, fail the Dudunsparce branch closed;
5. a known attack with provably insufficient current Energy is not a ready
   retaliation and may be ignored.

### Certified damage

For an Energy-payable attack, compute exact public immediate damage against
the promoted primary:

- printed fixed damage;
- Weakness and Resistance in engine order;
- printed ignore-Weakness/Resistance rules;
- all currently public attacker/defender Tool, Energy, Stadium, Pokemon, and
  persistent effects that can modify, prevent, redirect, or replace damage.

Damage equality is unsafe: `damage >= primary_remaining_hp` suppresses the
branch.

If an Energy-payable attack uses a coin flip, variable/plus/multiply formula,
hidden quantity, damage-counter placement, conditional attack prohibition,
or any modifier/protection/effect whose safe upper bound cannot be proved
from complete public state, classify it as dangerous and fail closed. Do not
use an unknown temporary restriction as evidence of safety.

The minimal v2 rule adds no successor counter-KO exception. Modeling future
draws, Dudunsparce, Fez, Prize cards, and opponent disruption together would
add a second untested hypothesis. This candidate proves only absence of a
currently ready public return KO.

## Frozen known-boundary disposition

- Marnie P1 step 89: **SUPPRESS**. Public Bench Grimmsnarl ex has seven
  Darkness Energy; Shadow Bullet `937` is 180, doubled by Alakazam's Darkness
  Weakness to 360, so `360 >= 140`.
- Marnie P0 retained gain: **PASS**. The ready Morgrem attack is 60, doubled
  to 120, so `120 < 140`.
- Mega P0 step 73: **PASS**. Hero's-Cape Solrock's conservative certified
  maximum is 70, so `70 < 140`.
- Oselcoun retained gain: **PASS**. No complete currently ready attack reaches
  140.
- Other four retained gains: unchanged target-commitment or multi-Prize PASS.
- Historical delayed two: unchanged target-commitment PASS.
- live `86459487` and `86387405`: target-commitment PASS.
- original live suppressions, initial Marnie/Mega bare-target boundaries,
  rejected-v1 regressions/gains, and Great-Tusk promotion-first boundary:
  remain suppressed under inherited conditions.

## Latch and fail-closed integration

Freeze the complete inherited transaction plus:

- retaliation-guard version and result;
- promoted primary serial, full fingerprint, remaining HP, Weakness,
  Resistance, Tool/Energy, and visible effects;
- every opponent Bench serial, full Pokemon/evolution/Energy/Tool
  fingerprint;
- every printed attack ID, cost, current-payability result, certified damage,
  and exact reason or fail-closed reason;
- Stadium and all visible damage/effect fingerprints used by the certificate.

Recompute and compare the certificate at RETREAT, payment, promotion, and
attack callbacks. Mutation, ambiguity, duplicate serial, owner mismatch,
unsupported effect, or a newly nonmatching certificate clears and delegates
to the accepted parent before RETREAT. Any abort after irreversible RETREAT is
an integration failure. Add no cross-turn latch.

## Focused verification before execution

Required tests include:

1. reconstructed Marnie P1 step 89 suppression;
2. Marnie P0 retained pass at 120 versus 140;
3. Mega step 73 retained pass at 70 versus 140;
4. Oselcoun retained pass;
5. exact damage equality suppresses;
6. Weakness and Resistance order;
7. ignore-Weakness/Resistance handling;
8. known insufficient Energy is safely ignored;
9. payable variable/coin/hidden attack fails closed;
10. ambiguous special-Energy unit fails closed;
11. unknown public modifier, prevention, protection, or effect fails closed;
12. the guard applies only to Dudunsparce-only exchange;
13. fingerprint mutation at each callback fails closed and irreversible abort
    is absent;
14. all inherited successor ranks, live two pass anchors, original live
    suppressions, and Historical packaged smoke remain correct;
15. compile/import, legal identical 60-card deck, deterministic deck request,
    both-seat packaged-form smoke, and cache-zero all pass.

## Immutable Phase 0

Reuse the exact prior 36-key schedule byte-for-byte. Run accepted parent then
fresh candidate, both seats, identical seeds, complete traces, one game/key,
Python 3.11 `-B`, explicit decks, engine seed, `max-steps 1000`, no retry.

Conjunctive PASS:

- candidate at least `28/36`, paired gain at least `6`, regression `0`;
- P0/P1 at least `13/18`, `15/18`;
- known/fresh/new_fresh at least `2/2`, `8/10`, `18/24`;
- opponent floors unchanged: Oselcoun `3/6`, Rmy `2/2`, Dragapult `5/6`,
  Great Tusk `1/2`, Historical `3/4`, Kangaskhan/Crustle `2/2`, Marnie
  `5/6`, Mega `1/2`, Starmie `6/6`;
- all 26 whole-game identity controls remain parent-identical;
- six gains, both Historical delayed traces, and Mega step-73 transaction are
  exchange-resilience-v1-identical and preserve outcomes;
- Marnie P1 stays parent-identical through step 89 and does not fire there;
- every other changed prefix is identical until RETREAT and has a complete
  inherited transaction plus retaliation certificate where applicable;
- latch abort, unrelated/promotion-first difference, action error, max-step,
  malformed row, duplicate/missing schedule, hash, schema, and cache faults
  are zero;
- every changed key repeats candidate-only three times with byte-identical
  traces and summaries equal after normalizing only trace path.

Fresh Sol-Ultra numerical audit, root raw verification, and a fresh Sol-Ultra
strategy GO are mandatory before the 1,440-key broad run. This candidate may
not be packaged or submitted before passing that sequence.

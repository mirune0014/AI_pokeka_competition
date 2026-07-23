# Frozen implementation decision: Xerosic immediate-KO successor single swap v1

- Recorded: 2026-07-19 04:35 JST
- Owner: root
- Status: approved for one isolated Fast candidate implementation
- Kaggle authorization: none

## Parent and rejected sibling

Implement directly from the accepted exact-v3 parent:

- `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`;
- source/runtime/deck SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The destination is
`candidates/alakazam_xerosic_immediate_ko_successor_single_swap_v1` and must
not exist before implementation.  Keep the 60-card deck byte-identical.

Do not stack or edit the rejected
`alakazam_xerosic_certified_retained_triple_v1` candidate.  Its global triple
ranker is read-only reference material.  Rejection evidence:

- numerical audit SHA-256
  `05BA130B3318BB6AC205285B4C3839F747652C01B6A22F36361C9EEDEE4B4ABD`;
- qualitative audit SHA-256
  `417E77BEB9FBA63BD5735505076C8DBDD64124AD84E6770CC23D9305D452133D`;
- exact result `86/144 -> 86/144`, 4 gains/4 regressions, P0 `45->43`;
- adoption blockers at `86674048/24`, `86666507/108`, and `86656277/101`.

## Single hypothesis

When exact-v3 has already chosen the three cards retained after an opponent's
certified Xerosic, repair exactly one narrow failure: if a publicly payable
opponent Powerful Hand will KO the Active and exact-v3 discards the only hand
Alakazam while retaining a targetless Rare Candy, swap only those two cards so
an energized, evolution-ready Bench Kadabra becomes the immediate next
attacker.  Preserve exact-v3's other two retained cards and every other action.

This is a two-turn public transaction:

`opponent Xerosic -> retain successor evolution -> opponent Powerful Hand KO -> promote energized Kadabra -> evolve to Alakazam -> attack`.

## Exact activation contract

1. Compute the exact-v3 parent action first.  The repair may transform only
   that returned action.
2. Require the complete fail-closed Xerosic callback certificate:
   `SelectContext.DISCARD`, effect ID 1197, effect owned by the opponent with a
   positive serial, full visible own hand, unique own-HAND CARD options and
   serials covering the hand exactly, and fixed discard count `handCount - 3`.
3. Require the opponent Active to be Alakazam with publicly payable Powerful
   Hand, no disabling status, and no ambiguous visible damage modifier.  Its
   public damage `20 * opponent handCount` must be at least own Active current
   HP.
4. Require exactly one evolution-ready Bench Kadabra: a complete Abra
   pre-evolution fingerprint, `appearThisTurn == false`, at least one attached
   Psychic Energy, and no ambiguity.  There must be no already attack-ready
   Bench Alakazam.
5. Require exactly one hand Alakazam discarded by the parent action and
   exactly one Rare Candy retained by it.
6. The retained Rare Candy must have zero next-own-turn public target in both
   the Active-survives and Active-KO branches: no compatible surviving,
   evolution-ready visible Abra.  Hidden deck/prize identities never count.
7. Perform exactly one swap: remove the Alakazam option from the parent's
   discard action and add the Rare Candy option.  Sort/format only as required
   for a valid deterministic action.  The other two retained cards must remain
   identical by card ID and serial.
8. Fail closed to the exact parent action on any malformed mapping, extra
   candidate/victim, ambiguous KO/damage/energy/modifier, newly played
   Kadabra, live Candy target, existing ready successor, inaccessible
   successor, or branch uncertainty.

## Prohibited scope

- no triple enumeration or global reranking;
- no duplicate penalties;
- no Dawn, Hilda, Poffin, draw, search, disruption, or hidden-capacity score;
- no Active-survives Bench-access claim;
- no deck changes, learned component, replay-derived opponent proxy, or
  opponent-policy imitation;
- no changes outside the certified single swap and minimal wrapper/refactor
  required to obtain the exact parent action first.

## Exact replay expectations

Positive anchor:

- `86657890/133`: parent action `[0,1,2,3,4]` becomes
  `[0,1,2,3,5]`, retaining Alakazam `(743,11)`, Dudunsparce `(66,18)`,
  and Basic Psychic Energy `(5,57)`.

Negative anchors must remain exact-parent:

- `86676249/39`;
- `86674048/24` -> `[0,1,2,3,4]`;
- `86666507/108` -> `[0..13]`;
- `86665439/67` and `/137`;
- `86660075/119`;
- `86657890/97`;
- `86656277/56` and `/101` -> `[0,1]`.

Also require option-order invariance, repeated-call determinism, malformed
input fail-close, source/runtime parity, legal 60-card deck, and both-seat
engine smoke.

## Fixed evaluation gates

Use a fresh corrected mandated-venv 576-run primary/duplicate matrix on the
same frozen 144 keys.  The runner must record correct trace facts, exact
commands, every frozen hash, and enforce all fail-fast controls.

- candidate at least 88/144;
- at least two gains and zero regressions;
- P0 at least 45/72, P1 at least 41/72;
- known at least 44/72, fresh at least 42/72;
- Historical-Silver at least 8/16 and Alakazam-Rmy at least 7/16;
- no opponent bucket below exact-v3;
- at least four intended activations spanning both seats, both seed blocks,
  and two Xerosic-bearing opponent buckets;
- every first difference must be the exact single swap;
- at least two independently changed games must realize the full successor
  transaction with zero certification defects.

Even a Phase-0 pass requires a new frozen both-seat Alakazam-mirror
confirmation panel with positive movement and zero regressions before a live
probe.  Only root may decide packaging or submission after final Sol-Ultra
judgment and an immediate authenticated refresh.

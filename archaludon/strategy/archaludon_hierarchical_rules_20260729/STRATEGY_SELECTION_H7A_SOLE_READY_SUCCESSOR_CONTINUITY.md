# H7-A strategy selection: sole ready successor continuity

Decision: `SELECT_IMPLEMENTATION_EXPERIMENT_ONLY`.

This rule is implementable as one narrow public-state transaction, but it is
not yet adoption- or live-worthy. It must be implemented as a direct,
unstacked child of exact historical-Silver and evaluated independently.

## Frozen inputs

- Historical-Silver `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Historical-Silver deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- `FUTURE_HYPOTHESES.md`:
  `0B03FEF73D5223A35E1A3908AD68C1EE722862828707F4577FDBFF70866E946A`
- Source replay `88660007`:
  `CE2B4EA6D95EEC05582AB709806E5C9B302F98479E67220852C42A6159A4AE2F`
- Correct historical-Silver seat: `1`
- Current `cg/cg.dll` used for card data:
  `9EA2B0A751029689BFF3DDCCB5F29A98EDD46961DAD264490ED121EF704FB500`

## Exact source

Rows 78-80 select the exact parent evolution, Assemble Alloy, and Metal
serials `#116/#120`. Row 81 places `#116` on exposed Active Archaludon ex
`#69`; this must remain parent-identical.

At row 82, the final freely allocable Metal `#120` has three legal targets:

- Active Archaludon ex `#69`, parent score 18,500;
- Bench Archaludon ex `#70`, parent score 11,200;
- Bench Duraludon `#65`, parent score 10,300.

The parent chooses Active `[0]`. This completes Metal Defender, which does 190
through Full Metal Lab but does not KO the opposing Active. The opposing
Active already has three visible Basic Metal and a payable 190-damage Metal
Defender that KOs our 110-HP Active.

Redirecting only the last Metal to Bench Duraludon `[2]` uniquely makes its
printed Hammer In payable. Important limitations:

- Full Metal Lab reduces that Hammer In to zero damage against the current
  opposing Metal Active.
- The exact parent later promotes zero-Energy Archaludon ex `#70`, not the
  preserved Duraludon.
- Therefore this source proves resource continuity only. It does not prove a
  win, positive future damage, or a correct later promotion.

## Sole hypothesis

At the final freely targetable Basic Metal placement of one Assemble Alloy
resolution, redirect that Metal from the exposed Active to the unique Bench
target that becomes attack-payable only if all public facts below hold:

1. placing the Metal on the Active uniquely completes a positive,
   deterministic current attack;
2. that attack is a certified non-KO after all public modifiers;
3. the opposing Active already has a payable deterministic return attack that
   KOs our exposed Active;
4. no Bench Pokemon is already attack-payable;
5. exactly one legal Bench target becomes attack-payable from this Metal;
6. no terminal win, current Prize conversion, forced-defense route, or
   equal/higher-Prize route has precedence;
7. the placement is freely targetable, not forced onto the Active.

“Ready” means only that a printed attack's visible Energy cost is payable. It
does not imply positive damage or a winning continuation.

## Isolated implementation contract

Destinations:

- `candidates/archaludon_h7a_sole_ready_successor_continuity_v1`
- `implementation/archaludon_h7a_sole_ready_successor_continuity_v1`
- `evaluations/archaludon_h7a_sole_ready_successor_continuity_v1`

First owned difference must be replay `88660007`, seat `1`, row `82`:

- parent `[0]`: `8#120 -> Active 190#69`;
- candidate `[2]`: `8#120 -> Bench 169#65`.

Rows 78-81 must remain parent-identical. The transaction stages are:

1. `EMPTY`;
2. `ALLOY_SELECTED`, storing the exact selected Energy serial order;
3. `ALLOCATING`, delegating and confirming every non-final placement;
4. `REDIRECT_EMITTED`, revalidating the certificate and emitting the unique
   ready-successor target on the final placement;
5. on the next novel callback, confirm the projected board, clear, and
   delegate.

The snapshot binds seat, turn, effect/evolution serial, selected Energy order,
complete public identities/HP/Energy/tools/statuses, both Prize counts,
Stadium, hand-visible Energy, turn flags, projected current attack and
damage, deterministic return attack and damage, and the unique successor and
attack.

Duplicates return the cached action without another parent call or stage
advance. Missing or duplicate serials, changed option fingerprint,
seat/turn/effect mismatch, unexpected allocation, public board mutation, or a
stale transaction clears and delegates the already-computed exact parent
action. After the redirect is emitted, rollback must never invent a second
action.

Forbidden behavior includes changing Energy selection, redirecting a
non-final Metal, choosing Bench Archaludon `#70` in the source, forcing End,
attack, retreat, or promotion, generic Bench-Energy scores, matchup labels,
replay IDs, hidden-card inference, H7-B promotion, and any H5/H6 code.

## Required verification

Focused and exact-engine tests must cover the full rows 78-82 transaction in
both logical seats and with serial permutation. They must show the parent and
candidate Energy boards, the visible return KO, preserved successor Energy
after the KO, reset/delegation, and exact-parent promotion afterward.

Mandatory negatives include current KO/win, Active survival, an already-ready
Bench attacker, zero/multiple newly ready Bench targets, nonpayable successor,
non-final placement, current attack already payable or still unpayable,
unknown/dynamic damage or Energy, public protection/status/modifiers,
return attacks requiring attachment/evolution/switch/hidden cards/chance,
return-route disabling, forced Active placement, visible terminal/Prize/
defense precedence, malformed options, duplicates, rollback, reset, and the
H5/H6/H7-B source controls.

Complete shadow uses the frozen 217-file, 11,967-callback corpus at:

`live/55073442/refresh_20260729_1541/shadow_corpus_207_prior_plus_10_new`

Its source manifest is:

`2BB9D462D1C6FD5BF49CEB34A9EA49F4C658A91DFF2330757AD510A5C62ABABD`.

Expected shadow behavior is rows 80-82 owned, exactly one action difference at
row 82, one parent-history rollback at row 83, and zero external differences,
invalid actions, or exceptions.

Fresh fixed-760 must use the same frozen historical-Silver 200-row panel and
seven-opponent 560-row panel. It requires exact schedule equality, duplicate
and byte-trace controls, zero execution faults, and no cell regression.
Outcome neutrality permits inactive retention only.

Live/formal-parent eligibility is deliberately higher:

- at least `+4/200` paired net on historical-Silver;
- at least `+8/760` overall;
- nonnegative movement in both seats;
- no adjacent cell loss;
- at least two independent H7-A mechanism occurrences;
- uncertainty analysis excluding material harm.

A tiny isolated delta is insufficient. The primary risk is sacrificing a
certified 190 damage attack for a successor that currently deals zero damage,
while H7-A alone cannot fix the later promotion. A separate H7-B mechanism
would require a separate hypothesis, implementation, and evaluation.

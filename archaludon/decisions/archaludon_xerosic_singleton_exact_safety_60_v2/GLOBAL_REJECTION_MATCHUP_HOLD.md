# Xerosic singleton global rejection and matchup hold

Date: 2026-08-16 (JST)

## Decision

Candidate F (`archaludon_xerosic_singleton_exact_safety_60_v2`) is globally
rejected and frozen. It must not be narrowed, packaged, submitted, merged, or
used as a new parent. The formal accepted parent remains the rollback point.

The same-deck control is an ablation instrument only; it is not a deployment
candidate. Because the targeted causal gate failed, the Xerosic series is
closed and no fixed760/fresh640 control continuation is authorized.

## Root-verified evidence

- Candidate F fixed760: 500 -> 498, delta -2.
- Candidate F fresh640: 476 -> 465, delta -11.
- Candidate F global combined: 976 -> 963, delta -13.
- Candidate F targeted Alakazam320: 276 -> 260, delta -16, gains 2,
  regressions 18.
- The Candidate-F global and targeted reports are historical evidence only;
  they do not authorize a submission.

Targeted raw output:
`archaludon/evaluations/archaludon_xerosic_singleton_deck_only_control_v1_targeted320_20260816_retry5/raw`

Targeted root recomputation:
`archaludon/implementation/archaludon_xerosic_singleton_deck_only_control_v1/ROOT_RECOMPUTE_TARGETED320_RETRY5.json`

Evidence hashes: report
`598D21F4214CD84A1B8C62E608C26A88E8E22C1729D981A20CEC798D786D688A`, manifest
`37AFE851C0C7837DF383E4B22256A8AF904F077E61852A880DCCA374F94F8019`, paired
rows `2F920D384D149512190C6AF5BC0958CA7F9E72E5F920A507B3F76F4B85BC1A99`,
and root recompute `A6C21C76799AF3672B868DFB11D1FEB88F6E9FF99A1F978EFD60459B84F7686D`.

Root recomputation is valid for 320/320 unique keys, both seats, exact seed
formula, zero action errors, zero max-step hits, and zero duplicate mismatch.
First semantic differences are 107 direct Xerosic PLAY and 3 Pokégear 3.0 to
Xerosic selections; no unknown mechanism-first difference remains. The
paired-results SHA is
`2F920D384D149512190C6AF5BC0958CA7F9E72E5F920A507B3F76F4B85BC1A99`.

## Implementation correction recorded

Two earlier targeted attempts are preserved as failed diagnostics. They
exposed wrapper errors rather than engine instability: first opponent-Xerosic
discard selections were shortened, then Explorer's Guidance selections were
mistaken for Pokégear. The final control has explicit context/effect guards:

- direct `MAIN` `PLAY` of card `1197` only;
- `TO_HAND` card `1197` only when effect card is Pokégear 3.0 (`1122`);
- opponent `DISCARD` and Explorer's Guidance (`1185`) pass through the formal
  parent unchanged.

Focused suite is 16/16 PASS, the failing raw outputs remain untouched, and the
control deck is byte-identical to Candidate F (`CBC9639B3FCA16767DCF48852B5ED1637C76D6A8594B9662B570DD12F7C3EC3F`).

## Next state

Keep the formal parent and existing accepted artifacts unchanged. Do not spend
additional evaluation or Kaggle slots on this Xerosic hypothesis. A future
improvement must start from the formal accepted parent with a new independent
hypothesis and its own causal comparison.

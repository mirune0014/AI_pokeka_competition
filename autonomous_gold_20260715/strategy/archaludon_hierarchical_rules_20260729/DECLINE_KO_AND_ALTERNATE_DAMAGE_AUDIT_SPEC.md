# Immutable qualitative audit specification: decline-KO and alternate damage

## Authority

- Formal policy:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`
- Policy SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/deck.csv`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Alakazam input specification SHA-256:
  `C0CEAD5039DC37EC1299AB086FABAA54ACFF74E471ABA73CC8C46013DAB492C1`
- Adjacent input specification SHA-256:
  `3E6712E109F46CE711B3A4B5114C94DA9D8E6C232D3850EFE08922B447EDE32B`
- Prior Alakazam report SHA-256:
  `C5122CC809EBD2D1D40894C714090AFC84883A38CFBC802907CEF6AECC8557A2`
- Prior adjacent report SHA-256:
  `F65E9F8EB59EFA8C9ECB687710EFA957A8246275915F3C6F7D8958342CD1B272`
- Episode CSV SHA-256:
  `A94A0754A9D2F84B88DB7D64BC126D4E8FA2855CC0769E799A031F6D4702F64E`
- Extracted deck manifest SHA-256:
  `F347CB1D5B3DB5FB1D4D1CE2098C3C53CBED98A542A1AA015FE894E22445F1F8`
- Raw replay locator:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_<EPISODE_ID>_replay.json`

## Frozen episode set

Inspect all 48 loss replays; do not select a favorable subset after reading
outcomes.

Alakazam losses:

`88614404, 88602602, 88479736, 88457867, 88454146, 88417236,
88399026, 88385224, 88323824, 88244115, 88242194, 88232035,
88191793, 88171291, 88163977, 88096405, 88096059, 87996118,
87994013, 87974582, 87935410, 87911107, 87892692, 87842092`.

Adjacent losses:

`88660007, 88655752, 88643491, 88584180, 88563380, 88509934,
88507294, 88411737, 88391698, 88389000, 88367994, 88356203,
88338429, 88272191, 88247531, 88225916, 88197270, 88134743,
88017509, 87868636, 87825800, 87709435, 87701753, 87690776`.

## Exact audit question

Find every high- or medium-confidence public-state callback where either:

1. an available opposing Active KO should plausibly be declined or delayed;
2. Boss, another target change, or a Bench-damage action yields a strictly
   stronger certified Prize, continuity, or terminal-defense line than
   KOing the current Active; or
3. every locally high-scoring action is losing, but a lower immediate-value
   action preserves a public comeback or forced-conversion out.

The audit concerns a decision rule, not replay-derived action imitation.
Opponent actions may establish that a printed attack/effect exists and was
payable from public state; they are not labels or an opponent-policy proxy.
Do not reconstruct hidden hands, unrevealed deck order, Prize identities, or
future draws.

## Required per-state evidence

For each surviving state, record:

- exact episode, correct seat, row, turn, context, Prize counts, and result;
- every relevant legal semantic action and the exact historical-parent
  semantic choice;
- cards, serials, zones, HP, status, attached Energy, Tools, Stadium, and
  public restrictions used by the certificate;
- exact printed attack/effect, public payment, damage, weakness/resistance,
  prevention/reduction, KO, and Prize calculations;
- the proposed semantic action and the smallest public-state reason it
  dominates the Active KO;
- whether the certificate proves only an immediate board/Prize improvement,
  a forced defense, an exact same-turn terminal, or a complete match
  conversion;
- exact parent source branch/score that produced the weaker action; and
- mandatory negative controls that must remain parent-identical.

No full-game alternate win may be claimed unless the proposed current-turn
transaction deterministically takes the last Prize or otherwise ends the
match from the current public state.

## Classification

Assign exactly one class:

- `HARD_GATE_CANDIDATE`: the proposed action is uniquely required by an exact
  terminal, forced-defense, or strictly dominating public Prize certificate;
- `SOFT_SCORE_CANDIDATE`: several legal lines remain and only a bounded
  expected-value preference is supportable;
- `ALREADY_COVERED`: the state belongs to frozen H1, H2, H4 v3, H5 v2, H6,
  H7-A, or the separate Bench-damage evolution audit;
- `INSUFFICIENT_PUBLIC_EVIDENCE`: hidden access, future draw, opponent choice,
  or an unproved multi-turn result is necessary.

Keep target choice, Prize arbitration, non-KO exposure, Bench-damage future
value, comeback outs, and harmful-KO avoidance separate. Do not turn them
into a generic board score.

## Output boundary

Recommend at most one new isolated mechanism, chosen only if:

- its first owned difference is exact and reproducible;
- its public certificate generalizes beyond an episode ID or opponent label;
- it is not already covered by H1/H2/H4/H5/H6/H7-A;
- its negative controls are explicit; and
- it can be reconstructed in both logical seats with exact transaction,
  duplicate, rollback, reset, and fail-closed behavior.

Otherwise report that no new hard rule is supported and state the missing
evidence. Do not implement source, run a numerical aggregate, recommend a
Kaggle write, or claim formal-parent promotion.

The intended report path is:

`autonomous_gold_20260715/strategy/archaludon_hierarchical_rules_20260729/DECLINE_KO_AND_ALTERNATE_DAMAGE_AUDIT.md`.

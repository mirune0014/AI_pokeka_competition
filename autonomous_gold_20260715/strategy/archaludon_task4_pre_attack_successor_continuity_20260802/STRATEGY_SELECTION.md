# Archaludon Task 4 strategy selection

## Decision

SELECT exactly one stateless veto-only rule:

`PUBLIC_PRE_ATTACK_EXECUTABLE_SUCCESSOR_BENCH_ZERO_CONTINUITY_GATE_V1`

When an exact terminal win is absent and either the Bench is empty or an exact
public-worst-reply proof shows zero executable backups, SAPT must preserve a
legal parent board-forming action instead of replacing it with a nonterminal
attack. At that boundary, binding uncertainty preserves the parent.

## Frozen parent and evidence

- Parent directory: `autonomous_gold_20260715/packages/archaludon_public_exact_same_active_attack_dominance_v1_clean_20260801_2352/extracted_frozen_verification`
- Parent `main.py` SHA-256: `914B8419ECAFB57D8F0CDC462E6035DB0EE6325044DFBCCE216F0FE759CE92DF`
- Parent `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Replay: `C:/Users/amuam/Downloads/89347400.json`
- Replay SHA-256: `F389CF9FD13BE52D155A3FA7B9FF5750358F3016848640236D4E2562DA1053A4`
- Root analysis: `autonomous_gold_20260715/live/manual_episode_89347400_analysis_20260802/ROOT_REPLAY_ANALYSIS.md`

Tasks 1–3 changed none of the replay's 11 canonical decisions. The inherited
`PUBLIC_SECURED_ATTACK_PURPOSEFUL_PREFIX_TRANSACTION_V1` changed Explorer to
Turbo Flare at step 12 and Ultra Ball to Turbo Flare at step 19, both with
`card_or_target_binding_unknown`. The later lone-Cinderace KO caused board-out.

## Placement

- Implement inside the SAPT section immediately before its existing
  `_practice_bind_attack` / `SECURED_ATTACK_NOW` fallback.
- Do not append an outer wrapper because recovering the pre-SAPT parent there
  would require a second stateful parent call or telemetry rebinding.
- Preserve every active owner, admitted purposeful prefix, defensive evolution,
  terminal rule, and Tasks 1–3.

## Activation

All conditions are required:

1. The existing parent is called exactly once.
2. `_practice_clear_main(obs)` is true.
3. The parent action is valid, single, non-ATTACK, non-END, and non-RETREAT.
4. Existing pre- and post-parent owner fingerprints are empty.
5. `_sapt_attack_boundary` certifies exactly one payable `EXACT` attack.
6. That attack is nonterminal.
7. Bench count and capacity are public and the Bench is not full.
8. Continuity is critical by either:
   - exact Bench count zero; or
   - an exact baseline, worst-public-reply, and backup-conversion proof showing
     `exact_backup_ready is False` with no executable route.

Unknown nonempty-Bench proof does not certify zero successors.

## Parent hold

Preserve the exact parent action for these board-forming families:

- exact-text/bound Poké Pad;
- exact-text/bound Ultra Ball with public minimum discard-cost feasibility;
- exact-text/bound Night Stretcher when public discard contains an exact Basic;
- direct Basic placement;
- at the activated Bench-zero boundary, a valid non-attack parent rejected by
  SAPT as `card_or_target_binding_unknown`.

The last clause restores step 12's Explorer without making Task 4 own Explorer
selection. Task 4 never selects search targets, Ultra Ball costs, recovered
cards, Bench targets, evolutions, attachments, or Turbo Flare allocation.

## Precedence

1. Exact terminal win.
2. Existing inherited or card-specific transaction owner.
3. Task 4 exact parent hold.
4. Existing nonterminal secured-attack fallback.

## Multi-callback behavior

- MAIN: return the exact parent action when the guard holds.
- Search, discard, target, and other continuation callbacks: Task 4 is inactive
  and the once-called parent owns the action.
- Task 4 creates no transaction or watch.
- Identical retries are deterministic and create no state.

## Required focused checks

Positive:

- Episode 89347400 step 12 restores Explorer.
- Episode 89347400 step 19 restores Ultra Ball.
- Bench-zero Poké Pad and a non-Cinderace state preserve parent.
- Exact nonempty no-successor Night Stretcher with public Basic preserves parent.
- Binding-unknown Bench-zero state preserves parent.
- Both seats, option permutations, and identical retries agree semantically.

Negative:

- terminal attack;
- surviving executable backup;
- full Bench or zero-card deck for deck search;
- Night Stretcher without discarded Basic;
- parent ATTACK, END, or RETREAT;
- non-MAIN callback or active owner;
- unknown or ambiguous nonempty-Bench proof;
- multiple or unknown payable attacks.

Every action must remain valid. Compile/import, legal 60-card deck with one ACE
SPEC, last-callable loader behavior, byte-identical non-main files, and a
cache-free candidate tree are mandatory.

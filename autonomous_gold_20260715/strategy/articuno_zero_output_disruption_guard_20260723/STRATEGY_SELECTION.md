# Strategy selection: public Articuno zero-output disruption guard v1

## Judgment

`ACCEPT_TO_IMPLEMENT`

Implement exactly one deterministic public-state rule named `alakazam_public_articuno_zero_output_disruption_guard_v1` directly from formal parent `candidates/alakazam_psychic_readiness_parent_continuation_v3`, policy SHA-256 `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.

Do not branch from or stack exploratory Active-Dudunsparce v4. V4 made zero differences on all `83` callbacks of live loss `87485519`; combining an unrelated Run Away rule would confound attribution.

The controlling evidence is `ROOT_VERIFIED_EVIDENCE.md`. Its hash must be frozen before implementation.

## Hypothesis

When exact public card text certifies that Powerful Hand will place zero counters into a Basic Team Rocket Pok?mon because Team Rocket's Articuno is visibly providing Repelling Veil, do not donate an Active Alakazam for a zero-output attack. If one exact Enhanced Hammer transaction is publicly certified to remove the protected Active's unique Special Energy and make all its printed attacks unpaid, play that Hammer, remove that Energy, and end the turn with Alakazam preserved.

No archetype label, opponent identity, private hand, hidden deck order, replay-specific exception, or opponent-policy inference is permitted.

## Start point and precedence

Call the exact formal parent once. Consider this rule only after the parent has finalized a unique legal Powerful Hand choice. Existing observation/schema validation, duplicate handling, and higher-precedence owner validation run first.

The zero-output predicate invalidates Powerful Hand for every inherited lethal, terminal, or transaction certificate. If an inherited transaction owns the intended Powerful Hand, the implementation may intercept only if its state can be rolled back or explicitly aborted without leaving a stale latch. Otherwise delegate unchanged.

All non-Powerful-Hand parent choices remain exactly parent-owned.

## Mandatory positive gates

Every gate is required.

1. Exact ordinary MAIN schema with complete raw/parsed parity for public board, hand, Energy attachments, options, current owner, and transaction state.
2. Unlocked, paid Active Alakazam `743`; the parent's returned action resolves to the unique legal Powerful Hand `1072` option.
3. An opposing Team Rocket's Articuno `414` is currently public in Active or Bench. Frozen card metadata must exactly match its Basic status, skill name Repelling Veil, and text preventing attack effects to Basic Team Rocket Pok?mon while distinguishing damage from effects.
4. No public ability-negation, skill-suppression, or effect ambiguity can disable or alter Repelling Veil. Unknown or unclassified public effects reject the route.
5. The opposing Active is complete and Basic. Frozen metadata must identify it as a Team Rocket Pok?mon by the exact card-name namespace `Team Rocket's `; do not infer this from the opponent deck.
6. Active Alakazam and attack metadata exactly identify Powerful Hand as counter placement with no ordinary-damage component. Its effective output is therefore certified as exactly zero.
7. At least one legal Enhanced Hammer `1081` PLAY option exists in the current hand. Its frozen text must exactly remove a Special Energy from an opposing Pok?mon.
8. Across all public opposing attachments, exactly one Special Energy is present and exactly one legal Hammer target is possible. That Energy is attached to the protected Active.
9. Removing that Energy leaves every exact printed attack of the unchanged opposing Active currently unpaid under the frozen Energy-unit model.
10. The transaction plan, relevant public fingerprints, stable semantic option keys, parent-state snapshot, and duplicate key are all complete before returning an override.

For live anchors, displayed observation step `87` is replay array index/shadow key `86`, and displayed observation step `105` is replay array index/shadow key `104`. In both states the parent Powerful Hand is replaced by semantic PLAY Enhanced Hammer, whose expected raw option is `0`; raw indices are controls, not rule predicates.

## Transaction

### Stage 1: PLAY_HAMMER

- Select the minimum stable semantic key among otherwise identical Enhanced Hammer cards.
- Return the unique legal PLAY option matching that physical card.
- Freeze the protected Active, Articuno, Hammer, unique Special Energy, remaining Energy units, printed attack-cost proof, current board, and parent state.

### Stage 2: SELECT_SPECIAL_ENERGY

- Require the exact Enhanced Hammer selection context and unchanged frozen public state.
- Select the unique target matching the frozen Special Energy physical fingerprint on the protected Active.
- Duplicates return the cached identical action without another parent call.

### Stage 3: VERIFY_AND_END

- At the next ordinary MAIN callback, verify the Hammer left hand, the exact Energy moved off the unchanged protected Active through an allowed public resolution, all other frozen public components remain consistent, Articuno and its protection remain public, and every printed opposing attack remains unpaid.
- Require one unique semantic END option.
- Return END, clear the candidate latch, and leave subsequent decisions to the exact parent.

At each callback call the parent exactly once under the repository's snapshot/quarantine rules. A successful override commits only the candidate's clean state. A failed or stale continuation clears the candidate latch, restores any quarantined parent state when required, and returns the genuine already-computed parent action. Never synthesize a replay-index fallback.

## Fail-closed negatives

Delegate exactly on any of the following:

- missing, malformed, mismatched, duplicated, or hidden-uncertain raw/parsed data;
- Articuno absent, unknown metadata, public skill suppression, or effect ambiguity;
- evolved Team Rocket target, non-Team-Rocket target, or incomplete target lineage;
- an ordinary-damage attack, Kadabra Super Psy Bolt, or any attack other than exact Powerful Hand `1072`;
- no Hammer, ambiguous Hammer semantics, no Special Energy, multiple opposing Special Energy targets, or the unique Energy not attached to the protected Active;
- post-Hammer opposing attack still paid, attack-cost uncertainty, or unknown Energy unit;
- missing or nonunique END;
- stale transaction fingerprint, duplicate mismatch, another owner with unsafe rollback, or any continuation mismatch.

## Positive controls

- Episode `87485519` at shadow keys `86` and `104`: protected Basic Team Rocket's Mewtwo ex with unique Team Rocket's Energy `15`; start Hammer at both points.
- Both semantic seats for each anchor.
- Protected Basic Team Rocket's Mewtwo ex, Articuno, Murkrow, and Porygon synthetic/public-metadata variants when all Hammer-denial gates hold.

## Mandatory negative controls

- Evolved Team Rocket Porygon2 and Honchkrow remain eligible for Powerful Hand under Articuno.
- Kadabra's ordinary-damage Super Psy Bolt remains eligible into protected Basics.
- Articuno absent; non-Rocket Basic; malformed or suppressed Articuno; unknown public effect.
- Zero, ambiguous, multiple, Benched-only, or non-Special Hammer targets.
- Removing the unique Special Energy still leaves any printed Active attack paid.
- Duplicate callbacks, stale target, changed Active, changed Articuno, changed Energy, missing END, and higher-precedence parent ownership.

## Breakage-only release gate

No win-rate uplift is required. Weak local results alone do not block the user-authorized exploratory submission. Every structural gate below is mandatory:

1. Exact parent diff: deck unchanged; only one isolated guard/transaction module plus the minimum final-policy hook.
2. Compile/import pass; legal 60-card deck with exactly one ACE; loader sees only/last callable `agent`; cache-free candidate and package.
3. Focused positive and negative suite covers every gate above in both semantic seats with deterministic duplicates and zero invalid actions or latch leaks.
4. Exact checked-engine continuations from both live anchors in both semantic seats complete Hammer to Energy `15` to END, cross the opponent turn boundary without the immediate Erasure Ball KO, and leave no stale state.
5. Callback-complete current-live and historical shadows have exact schedule equality, only certified Articuno-guard first differences, and zero invalid actions, duplicate mismatches, parent-call mismatches, emergencies, mandatory fallbacks, or unclassified differences. Inspect every changed position.
6. Both-seat packaged smoke has zero action errors and max-step hits; extracted package equals staging and all frozen hashes match.

Any failure above blocks packaging or submission. If the natural replay shadow cannot validate the post-divergence continuation, the checked-engine anchors are mandatory; static counterfactual aborts after the first changed action are not live failure evidence.

## Expected trade-off

The rule spends one Hammer and lowers later Powerful Hand by 20 while intentionally taking a no-attack turn. In exchange it removes a two-unit Special Energy, makes the current attacker unpaid, and preserves a Stage 2 that otherwise produces exactly zero before being KO'd. The narrow public text, target-stage, unique-Energy, and attack-denial gates contain the regression risk.

# Rule 3 controlling amendment: parent-prefix completion v1

This amendment controls the next repair of Rule 3 only. It supplements
`REQUIREMENTS_AMENDMENT_RULE3_REPAIR_V2.md`; it does not modify Rules 1, 2, or
4--10, the Historical-Silver scorer, the deck, the single-resolver structure,
or the public agent interface.

## Frozen inputs and diagnosis

- Candidate before this amendment:
  `archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- Pre-amendment candidate SHA-256:
  `1C5676A97783B17D0A4B1D2D647777975463CF8759DA534A62CA47F2D0C39BE2`
- Historical-Silver module SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Fixed-160 result for the pre-amendment SHA: baseline=candidate `100/160`,
  gains/regressions/ties `0/0/160`; all 160 traces were identical and Rule 3
  had no natural start in that panel. This is safety evidence only and must not
  be reused after this amendment.
- Natural Active-ex route: seat 1, seed `271958323`, opponent
  `archaludon_shumpei_current_v3`. Ultra Ball, Archaludon ex evolution, and
  Assemble Alloy completed, but the candidate forced Metal Defender at step
  40 and lost. Historical-Silver selected Lillie first, then Poké Pad/search,
  another Ultra Ball, Basic placements, and finally Metal Defender, and won.
- Natural Turbo route: seat 0, seed `271958324`, the same opponent. The parent
  selected physical Metal options `[0,1,2]`; Rule 3 selected `[0,3,1]`. Both
  won, so this is an unnecessary physical-copy divergence.

The defect is implementation-level: after reaching attack readiness, Rule 3
mistook “a complete route exists” for “attack must be emitted immediately.”
Rule 3 remains required and must be repaired rather than abandoned.

## A. Active-ex Historical-Silver setup prefix

After Assemble Alloy and any required manual attachment establish exact Metal
Defender readiness, do not force the attack. Enter the sole-owner stage
`ACTIVE_READY_PARENT_PREFIX` with the original seat, turn, evolved Active
Archaludon ex serial/lineage, current action count, a zero unique-callback
count, and `prefix_effect_open=false`.

The once-called Historical-Silver action for every callback is authoritative:

1. A terminal game result completes Rule 3 normally.
2. A changed seat, turn, Active serial, Active card identity, or evolution
   lineage is an explicit irreversible abort. Return that callback's exact
   parent action and never force an attack.
3. On every MAIN callback, exact unique Metal Defender must remain legal.
   Losing readiness is an explicit irreversible abort.
4. If the parent selects exact Metal Defender, emit the exact parent physical
   action, enter `ATTACK_EMITTED`, and complete only after the attack receipt.
5. A different attack, RETREAT, or END is an explicit irreversible abort. Emit
   the exact parent action; never replace it with Metal Defender.
6. A single legal parent PLAY, ATTACH, EVOLVE, ABILITY, or DISCARD action is
   emitted byte-for-byte, the Rule 3 owner is retained, and its effect chain is
   opened.
7. During an opened non-MAIN effect chain, emit every legal parent choice
   byte-for-byte. Do not rescore searches, discards, yes/no decisions, targets,
   or card choices. Returning to MAIN closes the effect chain and resumes the
   checks above.
8. An unowned effect prompt, invalid or multi-action MAIN choice, or
   unclassified parent choice is an explicit irreversible abort.

The parent is still called exactly once per callback. Rules 1, 4, and 5 cannot
start while Rule 3 owns the transaction.

## B. Duplicate, ordering, and boundedness

- Use the existing semantic prompt key and physical option specifications.
- An identical retry does not advance stage, action count, or callback budget.
- Rebind the originally selected physical card, target, and attack identifiers
  into the new option order. Confirm the new parent action selects the same
  semantic and physical references. Mismatch or failed rebind is an explicit
  `prefix_duplicate_parent_mismatch` abort.
- Every nonduplicate callback must have monotonic `turnActionCount`.
- Accept at most 64 nonduplicate prefix callbacks. Exhaustion is an explicit
  abort and cannot force Metal Defender.

## C. Turbo Flare physical Metal preservation

At Turbo Flare `ATTACH_TO`, define:

```text
required_count = min(3, select.maxCount, number_of_unique_legal_basic_metal_options)
```

If the once-called parent action is legal, selects exactly `required_count`
unique Basic Metal options, and all selected serials are present, preserve its
action list and order exactly and save the Metal serials in that order. The
existing Rule 3 target continuation then attaches those exact copies to the
searched Duraludon.

Only when the parent action is ineligible may Rule 3 use the existing
deterministic serial-ordered fallback for `required_count` cards. Duplicate
callbacks rebind the initially saved serial order and never switch to later
parent-selected copies.

## Required verification before evaluation

- Focused fixtures in both seats for immediate Metal Defender and for the full
  Lillie -> Poké Pad/search -> Ultra Ball -> Basic placement -> Metal Defender
  parent prefix.
- MAIN and effect-prompt duplicate retries plus option-order permutations.
- END, RETREAT, other attack, Active change, turn change, readiness loss, and
  callback-budget exhaustion: all explicit irreversible aborts with no forced
  Metal Defender.
- Turbo counts 0/1/2/3, eligible parent-copy preservation, ineligible-parent
  fallback, duplicate retry, and option reordering.
- Exactly one parent call per callback; existing Rule 1/4/5 fixtures remain
  passing; compile/import, legal 60 cards, ACE SPEC one, single resolver, and
  cache-free tree remain passing.
- Natural Active seed `271958323` must preserve the complete parent prefix,
  retain Rule 3 ownership until the parent Metal Defender, complete without an
  irreversible abort, and restore the parent win.
- Natural Turbo seed `271958324` must remove the first physical-copy
  divergence and complete without an irreversible abort.
- Former failure seed `271958318` must remain trace-identical to the parent.

Any natural Rule 3 start that ends in an irreversible abort rejects the
implementation, not the Rule 3 hypothesis. After these gates, freeze a new
candidate SHA and rerun the immutable fixed-160 schedule in a new destination.
Do not overwrite or reinterpret the earlier fixed-160 output.

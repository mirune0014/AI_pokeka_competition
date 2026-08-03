# Live-evidence addendum: Active-Kadabra stage-up v1

Date: 2026-07-18 JST  
Owner: root  
Decision: **continue Decision A for one isolated exploratory probe**.

## New fact and corrected attribution

Submission `54799469` added 26 public episodes after the previous snapshot.
Root's corrected verification is
`analysis/live_54799469_new26_1606_20260718/ROOT_NEW26_VERIFICATION.md`,
SHA-256
`5A02189DACF9871DAAA803DA9C8E33576B0C3BC2BC0822860BD15CFF2B6C308D`.

Across the 26 exact IDs and 1,741 target callbacks, the submitted certified
turn-plan candidate differs from exact v3 five times.  Its reserve-attachment
transaction completes once.  All four `EVOLVE_ACTIVE_READY` transactions are
incomplete but fail-closed: after Abra evolves, live state stores the former
Abra in Kadabra's `preEvolution`, so the old top-level `source_serial` lookup
fails at ACTIVATE.  Exact-v3 delegation happens to choose the same YES and
later Super Psy Bolt.  Those fallback actions are valid but are not certified
transaction completion.

This rejects the evolution branch of the already submitted turn-plan
candidate.  It corrects root's initial completion attribution and reinforces
exact v3 as rollback.

## Why it does not invalidate this frozen candidate

The Active-Kadabra stage-up candidate is not stacked on the turn-plan source.
Its exact parent is strict-Prize v3, SHA-256
`49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`.

Root directly re-read the frozen stage-up implementation.  Its continuation
does not search for the old Kadabra as a top-level Pokemon.  Function
`_stage_up_evolved_active_is_exact` requires:

- Active top ID is the new Alakazam;
- Active top serial is the selected Alakazam card serial;
- the prior evolution fingerprint ends with Kadabra and the frozen source
  serial;
- HP, energy, tools and the complete prior evolution chain remain exact.

This explicitly models the same live serialization contract that broke the
unrelated Abra-to-Kadabra transaction.

Root reran all 12 focused stage-up tests with CPython 3.11.6.  They exited 0.
The checked engine again completed all three exact transactions:

- S119: `EVOLVE -> YES/draw3 -> Powerful Hand 380 -> resolution`, three Prize;
- S128: `EVOLVE -> YES/draw3 -> Powerful Hand 400 -> resolution`, one Prize;
- S137: `EVOLVE -> YES/draw3 -> Powerful Hand 420 -> resolution`, one Prize.

The 48 named retention callbacks and 532 full-v3-win callbacks also passed.
The same 26 new public episodes contain zero stage-up-versus-v3 differences,
so they do not directly exercise or falsify the stage-up mechanism:

- comparison script SHA-256:
  `42406B61C2E17C62B0B581DC1856B88C98F8A59A5788A645127995AC3CCCE45A`;
- comparison output SHA-256:
  `DC0CD449CAD25721B4983288D1854CCB34D41E41E4DAA36B9C859952A56AA1C3`.

## Condition 6 clarification

The pre-submit safety condition applies to a violation in this frozen
candidate or to a demonstrated shared engine/serialization contract that
invalidates one of this candidate's certified assumptions.  An unrelated,
non-stacked candidate's incomplete latch does not globally block every later
candidate.  Its shared contract must still be checked; that check passes here
because the stage-up implementation expects the new top serial and old source
inside `preEvolution`.

Decision A therefore remains valid, subject to all original conditions plus:

1. bind the corrected new-26 verification and this addendum in the pre-submit
   decision record;
2. perform a new immediate authenticated refresh and abort on any new
   stage-up-specific or shared-contract violation, hash drift, duplicate or
   missing quota;
3. treat the first live `EVOLVE` activation as incomplete if the stage-up
   latch does not itself control YES, draw resolution and Powerful Hand.  A
   coincidentally identical fallback action does not count as completion;
4. on such an incomplete activation, reject the candidate and roll back to
   exact v3 immediately.

Scores `735.3` and `763.3` are not causal evidence for this rule.  This remains
one live-learning probe, not adoption or promotion.

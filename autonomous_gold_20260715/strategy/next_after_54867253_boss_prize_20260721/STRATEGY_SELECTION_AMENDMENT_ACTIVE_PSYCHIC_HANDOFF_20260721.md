# Controlling amendment: certified Active-Psychic ownership handoff

- Frozen by root: 2026-07-21 JST
- Original strategy:
  `STRATEGY_SELECTION.md`
- Original strategy SHA-256:
  `60DAF43E3F4133832127F4BE78B3E0906451A152B2EE0EB37CEEBAD0EA0651BF`
- Exact live parent SHA-256:
  `7838FBFF3CBA3AE5D9142E45B1334B192A5E758CFFA5598AF2A626E5C7D636E3`
- Root latch reproduction:
  `analysis/54867253_new17_boss_prize_20260721/root_verify_87214287_latch.json`
- Root reproduction SHA-256:
  `2FFB13B2CD259034A892C627C92F94ED37DC06A4B8840935CA19ACC7609C3145`
- Reproduction script SHA-256:
  `2BE3C111248C21C579784CDE997D1F98843C44E00201FB7E65FCB7C781C50009`

This amendment controls only the inherited-latch ownership gate of the
original exact Prize-lane Boss strategy. Every other original requirement,
positive, negative, regression gate, package gate, and submission condition
remains controlling.

The transient source SHA
`E8BBBA76BE032B2936FF1A6755E81924AD446646359534BCB8DBC3FA6F0FA097`
is unfinished and must never be packaged or submitted. Rebuild the amended
candidate in a fresh destination directly from the exact live parent.

## Root-verified contradiction

Sequential replay `87214287`, seat 1, proves:

1. At S128 the live parent attaches exact Psychic Energy and creates the sole
   `_active_psychic_ko_latch` at `stage="await_attack"`.
2. At S129 the live parent revalidates the exact post-attach state, returns
   the unique Powerful Hand, and changes only that latch stage to
   `"await_resolution"`.
3. A fresh isolated S129 has no certificate and returns ATTACH, so isolated
   activation is forbidden.

The original blanket prohibition on inherited ownership therefore conflicts
with the mandatory S129 terminal-Boss positive. The strategy is amended with
one named, exact ownership handoff; there is no general inherited-latch
relaxation.

## Exact entry certificate

The ordinary no-latch Prize-lane rule remains unchanged. The new handoff is
eligible only when all of the following hold before calling the exact parent:

1. The outer Boss latch is empty.
2. `_active_psychic_ko_latch` is the only nonempty inherited latch; its exact
   key set and every value are frozen, and `stage == "await_attack"`.
3. Turn, player, attacker, current target, selected Energy, post-attach hand,
   Prize counts, conservative damage, and every stored serial/fingerprint
   match the current public callback.
4. `_active_psychic_post_attach_is_same` passes.
5. The callback is first-seen ordinary MAIN, raw and parsed state agree,
   supporter is unused, and exactly one legal Powerful Hand exists.
6. Freeze the complete callback plus every mutable parent policy field: all
   seven inherited latches, semantic-failure state, decision cache,
   `pre_turn`, and both ability flags.

Run the exact parent once. Handoff remains eligible only when:

- parent returns that unique Powerful Hand;
- the sole Active-Psychic latch changes only
  `await_attack -> await_resolution`;
- every other latch key/value is byte-equivalent;
- parent cache changes only to this callback signature and Powerful Hand;
- no semantic-failure state, flag, or other mutable parent field changes.

Any cached shortcut without the stage transition, latch clearing, payload
mutation, alternate action, extra latch, or unrelated mutation forbids
takeover.

## Permitted handoff decision

Reapply every original exact metadata, field, hand, Energy, protection,
status, Stadium, Prize, damage, and legal-option check. Handoff may start only
when exactly one semantic terminal lane exists and it is a Bench target
reached by Boss.

- Equivalent physical Boss copies collapse to one semantic lane; remove the
  exact chosen serial from the projected hand and use the lowest legal Boss
  option index.
- Multiple terminal targets, an Active terminal lane, no terminal lane,
  insufficient post-Boss damage, or any uncertainty returns the parent
  Powerful Hand unchanged with its legitimate `await_resolution` state.
- The `87220395` higher-Prize Active preservation route remains governed only
  by the ordinary no-inherited-latch gate.

## Atomic commit and rollback

Build and validate the complete outer Boss latch and Boss action in local
temporary state first. Only after every check passes:

1. install the outer latch with
   `origin="certified_active_psychic_handoff"` and the frozen source
   certificate;
2. clear only `_active_psychic_ko_latch`;
3. clear the parent decision cache containing the unexecuted Powerful Hand;
4. cache and return the chosen Boss action.

If construction or commit fails, restore the exact legitimate parent
post-call state (`await_resolution` and cached Powerful Hand), clear any
partial outer state, and return Powerful Hand. Never call broad emergency
clearing.

After a Boss action has actually been returned, never resurrect either
Active-Psychic stage. The outer transaction subsumes its remaining attack
obligation.

## Continuation, speculative parent calls, and duplicates

Freeze the exact Boss serial, target, attacker, ordered hand, Prizes, both
fields, Energy/tools/evolutions, discards, deck counts, status, Stadium,
action count, option envelope, and expected logs. Require exact transitions:

`Boss PLAY -> frozen target -> exact field permutation -> unique lethal
Powerful Hand -> verified KO/prize prompt`.

For each new continuation callback:

1. snapshot complete parent mutable state;
2. run parent once to obtain a genuine fallback;
3. if the outer override succeeds, restore the speculative parent pre-call
   state before returning it;
4. if validation fails, clear only the outer latch, retain the parent
   post-call state, and return its valid action.

After verified attack resolution, clear only the outer latch/cache and let
the live parent select Prizes.

Check the outer duplicate record before invoking parent. Reuse it only when
full raw signature, transaction identity, and expected post-stage all match;
then return the identical action with zero parent calls and zero latch
advancement. A stage or identity mismatch invalidates the cache and follows
normal fail-closed processing.

## Required focused controls

In addition to every original negative, mutate each field independently:

- Active-Psychic latch missing/extra key, wrong stage/turn/player, changed
  serial/fingerprint, hand, Prize, Energy, target, or damage;
- any concurrent inherited latch, especially stranded-retreat;
- parent action other than Powerful Hand, missing stage transition, cache
  mismatch, or any unrelated parent-state mutation;
- fresh isolated `87214287/S129`;
- Active terminal, multiple terminal targets, nonterminal Boss, malformed or
  duplicate option mapping, unknown Prize metadata, modifier/protection/
  status, or damage shortfall;
- target prompt, hand/discard, field permutation, action count, log,
  attack option, and resolution mutation;
- duplicate callback at every stage, stale duplicate after advancement,
  exception before commit, abort after Boss, and turn/seat/game boundary.

Mandatory positives and retention:

1. Full sequential `87214287` from S128 through terminal Prize collection in
   both semantic seats; clear the old latch only on committed handoff.
2. `87220395` Active-preservation route in both semantic seats.
3. Callback-complete `87213204` identity through RETREAT, payment, promotion,
   Powerful Hand, and board-out win.
4. All broad Boss-v1 9/144 regressions, current replay corpus, and historical
   shadows remain parent-identical outside classified starts.

Run the original fixed both-seat Historical-Silver, Mega Lucario, mirror, and
Starmie smoke, then clean package/re-extract gates. One exploratory submission
remains permitted only after every amended gate passes and a fresh
authenticated Kaggle refresh reveals no contradictory evidence.

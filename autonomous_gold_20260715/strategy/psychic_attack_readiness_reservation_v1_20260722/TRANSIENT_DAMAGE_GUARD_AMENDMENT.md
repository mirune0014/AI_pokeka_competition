# Controlling transient-damage guard amendment

This amendment supersedes the original classification of episode `87355030`,
semantic seat 1, step 73 as a positive Super Psy Bolt route. All other frozen
scope boundaries remain controlling.

## Root-verified contradiction

At replay step 64/65, Mega Abomasnow ex `723/s12` used Frost Barrier `1047`.
The public attack text states that during the opponent's next turn this Pokemon
takes 30 less damage from attacks. At step 73 the proposed Kadabra Super Psy
Bolt `1071` deals 30 before that transient reduction, so its resolved public
damage is zero, not a strictly positive outcome. The previous candidate SHA
`4CE2A8D248A09277A943232F30712DFB61850CDB9BD30E55E1660EA63FA130A1`
therefore fails the frozen exact-positive-outcome contract and must never be
submitted.

Evidence replay:

`autonomous_gold_20260715/live/54888159/refresh_20260722_0956_root/episode_87355030_replay.json`

## Exact correction

Keep the same single Psychic-readiness hypothesis and parent. Add one
public-state, card-text-derived fail-closed guard to
`_strict_positive_outcome`:

- For an `ATTACK_DAMAGE` readiness route, inspect every attack printed on the
  unchanged public target Pokemon.
- Normalize the public attack text using the existing deterministic text
  normalizer.
- If any printed attack contains `during your opponent's next turn` together
  with either `less damage` or `prevent all damage`, the current snapshot alone
  cannot certify that the transient modifier is inactive. Reject the readiness
  override and return the exact parent action.
- Do not hard-code episode IDs, opponent names, deck archetypes, target card
  IDs, or hidden/history-derived state.
- Do not apply this damage guard to Powerful Hand, which places counters rather
  than doing attack damage.

This deliberately conservative rule may miss a safe chip attack when the
printed guard was not used. That is preferable to certifying zero damage as
positive and remains within the frozen fail-closed policy.

## Required evidence after the edit

1. `87355030/S73` is parent-identical in both semantic-seat fixtures and never
   starts a Psychic-readiness transaction.
2. H0 exact-engine routes remain complete in both semantic seats for:
   - `87368866/S77` (Basic Psychic to active Alakazam, then Powerful Hand);
   - `87374791/S109` (Basic Psychic to active Kadabra, then Super Psy Bolt).
3. H1 exact-engine forced-promotion and immediate-attack routes remain complete
   in both semantic seats for `87356191/S28`.
4. Synthetic positive/negative tests cover target attacks with `less damage`,
   `prevent all damage`, ordinary attack text, and Powerful Hand counter
   placement.
5. Re-run compile/import, legal deck, loader-only/last, duplicate/stale/owner
   controls, current39 and historical callback-complete shadows, every changed
   first position, deterministic repeated smoke, immutable baseline/candidate
   panel, numerical audit, package extraction/loader/both-seat smoke, and all
   hashes from the new source. All evidence and the archive from SHA `4CE2...`
   are stale and cannot authorize a write.

The live-probe decision remains breakage-only: local wins and losses are
diagnostic, but any invalid action, stale transaction, false positive outcome,
non-determinism, packaging failure, or source drift blocks submission.

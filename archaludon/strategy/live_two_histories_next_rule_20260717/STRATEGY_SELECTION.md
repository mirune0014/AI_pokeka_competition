# Live two-history next-rule selection: Fez immediate-KO escape bridge

Date: 2026-07-17 (JST)  
Role: read-only Sol-Ultra strategy judge  
Decision: select exactly one isolated deterministic rule; no battle, source,
package, or Kaggle write was performed.

## Authorities rehashed and read

| Authority | SHA-256 |
|---|---|
| `LIVE_54769337_COMBINED24_QUALITATIVE_DIAGNOSIS.md` | `AE6FEC424D4437230BDBE752C8763775BEA1E7F4CC365E72E947B6C0430DBF97` |
| `LIVE_54770067_CURRENT28_QUALITATIVE_DIAGNOSIS.md` | `D87CB8C3B3B3E215730A91091A9B23E9B1E992A4745308696278EB908C29D020` |
| current two-history `ROOT_VERIFICATION.md` | `C320681E4F3AA27214CE08778938DA515A6C533090E132D0BE88CF849A2DCB65` |
| submitted v3 `main.py` | `5F8F6578BF98BC285BB468FAD26969A22EDA96378F8E3AE35F134EA70EB91830` |
| submitted fragile-guard `main.py` | `60D61F4269566B5E922EA9044A32A0B3BA5BB769F8AE9959E86C0EDCB008A9C9` |
| unchanged legal `deck.csv` | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |

The live histories are diagnosis evidence only, not action labels or an
opponent-policy proxy. At the current verified snapshot, v3 is `23-23` at
`656.0055705801833` and fragile guard is `22-25` at
`694.0872916609401`; neither score proves the rule below.

## Selected hypothesis

Select **`alakazam_fez_ready_attacker_immediate_ko_bridge_v1`**.

The submitted source's RETREAT whitelist omits Fezandipiti ex `140`. Across
both submissions, public states repeatedly contain Active Fez, an already
energized Bench Alakazam, and a legal immediate Powerful Hand knockout. The
repair is one complete transaction, not a generic Fez preference:

`RETREAT Fez -> exact frozen payment -> exact frozen energized Alakazam ->
immediate Powerful Hand 1072 KO`.

### Exact start predicate

The overlay may replace the unchanged parent's first choice only when every
condition below is public and true.

1. Selection context is own `MAIN`, turn is at least 2, no bridge latch is
   active, retreat has not already been used, and the unchanged parent does
   not already choose a legal immediate attack.
2. Own Active is Fezandipiti ex `140` with a positive serial. A legal RETREAT
   option exists. Retreat cost, attached energy units, and the exact attached
   card serial(s) that pay it are known. Ambiguous or underpaid costs fail
   closed.
3. At least one Bench Alakazam `743` has a positive serial and Psychic Energy
   `5` or `19` attached. Freeze one destination by: most attached cards, then
   lowest Bench index, then lowest positive serial. Do not count an
   unenergized Alakazam or Kadabra.
4. Opposing Active has a positive serial, positive remaining HP, and a complete
   public fingerprint (card/serial/HP/evolution stack/Energy/Tool/status).
   Mist Energy `11`, or Rock Fighting Energy `20` on a printed Fighting
   Pokemon, blocks the certificate. Any unknown protection also fails closed.
5. Powerful Hand `1072` will be legal after promotion and
   `20 * current_hand_count >= opposing_remaining_HP`. No future draw,
   evolution, Supporter, search, or opponent action may be assumed.
6. Let `post_KO_prizes = own_prizes - public_prize_value(opposing Active)`.
   Require `post_KO_prizes == 0` or `current_deck_count > post_KO_prizes`.
   Equality fails closed.

### Frozen latch and clear conditions

The implementation must use one explicit state machine.

1. At certified `MAIN`, freeze turn/player, Fez serial, exact payment serials,
   destination Alakazam serial, target fingerprint, hand/deck/prize counts;
   choose RETREAT only.
2. At the engine's retreat-payment selection, choose only the frozen attached
   card serial(s). On any different context or unavailable serial, clear and
   delegate unchanged parent; the integrated smoke fails.
3. At `TO_ACTIVE`, choose only the frozen energized Alakazam serial.
4. At the next same-turn `MAIN`, require the frozen Alakazam Active with
   Psychic attached, unchanged target fingerprint, unchanged hand/deck/prize
   certificate, no protection, and legal attack `1072`; choose it immediately.

Clear on turn/player change, any unexpected context, missing/nonpositive or
changed serial, changed hand/deck/prizes, changed target HP/attachments/status,
lost Energy, absent attack, failed damage, or failed post-KO clock. The latch
must not choose setup, draw, Boss, attachment, evolution, or a second retreat
between its stages. Any mismatch after irreversible RETREAT is an engine-smoke
failure and blocks promotion even if fallback remains action-valid.

## Required live anchors and boundaries

The implementation worker must bind exact raw observations, not hard-code
episode IDs.

Positive anchor set:

- `86386369 S48` (loss): Active Fez with Telepath; energized Bench Alakazam;
  hand 12; opposing Solrock 110 HP; projected Powerful Hand 240.
- `86430395 S90` (loss): Active Fez with Telepath; energized Bench Alakazam;
  hand 13; opposing Crustle 150 HP; projected 260; Alakazam is non-ex, so the
  public ex-only prevention does not invalidate the attack.
- `86387293` (loss; first certified state in the raw replay): Active Fez with
  Enriching, energized Bench Alakazam, legal retreat, and immediate public KO.
- `86385015` (loss): include every Fez/ready-Alakazam retreat state in the
  directed audit. It may fire only where the full HP/protection/clock
  certificate is true; near-states must fail closed rather than be force-fit.

Mandatory win boundaries are `86387405` (first analogous certificate at
`S54`) and `86381796`. Both must remain wins in the checked-engine directed
fixture, and every earlier nonqualifying observation must stay parent-identical.
Replay continuation after first divergence is not counterfactual evidence.

## Immutable Phase 0

Run parent and candidate with the same checked engine, explicit decks,
`--engine-seed`, `--max-steps 1000`, and traces for both seats on exactly these
eight opponent/seed pairs (16 paired keys, 32 one-game commands):

- `new_fresh/great_tusk/{p0,p1}/2026091708,2026091718,2026091725`;
- `new_fresh/mega_lucario/{p0,p1}/2026091723`;
- `new_fresh/dragapult/{p0,p1}/2026091735`;
- `fresh/starmie/{p0,p1}/2026081710`;
- `new_fresh/starmie/{p0,p1}/2026091719`;
- `new_fresh/alakazam_rmy/{p0,p1}/2026091723`.

Before those games, a checked-engine directed fixture must execute the exact
four-stage chain on each qualifying live anchor and must prove fail-closed
behavior on the named near-states and win boundaries.

Phase 0 passes only if:

1. compile/import, legal unchanged 60-card deck, both-seat smoke, and hashes
   pass; all 32 commands exit 0 with unique/equal schedules, zero action error,
   retry, malformed result, duplicate, or max-step hit;
2. every certified directed anchor executes RETREAT/payment/frozen
   promotion/immediate `1072` KO, while every failed predicate is exactly
   parent-identical;
3. candidate has zero parent-win regression across the 16 local keys, both
   named live win boundaries remain wins, and all inherited fragile/Enriching
   changed-key controls retain their accepted outcomes;
4. every changed key repeats candidate-only three times byte-identically and
   every first divergence is solely this latch;
5. no broad or submission promotion occurs if the directed engine cannot
   complete the latch or if a changed local key regresses. Phase 0 is a
   mechanics/safety screen, not a win-rate estimate.

Any later broad run must use the accepted parent's frozen 1,440-key schedule,
finish at least level with that parent, have zero parent-win regression and no
negative seat/panel/opponent floor, retain inherited gains, and have every
changed trace predicate-certified.

## Why the other hypotheses wait

Boss Active-KO superiority/frozen-target transaction is second. Its source
defect is direct, but same-Prize Boss can remove a more valuable future threat;
the current evidence includes winning boundaries, so a broad tie-suppression
rule has materially greater win-line risk than the exact Fez KO bridge.

The executable terminal-KO deck-clock certificate is third. It directly
explains three deck-zero losses, but must prove attacker, evolution, attach,
Boss, costs, target, protection, damage, and final Prizes while preserving
legitimate terminal draws. That larger transaction has more ways to suppress
a winning line. Preserve-Psychic and Starmie-to-Shaymin remain narrower later
families and are not stacked here.

## Implementation-parent condition

Do not implement until the corrected Enriching broad audit and final judgment
are recorded. Then branch from the strongest **locally accepted deterministic
parent at implementation time**, rehash it in the freeze, and add only this
one overlay. If Enriching is rejected, fall back to accepted fragile guard
`60D61F...`; if accepted, use its finally frozen source. Do not stack unresolved
siblings or merge this rule with Boss, deck-clock, Starmie, or Psychic-routing
changes.

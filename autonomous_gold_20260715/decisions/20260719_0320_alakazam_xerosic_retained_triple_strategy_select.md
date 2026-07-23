# Alakazam exact-Xerosic retained-triple strategy selection

- Recorded: 2026-07-19 03:20 JST / 2026-07-18 18:20 UTC
- Root-owned workspace: `autonomous_gold_20260715`
- External writes in this cycle: none

## Frozen parent

- Candidate: `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`
- `main.py` SHA-256: `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`
- `deck.csv` SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`

## Rejected predecessor

`alakazam_recycle_pad_alakazam_attack_line_v1` is rejected and must not be
packaged or submitted.  Its fixed 144-row Phase-0 result was exact parity with
the parent: 86-58 overall, P0 45/72, P1 41/72, paired gains 0 and paired
regressions 0.  It activated in only one row and failed its frozen contiguous
transaction gate.

Root and Sol-Ultra diagnosis located the abort at order 16 step 166.  Poké Pad
exposes `TO_HAND` with `minCount=0,maxCount=1`, while the rejected overlay
required `minCount==1`.  Allowing only 0 or 1 completes the intended
Ash -> Pad -> Alakazam -> immediate Active evolution -> Psychic Draw route,
but the game still loses.  This repair is technically sound but deferred
because it addresses a later and less frequent branch than the repeated live
Xerosic defect.

## Live evidence for the selected sibling

- Episode 86657890 replay SHA-256:
  `E4B18E0A357195BB35F8272A012AA7C48128D3FBDC40FCA18848B494A48FBABF`
  - step 133 Xerosic discard removes the held Alakazam even though an energized
    Kadabra is the public successor after the Active Alakazam is removed.
- Episode 86666507 replay SHA-256:
  `17D8A116CDF58F819CFD264AD8D70A889F5FF4E926C3347CE441E68426CD6867`
  - step 108 Xerosic discard retains two redundant Rare Candy while removing
    both live Dudunsparce, all visible draw supporters, and Telepath Energy.

The submitted stage-up source and the exact-v3 parent chose the same actions at
all target decisions in the six audited Alakazam losses.  The stage-up overlay
therefore did not cause these failures.  The exact-v3 source has no
`SelectContext.DISCARD` scoring branch, so tied zero scores fall through to
hand/option order.

## Selected isolated hypothesis

Create `candidates/alakazam_xerosic_certified_retained_triple_v1` directly from
the frozen exact-v3 parent.  On an exact, fully certified Xerosic (`effect.id ==
1197`) own-hand discard-to-three callback only, enumerate every legal retained
triple.  Select deterministically by public attack-continuity and successor
readiness across both Active-survives and Active-is-removed branches, then
discard the complement.  Complete successor, draw/recovery, energy, and
executable disruption roles outrank redundant resources without a marginal
public role.

The rule must fail closed on malformed or ambiguous option mappings and must
preserve the parent byte-for-byte outside the exact callback.  It must not use
hidden-card assumptions, learned scoring, replay-derived opponent-policy
proxies, or any recycle overlay.

## Decision

- Recycle repair: `DEFER`
- Next candidate: `IMPLEMENT`
- Candidate worker: a newly spawned `ptcg_candidate_worker`; its configured
  `gpt-5.6-sol` xhigh implementation run uses the requested Fast tier.
- Broad evaluation and Kaggle write: not authorized by this selection alone;
  they require the normal frozen implementation, engine, paired-evaluation,
  numerical-audit, packaging, and pre-submit refresh gates.

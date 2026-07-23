# Continuity2 v1 immutable implementation specification

Frozen by the root agent on `2026-07-16` before source writing.

## Inputs and destination

- Frozen source directory:
  `autonomous_gold_20260715/candidates/historical_silver_lucario_pokegear_duplicate_boss_continuity_v1`.
- Frozen `main.py` SHA256:
  `A69E2C5915355D402B314AA4BC66D933B68A5C0E2976A86905238A97EB6093AE`.
- Frozen `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Isolated destination:
  `autonomous_gold_20260715/candidates/historical_silver_continuity2_v1`.
- Deck, `cg/`, and requirements must remain byte-identical. No existing candidate,
  baseline, package, tool, meta agent, or documentation file may be modified.

## Single hypothesis

A deterministic public-state certificate that binds the current attacker (`H0`),
the next own-turn attacker (`H1`), and a pivot/promotion body (`H2`) through one
exclusive resource ledger will reduce missed attacks and stranded Energy without
damaging established setup, immediate attacks, blockers, or adjacent matchups.

This is one behavior theme: `BUILD_SUCCESSOR / RECOVER_ATTACK`. It is not a set of
matchup patches.

## Explicit exclusions

- Boss target or general Boss timing changes.
- Multi-turn `PrizeLane` or prize-map optimization.
- General Pokegear/Supporter-role redesign, including the fourth-Boss Alakazam case.
- Matchup detector redesign, disruption, deckout policy, or deck changes.
- RL, learned scores, behavior cloning, Gold-action imitation, opponent-policy
  templates, hidden-hand guesses, native-engine search, or random rollout.

## Semantic foundation

Implement a pure public-state planner and typed helpers sufficient for the
certificate:

- one shared turn budget for manual attachment, Supporter, Stadium, retreat, and
  the current attack opportunity;
- stable option and in-play identity keys;
- attack readiness from printed Energy and current state;
- explicit attack-damage versus placed-counter handling for visible response
  threats used by the point controls;
- explicit known prevention for Mysterious Rock Inn and Cornerstone Stance, and
  no certificate when an unsupported effect makes the result unknown;
- visible payable opponent response envelope with Active damage/counters and
  Bench spread; no unseen card or future draw is assumed;
- deterministic fallback; `random.sample` is removed.

The simulator's legal options remain authoritative. The planner must not invent
an action that is absent from `Options[]`.

## Certificate

Build one JSON-serializable plan from each observation.

- `H0`: current-turn attacker and the ordered legal prerequisites needed to attack.
- `H1`: next-turn attacker after H0 survives or is KOed, using only known retained
  resources and one future manual attachment where a specific retained Metal exists.
- `H2`: pivot/promotion body used only when it preserves or restores the certificate.
- Ledger: hand/discard Metal, current/future manual attachment, Assemble Alloy,
  Turbo Flare options when actually exposed, retreat payment, evolution cards,
  recovery cards, Cape/Lab/Ice, and Bench slots.
- A resource can appear in at most one ledger reservation.
- H1 is unsafe if the visible payable response KOs it through Bench spread.
- Unsupported attack/effect text produces `UNKNOWN`, never a positive certificate.

Strict preference within governed contexts:

1. preserve an already legal current attack;
2. complete a current attack that is one governed prerequisite away;
3. certify H1 under public H0-survives/H0-KO branches;
4. preserve H1's last known prerequisite;
5. cross a public survival breakpoint that adds a certified attack;
6. reduce stranded Energy or exposed prize liability only as a tie-break;
7. otherwise preserve the exact legacy score and choice.

## Governed choices

- MAIN: Archaludon/Duraludon evolution, manual Metal attachment, retreat, governed
  survival plays, Night Stretcher/search only for a named certificate prerequisite,
  and attack/end only to preserve an existing certificate.
- Child contexts: Assemble Alloy/Turbo Flare target allocation, `ATTACH_FROM`,
  `ATTACH_TO`, own promotion/`TO_ACTIVE`, plan-required recovery/search selections,
  and healing target.
- Optional counts/subsets: choose only the amount needed by H0/H1; do not maximize
  independently.

All other choices retain legacy behavior.

## Mandatory point controls

1. Episode `86162213`: never claim Archaludon ex can damage Crustle `345` through
   Mysterious Rock Inn. The useful changed position is step `38`: a 70-HP,
   three-Energy non-ex Archaludon with legal Ice Cream facing visible Superb
   Scissors `120`; healing is eligible only because it crosses the survival/
   additional-attack breakpoint after public effects.
2. Episode `86161083`: a 30-HP Bench candidate is not H1-ready against visible
   Jetting Blow Bench spread `50`.
3. No hand Metal, discard Metal, manual attachment, Alloy attachment, evolution,
   or recovery card can certify two roles simultaneously.
4. Retreat and the actual promoted serial/location must share the same route.
5. Existing immediate attacks, Cornerstone/Mysterious Rock Inn blocks, Turbo Flare
   development, and successful Lucario/Dragapult sequences remain legal.
6. Every planner exception and outer agent exception uses deterministic legal
   indices and is traceable; no random fallback remains.

## Trace contract

Expose the latest decision trace in module state and optionally emit JSONL only
when an environment path is explicitly provided. Default Kaggle execution has no
trace I/O. Each planner activation/divergence records:

- `plan_hash`, turn, context, event;
- H0/H1/H2 identity, card/form, location, attack, and readiness;
- visible Active-response and Bench-spread envelope plus unknown flags;
- complete resource ledger/reservations;
- chosen option stable key, reason, and legacy versus planner score;
- `BUILD`, `CHOOSE`, `ABANDON`, or `FALLBACK`.

## Implementation verification before numerical evaluation

- byte equality for `deck.csv`, `cg/`, and requirements;
- source compiles and imports with the competition runtime;
- exact 60-card deck and no forbidden dependency/network/config access;
- deterministic repeated calls on identical observations;
- focused unit/scenario tests for all mandatory point controls;
- packaged two-seat smoke with zero action errors and max-step hits;
- a root diff review confirms excluded behavior was not intentionally changed.

No Kaggle package or submission is authorized by this specification.

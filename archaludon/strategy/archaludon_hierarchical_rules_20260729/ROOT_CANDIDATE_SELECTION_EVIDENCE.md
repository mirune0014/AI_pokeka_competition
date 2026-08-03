# Root candidate-selection evidence

## Fixed parent and live reference

- Direct parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`
- Parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Current live submission:
  `54927163`, COMPLETE, 184 public games, 93-91, latest saved score
  `825.8807714169828`.
- Root evidence:
  `evidence/live_54927163_refresh_20260729_0344/ROOT_VERIFIED_EVIDENCE.md`
  (`B783670F785675A86F9C1F063E6C5B2D7BB9D22705AFE528CDB2B478345BE868`).
- Episode CSV:
  `evidence/live_54927163_refresh_20260729_0344/submission_54927163_20260729_0344_episodes.csv`
  (`A94A0754A9D2F84B88DB7D64BC126D4E8FA2855CC0769E799A031F6D4702F64E`).

All new candidates must be direct children of this exact parent. The broad
Continuity2 planner is rejected and must not be reused or stacked. The already
evaluated direct-final-Prize Attack gate is safe and outcome-neutral, but it is
not a fresh strength hypothesis.

## Root-verified loss state

Episode `88457867`, target decision observation step `144`:

- Our remaining Prizes: `2`; opponent remaining Prizes: `1`.
- Our Active: Archaludon ex, card `190`, serial `70`, 300 HP remaining,
  three Metal Energy, and a legal 220-damage Metal Defender.
- Opponent Active: Dunsparce, card `305`, serial `16`, 70 HP, one Prize.
- Opponent Bench: exactly one visible attack-ready Alakazam, card `743`,
  serial `12`, 140 HP, one Psychic Energy, complete visible evolution line;
  the other three visible Bench Pokemon are zero-Energy Dunsparce.
- Boss's Orders was known in our hand after the immediately preceding Pokegear
  resolution.
- The exact parent assigned Boss `-500` because the Active was already KOable,
  used Explorer, then KOed the Dunsparce.
- The visible Alakazam promoted and its public Powerful Hand damage was enough
  to KO our two-Prize Active and end the game.
- Boss plus the already ready Metal Defender could instead switch and KO the
  unique visible ready Alakazam. This is a certified current-turn target
  conversion, not a claim that the hidden future game is guaranteed.

The root checked the cited raw replay directly. No opponent hidden hand,
opponent-action imitation, episode-ID exception, or future-action label is
required.

## Independent qualitative reports

- Alakazam audit:
  `ALAKAZAM_LOSS_AUDIT_REPORT.md`
  (`C5122CC809EBD2D1D40894C714090AFC84883A38CFBC802907CEF6AECC8557A2`).
  It inspected 24/24 specified losses and recommends a narrow endgame
  threat-removal Boss override at `88457867:144`.
- Adjacent audit:
  `ADJACENT_LOSS_AUDIT_REPORT.md`
  (`F65E9F8EB59EFA8C9ECB687710EFA957A8246275915F3C6F7D8958342CD1B272`).
  It inspected 24/24 specified losses and recommends a more general certified
  turn-plan reservation mechanism. Its concrete cases include missed
  last-prize recovery/Boss conversion, higher-prize Boss targets, spending the
  sole attack-completing Energy, and exposing the highest-investment attacker.

## Candidate alternatives for the first isolated implementation

1. **Narrow certified endgame response-threat gust**
   - Changes the exact Alakazam loss state.
   - Small callback surface.
   - Uses only public board, hand access, Prizes, HP, Energy, legal actions,
     current attack damage, and public Powerful Hand damage.
   - Must remain below an immediate terminal win and fail closed on ambiguous
     targets, multiple visible ready successors, incomplete attack legality, or
     an unkillable threat.

2. **Generic certified turn-plan reservation**
   - Addresses more loss mechanisms.
   - Has a much larger callback and sequencing surface and repeats the principal
     failure mode of the rejected broad planner if implemented all at once.
   - It should be decomposed into later one-mechanism candidates unless the
     strategy judge can define an equally narrow certificate.

Root preference is alternative 1 first. It has a causal live loss example,
implements the discussed look-ahead hierarchy, and minimizes regression risk.
The higher-prize Boss route, non-ex 120-damage breakpoint, sole-Energy
reservation, promotion/investment preservation, and Bench-damage protection
remain separate future hypotheses.

## Required decision

Select exactly one first rule hypothesis. Define an immutable, deterministic,
public-state contract including:

- precedence relative to current terminal wins and existing matchup rules;
- exact trigger and target certificate;
- multi-callback transaction stages, snapshot/rollback, and deterministic
  duplicate handling;
- positive state(s), fail-closed negatives, and engine completion requirements;
- forbidden generalizations;
- shadow and paired-evaluation evidence needed before a safe exploratory live
  submission.

The selected rule must be implemented alone, directly from the fixed parent.

# Root verification: Archaludon practice-first live probe

> Superseded after Kaggle validation: submission `55154818` exposed a missing
> deck-request guard in the final wrapper and is rejected.  See
> `autonomous_gold_20260715/live/55154818/VALIDATION_ERROR_ROOT_DIAGNOSIS.md`.
> The gameplay fixtures remain evidence for the two rules, but this exact
> source/archive is not deployable and must never be resubmitted.

Verified at `2026-08-01 14:40 JST` for a deliberately short, breakage-only
pre-submit gate.  Per the user's direction, this verification does not claim
local strength and does not include a broad replay shadow or matchup matrix.

## Frozen inputs

- Formal parent `main.py` SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Candidate `main.py` SHA-256:
  `5A0F4BE26EE0AB0B05200A4640301141F58CDDDAD1750D65EA2D1986CE52E7B5`
- Candidate `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Candidate `requirements.txt` SHA-256:
  `9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47`
- Clean archive SHA-256:
  `E8F735A7504F906D85B0D767FCC0E3C6AD7E31614786326DE620640A6F45B4E1`

The candidate begins with the exact 1,025,951-byte parent and appends one
final wrapper.  The parent prefix is byte-identical.  No episode, replay,
opponent, matchup, or seed identity occurs in the production suffix.

## Implemented live hypotheses

1. In an owner-free clear Main callback, take a unique exact payable attack
   immediately when it wins the game by taking the remaining Prizes or by
   knocking out the opponent's last Pokemon.
2. Otherwise, when the parent would play a Basic Duraludon before a unique
   exact nonterminal attack, attack instead only when every physical Basic
   projection preserves the same attack certificate and the play supplies no
   public role.  Public roles include board-out protection, an acceleration
   recipient, a visible evolution/attachment conversion, the first executable
   backup, a one-Prize wall, an improved exact reply, or a changed attack
   certificate.

The exact parent is called once.  Existing transaction owners dominate, and
ambiguous or incomplete public information returns the parent's action.

## Breakage-only gate

- Source compiled and imported with bytecode disabled.
- The last top-level function is callable `agent` at line 28,995.
- Deck is unchanged, exactly 60 cards, with one ACE SPEC.
- Candidate and extracted package contain zero cache artifacts.
- Focused replay checks passed:
  - three unique exact terminal-attack overrides;
  - three role-empty Duraludon-play suppressions;
  - three required holds covering board-out, Turbo Flare recipient, and
    visible evolution/attachment conversion.
- Four negative fixtures preserved the parent: live owner, multiple terminal
  semantics, unsupported oracle, and a nonterminal play with a public role.
- Duplicate/reordered UI rebinding and identical retry behavior passed.
- Candidate-tree smoke completed once in each seat with zero action errors
  and no max-step hit.
- The clean archive contains exactly 12 runtime files at its root.  Extracted
  `main.py`, `deck.csv`, and `requirements.txt` match the frozen hashes.
- Extracted-package smoke completed once in each seat against historical
  Silver: one win and one loss, zero action errors, and no max-step hit.

The initial seeded package-smoke invocation failed before game start because
the default local engine lacks `BattleStartSeeded`.  The same extracted
package was immediately rerun through the supported unseeded entrypoint and
passed in both seats.  This is an engine-capability mismatch, not a candidate
action failure.

## Live refresh

- Relevant mature Archaludon submission: Kaggle `55126164`, `COMPLETE`, CLI
  public score `814.6`.
- Episode refresh: 53 total rows, one validation and 52 public; public record
  `32-20`.  There are 38 episode IDs not present in the prior 15-row snapshot.
- Current episode CSV SHA-256:
  `6776E4FD550EBBB51D3BDB43B9F41BBF8F7D9B123C7BF463FCAF5DF781FF2B2A`
- Latest public episode: `89133150`, a loss, ending at
  `2026-07-31T11:21:37.114417600Z`, with exact updated score
  `814.6711577446199`.
- UTC quota date `2026-08-01`: `0/5` used, `5/5` remaining before write.

## Root decision

Original prewrite judgment: `PASS_FOR_EXPLORATORY_LIVE_PROBE`.

Post-validation controlling judgment: `REJECT__KAGGLE_DECK_REQUEST_ERROR`.

The pass means the artifact is legal, traceable, packaged, and has no observed
destructive runtime failure.  It does not mean the two rules improve local
win rate.  Their value and any interaction will be judged from live firings,
as explicitly requested by the user.

# Root verification specification: cumulative public hierarchy v1

Date: 2026-07-30 JST

This file freezes the Root-side destructive-safety and live-eligibility checks
before the cumulative source is accepted. It does not authorize a Kaggle
write.

## Immutable authorities

- Exact historical-Silver parent `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Exact deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Cumulative integration selection SHA-256:
  `2797D1C3B590E369FF3B38B20D2783ADAF1223FB0056759AAAEE69AFC453D942`.
- Cumulative user policy SHA-256:
  `F8E81D3872C809477068E7C9B476302BE20C14001127EA308C4C80B4CB95BB66`.
- Search-aware final admission judgment SHA-256:
  `FF9988CCD5352528160CB9A298EEB99B38501762C481D014ABD9CBE09734FF10`.
- Corrected isolated fixed-760 specification SHA-256:
  `83A26F42B264E63C8D58B923C7B50875F0C3EDD8B530360D12164A2988029BDC`.

The candidate must be a fresh direct child of the exact parent. It may port
certificates and transaction logic from the eight admitted component sources,
but it must not call or nest their agents.

## Frozen included-source ledger

| Rule | Source SHA-256 |
|---|---|
| H2 last-Prize Stretcher-Metal-Boss | `F45E0EB55D8DD7CC48ADD02EE342F2B0721CB0D9F88C1B97C1793A755C52B76F` |
| Search-aware Active terminal | `6B71FC078BC2F4B26B4D5509B49DAE960968D1EE71D0C805FD9F6DB9EAC0AC08` |
| H1 endgame Alakazam Boss | `CC7C2C53EC49BF4C690D6CD686DFB8BBA0041F1EA8F174C8B91135FBBA33DC49` |
| H5 v2 lethal Active/no ready successor | `E493C692198FE3699269F3CAFECD3010815DDE5EA2B3002321DDE109F9566798` |
| H4 v3 inherited-attack higher-Prize Boss KO | `36A7D19EEBB781C0406D2A99571B728DE841FBEAC7BC15C0AAF869BD0367DD45` |
| H6 v2 attack-completing Energy reservation | `C2B2E6E2A3170A1E90853CD0128075EA023831C17F2B7263744E371FC826E530` |
| Hero current-payable survival | `0EDE7D1B58AC31F6E3C4F10093D79940F08F058B7F63148CC48A884B25D4972B` |
| H3 v2 lone-Cinderace formation | `9D5A2A87770FE4CC2F77599E0FDF044ECC61C3F20BA335A02E1E2650BE5036B0` |

Any absent, ambiguous, or mismatched source aborts the build. Rejected sibling
versions must not appear in the candidate or proposal registry.

## Structural and action-validity gate

Root will independently verify:

1. Only `main.py` differs from the exact parent runtime.
2. Compile, clean import, deck request, loader-last and loader-only behavior.
3. Exactly 60 cards and one ACE SPEC; all non-`main.py` runtime members match
   the parent.
4. The exact parent action is computed once per novel public callback and is
   cached for duplicate retries.
5. All clear rules evaluate as pure proposals from one immutable public
   snapshot. Suppressed proposals do not mutate state.
6. At most one global transaction owner and at most one emitted action exist
   per callback.
7. Semantic rebinding is unique and legal. Ambiguous or missing binding,
   unregistered rank, unknown collision, stale stage, caught exception, and
   invalid owner certificate fail closed to the actual-state parent.
8. No opponent identity, episode, row, seed, fixed option serial, hidden card,
   or replay-future condition is read.
9. Zero invalid action, untraceable override, exception leak,
   nondeterminism, stale owner, two-owner state, action error, or max-step hit.

## Frozen precedence and collision gate

The total order is:

`engine/reset > parent direct terminal > active owner > H2 > search-aware >
H1 > H5v2 > H4v3 > H6v2 > Hero > H3v2 > exact parent`.

Root will verify all 28 unordered clear-state rule pairs with the higher-ranked
rule winning, plus an all-eight fixture with H2 winning. Every pair and the
all-eight fixture must cover:

- both logical seats;
- both directions of active ownership;
- competitor present and suppressed at arm;
- competitor newly appearing after arm;
- same-action and different-action collisions;
- equivalent duplicate and reordered legal options;
- semantic serial remapping;
- identical retry;
- turn change, result, new game, reset, and caught exception;
- pre-irreversible rollback and post-irreversible logical clear.

An existing valid owner retains attribution for the same semantic
continuation. A different newly eligible action after an irreversible owner
step clears every rule and delegates to the actual-state parent. Ownership may
never transfer halfway through a transaction.

## Component reproduction and shadow gate

The integrated runtime must reproduce every admitted component's:

- focused positive and miss/control routes;
- frozen negative and rejected-sibling regression states;
- duplicate, retry, rollback, turn-change, reset, and exception behavior;
- both-seat full transaction and immediate post-transaction guard.

The frozen replay union must contain all component source replays, all frozen
negatives and search misses, and every public replay known at execution time.
For every callback Root will verify:

1. cached parent action equals an independently loaded exact parent;
2. each proposal equals the isolated admitted component on its certificate;
3. an unopposed proposal yields the isolated component action;
4. collisions yield the frozen winner, owner, and suppression set;
5. final parent differences are a precedence-resolved subset of isolated
   component differences;
6. no interaction-created external difference exists.

Every first difference and every later owned callback must be represented by
raw telemetry without inference.

## Required callback telemetry

Every callback, including parent-equal, reset, and caught-exception callbacks,
must persist:

- snapshot/game/seat/turn/action context;
- exact cached parent semantic action;
- all rule proposals in precedence order;
- for every rule: source/contract hash, eligibility, rejection reason,
  certificate digest, rank, transaction ID, stage before/after, emitted,
  confirmed, retry status, suppressor, and rollback reason;
- active owner before/after, collision set, selected winner, suppression set,
  precedence reason, final action, and attribution owner;
- option-binding result, emergency/fail-closed reason, and state-clear result.

## Immutable fixed-760 gate

After the source and tests are frozen, the deterministic execution operator
must run the exact 200-row historical mirror plus seven-opponent 560-row
adjacent schedule in both seats with identical seeds and `max_steps=1000`.
The physical paired CSV must contain:

`panel,opponent,seat,seed,baseline_win,candidate_win,baseline_result,
candidate_result,baseline_steps,candidate_steps`.

Root will recompute the raw rows and require:

- 760 unique `(panel, opponent, seat, seed)` keys and exact schedule equality;
- parent `478/760`, historical `100/200`, adjacent `378/560`;
- parent seats `243/380` and `235/380`;
- cumulative totals no lower than those exact overall/panel/seat totals;
- zero parent-win/candidate-loss flip;
- no opponent/seat cell loss and no loss of the inherited `28/80`
  Kangaskhan/Crustle floor;
- zero missing starts, nonbinary result, duplicate mismatch, action error,
  exception, nondeterminism, stale state, or max-step hit;
- Root inspection of every trace difference and its rule/owner/precedence
  attribution.

Neutral output is destructive safety, not strength evidence.

## Package, pre-write, and live policy

If and only if every destructive gate passes, Root may build one clean
nonduplicate archive, extract it, and repeat both-seat component, collision,
search-hit/miss, duplicate/reset, and deterministic battle smoke. Package
membership and hashes must be frozen and caches/tests/generated artifacts must
be absent.

Immediately before any Kaggle write Root must refresh authenticated
submission capability, UTC quota, current status/score, exact public episode
set, source/archive hashes, and nonduplicate status. A weak or neutral
candidate may be used as one practical live experiment; a known-broken,
illegal, invalid, unpackaged, duplicate, or unattributable candidate may not.

Correct-seat shadow every genuinely new public replay. A rule-owned or
collision-owned certificate breach, invalid action, stale/two-owner state,
exception, package fault, or attributable regression triggers repair or
rollback. A parent-path loss is recorded separately and is not mixed into the
current implementation. A rule that does not fire remains installed and earns
neither positive nor negative strength credit.

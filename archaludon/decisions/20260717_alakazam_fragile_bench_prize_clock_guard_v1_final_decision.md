# Alakazam fragile-bench prize-clock guard v1 — final strategy judgment

Date: 2026-07-17 (JST)  
Role: `ptcg_sol_ultra_worker` final rule-level judge  
Scope: final accept/reject judgment only; no packaging, simulation, or Kaggle write was performed here.

## Authorities reviewed

- Strategy selection: `decisions/20260717_alakazam_second_distinct_slot_strategy_select.md`  
  SHA-256: `93A130DEE03EEF0F72E38D5F8CEA00A8B7A04B4546841B90D6FAA7842061CAA0`
- Implementation receipt: `implementation/alakazam_fragile_bench_prize_clock_guard_v1/IMPLEMENTATION_RECEIPT.md`  
  SHA-256: `DF4EEB39F967B9DB6849DF749321FB7B3E45970C5DCA797F24FFBD91AE7CAD34`
- Phase-0 execution manifest: `evaluation/alakazam_fragile_bench_prize_clock_guard_v1/PHASE0_EXECUTION_MANIFEST.md`  
  SHA-256: `5C76F29E317D7532B64D990B1201907782DD73AFE163E567E368B46C2BA6A869`
- Phase-0 repeat manifest: `evaluation/alakazam_fragile_bench_prize_clock_guard_v1/PHASE0_REPEAT_MANIFEST.md`  
  SHA-256: `D9FE89FE4481D6B41BA1A679F0EC615B1E98A6F0120EA0031E249880BB06247F`
- Phase-0 numerical audit: `evaluation/alakazam_fragile_bench_prize_clock_guard_v1/PHASE0_NUMERICAL_AUDIT.md`  
  SHA-256: `6AF9B155C1516A6D958D1269C76C68AF4430DC74C7DE440FC5E3FBFCA1CA6D86`
- Broad execution manifest: `evaluation/alakazam_fragile_bench_prize_clock_guard_v1/BROAD_EXECUTION_MANIFEST.md`  
  SHA-256: `C4EC60A1C584DD7431E376E88B33EC6DCC02BCF4D9B69D0AEC50DFB610997A98`
- Broad numerical audit: `evaluation/alakazam_fragile_bench_prize_clock_guard_v1/BROAD_NUMERICAL_AUDIT.md`  
  SHA-256: `B532657B64DE87E08A6C3536A97F24E63D3FA1CA9E484CB60A308FED4B426E71`
- Live first-three qualitative diagnosis for submission `54769337`: `live/54769337/monitor_20260717_0705/LIVE_FIRST3_QUALITATIVE_DIAGNOSIS.md`  
  SHA-256: `1CDA1E73932E6DF5C6A9C0167A5E72AB386DADDBE5D380753220D5F1B44CF2B5`

## Frozen hypothesis and isolation

The candidate changes only the decision to bench an additional Abra in a narrow public-state prize-clock situation. It suppresses every legal `PLAY Abra` action only when all of the following hold:

1. accepted Alakazam v3 would otherwise rank `PLAY Abra` first;
2. the own Active is Alakazam, has Psychic Energy, and has a legal Powerful Hand attack;
3. the opponent has at most three prizes remaining;
4. the opposing Active is a ready Starmie with Jetting Blow or Dragapult with Phantom Dive;
5. the new Abra would be exposed at full HP; and
6. the existing evolution state already dominates that Abra: either a Bench Alakazam exists, or a Bench Kadabra plus an Alakazam in hand exists.

When the predicate is true, all `PLAY Abra` scores are set to `-1` and the next-highest unchanged v3 action is selected. No deck change is part of the hypothesis.

The implementation receipt shows an exact isolated overlay: 103 insertions and zero deletions relative to the accepted v3 source; the runtime wrapper changes only its module name. Boundary tests, compile/import, legal 60-card deck, integrated both-seat smoke, and cache-zero checks all passed.

## Evidence judgment

The broad paired schedule contains 1,440 unique `(panel, opponent, seat, seed)` cells with exact baseline/candidate schedule equality. All candidate commands exited successfully, with zero retries, action errors, invalid/malformed/missing rows, or max-step hits. Candidate determinism was independently repeated for every one of the eight changed keys: 8/8 traces were byte-identical and 8/8 normalized summaries were identical.

The result ledger is:

- accepted v3 parent: 829/1,440 wins;
- candidate: 830/1,440 wins;
- discordant outcomes: one parent loss to candidate win, zero parent wins to candidate losses;
- seat totals: P0 415 to 415, P1 414 to 415;
- panel totals: known 211 to 211, fresh 201 to 201, newfresh 417 to 418;
- seven non-target opponents are exactly flat; Starmie improves 102 to 103;
- 1,432/1,440 complete traces are identical; all eight divergences are the frozen Starmie predicate keys;
- the sole result flip is `newfresh / starmie / p1 / seed 2026091719`, loss to win;
- all changed traces preserve an attack in the triggering turn and the intended follow-through line, while withholding the exposed Abra prize.

Every frozen absolute, seat, block, target-matchup, regression, semantic-isolation, and determinism gate passes. The protected Dragapult boundary remains identical because Battle Cage already blocks the relevant counters, which is the intended complement of the new rule rather than a missed target.

However, this is **not statistically persuasive evidence of a general win-rate gain**. There is only one discordant outcome, so the exact one-sided sign-test tail is `p = 0.5`. The observed +1 is compatible with a real narrow benefit, but it provides no useful lower confidence bound on broad strength. The acceptance below rests on exact isolation, direct prize-exchange logic, deterministic reproduction, and the absence of any observed regression across the frozen population—not on significance.

The first three public episodes of submission `54769337` do not strengthen or weaken this rule: the predicate would have fired in none of them. They instead expose a no-backup Basic opener failure and a separate Boss-induced Dudunsparce active-lock problem. At the time of that diagnosis, the displayed live score was supported by only two public scored games after validation. It is therefore not evidence that the live submission is recovering, mature, Bronze-level, or an adequate comparator.

## Final verdict

**ACCEPT** `alakazam_fragile_bench_prize_clock_guard_v1` as the next frozen operational Alakazam strength parent.

Also **AUTHORIZE exactly one clean package and one live Kaggle submission** of this candidate as the user-requested second, mechanism-distinct slot, subject to the root agent first refreshing Kaggle quota/status and independently confirming the submission-critical hashes and raw-row invariants required by `AGENTS.md`. This is a locally justified exploratory live probe: it is a narrowly dominant, deterministic safety rule with zero observed regressions. It must not be described as statistically proven improvement.

This verdict makes **no Bronze claim**, no leaderboard-rank claim, and no claim that the current live submission is recovering. A Bronze-stability claim requires substantially more live games and evidence across the actual public opponent mix.

## Exact package authorization

Build from a new clean staging directory. Package only the candidate source and deck below plus the byte-identical trusted support files from the accepted v3 package. Do not copy the candidate runtime wrapper into the archive; it is recorded to freeze local execution identity.

Candidate inputs:

| File | SHA-256 | Bytes | Package role |
|---|---|---:|---|
| candidate `main.py` | `60D61F4269566B5E922EA9044A32A0B3BA5BB769F8AE9959E86C0EDCB008A9C9` | 40,421 | archive root `main.py` |
| candidate `deck.csv` | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` | 262 | archive root `deck.csv` |
| candidate runtime `main.py` | `89BB1CB867104ECF1418009CAAE6F9BC548682CC33474FF33537DC3DCFE75B60` | 672 | local-runtime identity only; do not package |

Trusted support anchor: `packages/alakazam_run_away_draw_actual_capacity_v3_20260717/staging_clean`

| Archive member | SHA-256 | Bytes |
|---|---|---:|
| `requirements.txt` | `9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47` | 60 |
| `cg/__init__.py` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | 0 |
| `cg/api.py` | `593F1298E52A635F90F8F505A52113E9AF114F444C293404E37906F18EE06CED` | 26,933 |
| `cg/cg.dll` | `9EA2B0A751029689BFF3DDCCB5F29A98EDD46961DAD264490ED121EF704FB500` | 1,525,248 |
| `cg/game.py` | `3BD3D4F4A369A11E6D2F5DA9094CF15EBC410A2221835E6417B7CFF4883F1FC2` | 2,225 |
| `cg/libcg.dylib` | `77BB978A8129B094452679E0DAF0DA69593AFDA7331685F4642C0D4A94D39D82` | 1,245,544 |
| `cg/libcg.so` | `FFD89BF923525A3E6FEB5E6201E96A866C0F456895499ED5C4A566303CAAE67C` | 1,342,400 |
| `cg/libcg-arm64.so` | `030B4728CE9FB9E90B75830B7CF7236F71859732A05EC4A377078EEE0421BBE5` | 1,300,584 |
| `cg/sim.py` | `1555F57F5D22BF4C09D70E0E667A916E575E68C9DD1DE9EAD34BA5E7E4968655` | 2,273 |
| `cg/utils.py` | `60F29665CEE0A88525D6F0383BC45959A6262D16FE35EF380AECE1E0EA13C49B` | 1,970 |

Before submission, root must verify archive membership and hashes, compile/import, legal 60-card deck, packaged smoke in both seats, deterministic valid actions, no known P1/broken behavior, and frozen-file checks. The submission note should identify the hypothesis as fragile-Abra prize denial against ready Starmie/Dragapult and explicitly record that this is the mechanism-distinct exploratory slot.

## Exactly one next rule direction

After freezing this candidate, investigate one separate multi-step continuity rule prompted by the live mirror episode:

> When the opponent's immediately preceding public Boss's Orders forces Dudunsparce Active, a Bench Alakazam with Psychic Energy is ready, legal Active Run Away Draw is offered, the opposing Active is counter-susceptible, and current or capacity-certified post-draw Powerful Hand can take that Active prize, use Active Run Away Draw to vacate the Active slot, promote the ready Alakazam, and attack in the same turn, with an explicit deck-capacity and returned-stack certificate.

Do not combine this direction into the present package. It is the next isolated hypothesis because it addresses a live-observed, public-state active-lock line with a complete same-turn exit/promotion/attack plan; it remains unimplemented and unevaluated until separately frozen.

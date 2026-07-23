# Meta Deck Scouting 2026-07-03

Public top episode sample: `data/episodes/2026-07-02-sample`.

## Archetype Buckets

Extracted initial 60-card lists from 8 public top episodes:

- `marnie_grimmsnarl`: 9 decks
- `ogerpon_toolbox`: 3 decks
- `alakazam_psychic`: 2 decks
- `mega_lucario`: 1 deck
- `archaludon_metal`: 1 deck

Source outputs:

- `analysis_outputs/episode_decks_2026_07_02_sample/archetypes.csv`
- `analysis_outputs/episode_decks_2026_07_02_sample/decks.csv`
- `analysis_outputs/scouted_decks_2026_07_02/`

## Candidate Marnie Lists

Tested with the same rule agent:

- `submission_marnie_variant_tonakaiiii`: direct public top Marnie list.
- `submission_marnie_variant_debauchery`: direct public top Marnie list.
- `submission_marnie_variant_kazuki`: direct public top Marnie list.
- `submission_marnie_variant_hybrid2`: local legal hybrid based on public lists.

The first hybrid was invalid because it included both `Unfair Stamp` and `Hero's Cape`, which are both ACE SPEC cards.

## Current Local Signal

Most useful 10-game comparison:

- `analysis_outputs/matchup_matrix_marnie_hybrid2.csv`

Key results when Marnie is player A:

- `hybrid2` vs `archaludon`: 2-8
- `hybrid2` vs `great_tusk`: 7-3
- `hybrid2` vs `zoroark`: 8-2
- `tonakaiiii` vs `archaludon`: 3-7
- `tonakaiiii` vs `great_tusk`: 3-7
- `tonakaiiii` vs `zoroark`: 10-0

Key results when Marnie is player B:

- `archaludon` vs `hybrid2`: 10-0
- `great_tusk` vs `hybrid2`: 4-6
- `zoroark` vs `hybrid2`: 1-9
- `archaludon` vs `tonakaiiii`: 9-1
- `great_tusk` vs `tonakaiiii`: 7-3
- `zoroark` vs `tonakaiiii`: 0-10

Interpretation:

- Marnie is clearly stronger than the older Zoroark implementation in local tests.
- The hybrid improves Great Tusk/Crustle handling by cutting the Snorunt/Froslass line and adding more direct Grimmsnarl setup plus Boss/Cape.
- Archaludon remains the main bad matchup. It beats Marnie through high tempo energy acceleration, repeated 220 damage, and prize pressure on small support Pokemon.

## Rules Added From Strong-Player Thinking

- Do not overbench low-HP support before the matchup is known.
- Treat Crustle and Cornerstone Mask Ogerpon ex as blockers that Shadow Bullet cannot KO.
- Against Crustle, find Boss targets instead of repeatedly attacking into immunity.
- Against Land Collapse decks, start conserving the deck once Grimmsnarl is set up.
- Attach Handheld Fan to the active Pokemon that will actually be attacked.
- Prefer Boss when Shadow Bullet can take a prize-map KO.

## Next Iteration

Priority order:

1. Improve Archaludon matchup.
2. Add another public archetype implementation, likely Ogerpon toolbox or Alakazam Psychic.
3. Run a larger matrix after each change, then inspect `tools/summarize_local_traces.py` outputs for why games were lost.

## Iteration 2026-07-03: Playing Rules

Tested rule/deck variants:

- `oldpkg`: previously packaged tonakaiiii public-list candidate.
- `heal`: Munkidori healing and anti-liability rules.
- `current`: Froslass/Snorunt suppression vs Archaludon.
- `prizemap`: oldpkg plus Archaludon-specific Boss and bench-ping targets.
- `munki2`: prizemap with Munkidori reduced from 4 to 2.
- `munki3`: prizemap with Munkidori reduced from 4 to 3 and Boss increased from 2 to 3.

Rejected changes:

- Global going-first preference: did not improve enough and hurt Great Tusk.
- High-priority Unfair Stamp: helped Great Tusk but worsened Archaludon.
- Heavy Munkidori healing rules: did not reliably trigger and hurt hybrid lists.
- Fully suppressing Froslass/Snorunt after Archaludon is visible: did not improve overall, because many liabilities are already created before matchup markers are visible.
- Munkidori 2-copy deck: lost too much Great Tusk equity.

Current candidate:

- `submission_marnie_grimmsnarl_munki3boss.tar.gz`
- Deck change from public tonakaiiii list: `-1 Munkidori`, `+1 Boss's Orders`.
- Rule change from oldpkg: prioritize Duraludon, Cinderace, and Relicanth as Archaludon prize-map targets for Boss and Shadow Bullet bench damage.

Direct 20-game comparison against oldpkg over core local opponents:

- `munki3`: 64 / 120 wins
- `oldpkg`: 59 / 120 wins

Breakdown from `analysis_outputs/matchup_matrix_marnie_old_vs_munki3_20.csv`:

- `munki3` vs `archaludon`: 4-16; reverse direction 2-18.
- `munki3` vs `great_tusk`: 12-8; reverse direction 9-11.
- `munki3` vs `zoroark`: 18-2; reverse direction 19-1.

Package smoke test:

- Archive has no `__pycache__` or `.pyc`.
- Extracted package started locally with `action_errors: 0`.

## Iteration 2026-07-03: Public Top Mimic

Public replay deck buckets still point to `marnie_grimmsnarl` as the most common visible top archetype. The visible Marnie lists split into two useful families:

- `tonakaiiii`: Munkidori/Froslass/Fan pressure, good disruption tools, weak into Archaludon tempo.
- `kazuki0123` / `The Debauchery Tea Party`: Dunsparce/Dudunsparce draw engine, Hero's Cape, higher setup consistency and better Marnie mirrors.

Tested top-list mimics by keeping the improved rule engine and swapping deck shells:

- `submission_marnie_variant_debauchery_prizemap`: exact Debauchery public deck plus Archaludon prize-map rules.
- `submission_marnie_variant_kazuki_prizemap`: exact Kazuki public deck plus Archaludon prize-map rules.
- `submission_marnie_variant_kazuki_boss2`: Kazuki shell with `-2 Xerosic's Machinations`, `+2 Boss's Orders`.
- `submission_marnie_variant_kazuki_boss3_munki3`: Kazuki shell with one fewer Munkidori and three Boss.
- `submission_marnie_variant_kazuki_boss2_fan2`: KazukiBoss2 with `-1 Energy Search`, `-1 Energy Recycler`, `+2 Handheld Fan`.

Best current candidate:

- `submission_marnie_grimmsnarl_kazuki_boss2.tar.gz`
- Deck concept: copy the public Kazuki Marnie/Dunsparce engine, but restore 2 Boss so the agent can force prize-map KOs and play around Crustle-style blockers.
- Local package smoke test passed against Zoroark with `action_errors: 0`.

Key comparison outputs:

- `analysis_outputs/matchup_matrix_marnie_public_top_prizemap_20.csv`
- `analysis_outputs/matchup_matrix_marnie_kazuki_boss_variants_20.csv`
- `analysis_outputs/matchup_matrix_marnie_final_candidates_20.csv`
- `analysis_outputs/matchup_matrix_marnie_kazuki_fan2_20.csv`

Most recent final-candidate signal:

- Against core opponents in `matchup_matrix_marnie_kazuki_fan2_20.csv`:
  - `kazuki_boss2`: 63 / 120
  - `munki3`: 61 / 120
  - `grim4`: 59 / 120
  - `kazuki_fan2`: 59 / 120
- Against Marnie candidate variants in the same run:
  - `kazuki_fan2`: 71 / 120
  - `kazuki_boss2`: 64 / 120
  - `grim4`: 53 / 120
  - `munki3`: 52 / 120

Rejected or held changes:

- Exact Debauchery deck: strong Zoroark results but too weak into Archaludon/Great Tusk under current rules.
- Exact Kazuki deck: best Marnie-candidate mirror signal, but no Boss made Archaludon and Great Tusk worse.
- Boss3/Munkidori3 Kazuki: did not beat Boss2 overall.
- Fan2 Kazuki: better into Marnie candidates, but worse against the core local opponent set, especially Archaludon and Great Tusk.

Next tuning focus:

1. Improve Archaludon without sacrificing the Kazuki/Dunsparce mirror strength.
2. Build or import Ogerpon toolbox and Alakazam local agents so the core opponent set better matches the public top-deck buckets.
3. Inspect submitted battle logs after the next Kaggle run to decide whether the real queue is Marnie-heavy enough to favor `kazuki_fan2` over `kazuki_boss2`.

## Iteration 2026-07-03: Resource and Meta Target Rules

Current submitted-candidate directory:

- `submission_marnie_grimmsnarl`

Current package:

- `submission_marnie_grimmsnarl_kazuki_boss2_meta_targets.tar.gz`

Adopted small rule patch:

- Added Alakazam and Ogerpon-family target recognition for Boss and Shadow Bullet bench-damage selection.
- This is a low-surface patch: it should only matter when those public top archetypes are visible.
- Package smoke test passed with `action_errors: 0`.

Tested but not adopted:

- `submission_marnie_variant_kazuki_boss2_resource_rules`
  - Added stronger Energy Search / Energy Recycler usage, Trading Places scoring, and Morpeko damage handling.
  - One run improved core-opponent score (`65 / 120` vs current `51 / 120`), but a repeat was weaker and candidate mirrors worsened.
  - Kept as an experimental branch, not the submission candidate.
- `submission_marnie_variant_kazuki_boss2_energy_rules`
  - Isolated Energy Search / Energy Recycler and Trading Places only.
  - Mild and inconsistent improvement; not enough to adopt.
- `submission_marnie_variant_kazuki_boss2_grim4_cut_morpeko`
- `submission_marnie_variant_kazuki_boss2_grim4_cut_munki`
- `submission_marnie_variant_kazuki_boss2_grim4_cut_energysearch`
  - Tested 4 Grimmsnarl ex variants by cutting Morpeko, Munkidori, or Energy Search.
  - Did not beat current KazukiBoss2 on core opponents in the latest matrix.
- `submission_marnie_variant_kazuki_boss2_conserve_search`
  - Suppressed Poffin and Spikemuth search after Great Tusk/Crustle was known and Grimmsnarl was ready.
  - Hurt Great Tusk results; not adopted.

Relevant outputs:

- `analysis_outputs/matchup_matrix_marnie_resource_rules_20.csv`
- `analysis_outputs/matchup_matrix_marnie_energy_resource_20.csv`
- `analysis_outputs/matchup_matrix_marnie_kazuki_grim4_variants_20.csv`
- `analysis_outputs/matchup_matrix_marnie_conserve_search_20.csv`
- `analysis_outputs/matchup_matrix_marnie_meta_target_patch_10.csv`

Interpretation:

- Great Tusk losses are not fixed by simply conserving deck searches; we still need a better proactive prize plan or a more faithful Great Tusk/Ogerpon/Alakazam local meta set.
- Archaludon remains bad, but the tested 4-Grimmsnarl variants did not produce a reliable net improvement.
- The next useful work is building/importing Ogerpon and Alakazam local agents or using real submitted battle logs to identify which matchup is actually costing rating.

## Iteration 2026-07-03: Public Meta Opponents

Added simple local opponents from public replay deck lists:

- `meta_agents/alakazam_psychic_public_simple`
  - Source deck: `analysis_outputs/scouted_decks_2026_07_02/alakazam_psychic__capbloo__ep83190471_p1.csv`
  - Plays Abra/Kadabra/Alakazam, Dunsparce/Dudunsparce, Powerful Hand, Boss, and basic disruption.
- `meta_agents/ogerpon_toolbox_monnosuke_simple`
  - Source deck: `analysis_outputs/scouted_decks_2026_07_02/ogerpon_toolbox__monnosuke__ep83190476_p0.csv`
  - Plays Cornerstone Mask Ogerpon ex, Okidogi, Solrock/Lunatone, Binacle/Barbaracle, and Boss/draw supporters.

Both agents are simple local testing opponents, not exact recreations of the original competitors' policy logic.

Current package:

- `submission_marnie_grimmsnarl_kazuki_boss2_xerosic1.tar.gz`

Adopted deck change from the previous `kazuki_boss2_meta_targets` candidate:

- `-1 Energy Search`
- `+1 Xerosic's Machinations`

Why adopted:

- Xerosic1 was tested because Ogerpon and Alakazam build large hands, and the original public Kazuki list used Xerosic.
- In `analysis_outputs/matchup_matrix_marnie_xerosic_public_meta_20.csv`, Xerosic1 scored `100 / 200` against the expanded public-meta set, while current scored `91 / 200`.
- In the confirmation run `analysis_outputs/matchup_matrix_marnie_xerosic1_confirm_20.csv`, Xerosic1 remained slightly ahead: `97 / 200` vs current `95 / 200`.
- Candidate head-to-head in the confirmation run was neutral: `20 / 40` each.
- Package smoke test passed with `action_errors: 0`.

Rejected:

- `submission_marnie_variant_kazuki_boss2_ogerpon_morpeko`
  - Tried to answer Cornerstone Mask Ogerpon ex by promoting/charging Munkidori or Morpeko when Shadow Bullet was blocked.
  - Did not improve the Ogerpon matchup enough and hurt Archaludon/Great Tusk, so it was not adopted.
- `submission_marnie_variant_kazuki_boss2_xerosic2_cut_resources`
  - Two Xerosic copies by cutting both Energy Search and Energy Recycler.
  - Too inconsistent and worse than Xerosic1 overall.

Updated interpretation:

- Alakazam is manageable for Marnie when Boss and bench-ping target selection are working.
- The Ogerpon public-deck local opponent is a real problem because Cornerstone Mask Ogerpon ex can wall Shadow Bullet. Simple play rules are not enough; improvement likely needs deck construction changes, a stronger non-ability attacker plan, or real submission logs to decide whether this matchup is common enough to tech for.

## Iteration 2026-07-03: Deck-Power Pivot to Great Tusk

Reason for pivoting away from Marnie as the first candidate:

- Marnie can be tuned, but its main attack has structural dead spots into Cornerstone Mask Ogerpon ex and Crustle.
- In the latest combined local matrix from two 20-game sweeps per ordered matchup:
  - `great_tusk`: `338 / 480`
  - `archaludon`: `334 / 480`
  - `ogerpon`: `303 / 480`
  - `xrules` Marnie: `218 / 480`
  - current Xerosic1 Marnie: `214 / 480`
- This suggests the biggest available improvement is deck/archetype choice, not another small Marnie rule patch.

New first submission candidate:

- Directory: `submission_great_tusk_crustle`
- Archive: `submission_great_tusk_crustle_public.tar.gz`

Deck plan:

- Great Tusk + Explorer's Guidance is the primary deck-out plan.
- Crustle/Dwebble is the non-ex wall package.
- Boss's Orders, Xerosic's Machinations, Switch, Pokegear, Poke Pad, and Fighting Gong support the mill plan.
- Terrakion is the small emergency attacker package.

Packaging verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive contains no `__pycache__` or `.pyc`.
- Extracted package smoke test against Ogerpon completed with `action_errors: 0`.

Great Tusk targeted checks:

- `analysis_outputs/target_great_tusk_vs_zoroark_20_summary.jsonl`
  - Great Tusk as player 0 scored `11 / 20` against Zoroark in this targeted run.
- `analysis_outputs/target_great_tusk_vs_archaludon_20_summary.jsonl`
  - Great Tusk as player 0 scored `15 / 20` against Archaludon in this targeted run.

Tested but not adopted:

- `submission_great_tusk_crustle_wallsetup`
  - Raised initial Dwebble/Crustle setup priority.
  - Combined candidate-vs-meta score improved from original `282 / 400` to `296 / 400`.
  - However, direct Great Tusk mirror fell to `32 / 80`, so it is too risky if public Great Tusk-style decks are common.
- `submission_great_tusk_crustle_wallplay`
  - Only raised Dwebble priority after wall mode was known.
  - Scored `143 / 200` against the candidate meta set, below original Great Tusk at `147 / 200`.
  - Not adopted.

Current decision:

- First candidate for the next submission is `submission_great_tusk_crustle_public.tar.gz`.
- `submission_marnie_grimmsnarl_kazuki_boss2_xerosic1.tar.gz` remains a fallback and a useful comparison baseline, but it is no longer the highest local-score candidate.

## Iteration 2026-07-03: Great Tusk Play-Rule Tuning

Updated first submission candidate:

- Directory: `submission_great_tusk_crustle`
- Archive: `submission_great_tusk_crustle_setupaz.tar.gz`

Adopted rule patch:

- Suppress early Boss's Orders / Lisia's Appeal / Xerosic's Machinations when Great Tusk or Crustle is not yet ready to attack or wall.
- Keep high-priority Xerosic against Alakazam, because Powerful Hand scales with hand size.
- This targets losses where the agent spent early supporter turns on disruption while Land Collapse was not online.

Evidence:

- `analysis_outputs/matchup_matrix_great_tusk_setupaz_candidate_20.csv`
  - original Great Tusk: `139 / 200`
  - setupaz: `156 / 200`
- `analysis_outputs/matchup_matrix_great_tusk_setupaz_confirm2_20.csv`
  - original Great Tusk: `146 / 200`
  - setupaz: `150 / 200`
- Combined:
  - original Great Tusk: `285 / 400`
  - setupaz: `306 / 400`
- Main gains:
  - Marnie baseline: `47 / 80` -> `57 / 80`
  - Zoroark: `46 / 80` -> `56 / 80`
  - Alakazam: `73 / 80` -> `77 / 80`
- Main risk:
  - Great Tusk mirror fell to `34 / 80` in the two full setupaz confirmation runs.
  - Public top replay buckets currently looked more Marnie/Ogerpon/Alakazam-heavy than Great Tusk-heavy, so the net-meta improvement was prioritized.

Package verification:

- `submission_great_tusk_crustle_setupaz.tar.gz` contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke tests completed with `action_errors: 0` against Ogerpon and Zoroark.

Tested but not adopted:

- `submission_great_tusk_crustle_deckrace`
  - Tried to suppress Explorer/searches when own deck was behind in the deck race.
  - Scored `135 / 200`, below original Great Tusk at `137 / 200`.
- `submission_great_tusk_crustle_setupfirst`
  - Suppressed early disruption before the attack/wall plan was ready.
  - Slight aggregate gain: `282 / 400` vs original `280 / 400`, but Alakazam regressed.
- `submission_great_tusk_crustle_setupaz_mirror`
  - Restored disruption priority in Great Tusk mirrors.
  - Improved mirror compared with setupaz in some quick checks, but dropped Zoroark/Archaludon enough that full meta comparison favored setupaz: `155 / 240` vs mirror `151 / 240`.

Current decision:

- Use `submission_great_tusk_crustle_setupaz.tar.gz` as the next local-best submission candidate.
- Keep `submission_great_tusk_crustle_public.tar.gz` as the more mirror-safe fallback if the real queue proves Great Tusk-heavy.

## Iteration 2026-07-03: Post-setupaz Rejection Log

Additional tested but not adopted:

- `submission_great_tusk_crustle_setupaz_terminal`
  - Suppressed Explorer's Guidance when the opponent had 1 deck card left, expecting raw Land Collapse to finish without self-thinning.
  - Smoke result was poor, especially into setupaz mirror (`0 / 5` as player 0), so the rule was rejected.
- `submission_great_tusk_crustle_setupaz_ash1`
  - Deck change: `-1 Boss's Orders`, `+1 Sacred Ash`.
  - Directly held up against setupaz, but common-meta score dropped in the first matrix: setupaz `145 / 200`, ash1 `140 / 200`.
  - Boss count is too important to cut.
- `submission_great_tusk_crustle_setupaz_ash_lisia`
  - Deck change: `-1 Lisia's Appeal`, `+1 Sacred Ash`.
  - First run improved common-meta score (`145 / 200` vs setupaz `140 / 200`), but confirmation reversed enough that the combined common-meta score was effectively neutral/slightly worse: setupaz `279 / 400`, ash_lisia `278 / 400`.
  - Not adopted because the gain did not reproduce.
- `submission_great_tusk_crustle_setupaz_prizewall`
  - Forced Crustle wall mode when the opponent had 2 or fewer prize cards left.
  - Smoke result was poor into Zoroark and Marnie, so it was rejected before a full matrix.

Current decision remains:

- Keep `submission_great_tusk_crustle_setupaz.tar.gz` as the active next-submission candidate.

## Iteration 2026-07-03: Expanded Public-Top Sample and Targeted Setup Suppression

Expanded the public top replay sample from 8 to 19 episode files:

- Source: `data/episodes/2026-07-02-sample`
- Output: `analysis_outputs/episode_decks_2026_07_02_sample_19`

Updated archetype buckets from 38 extracted decks:

- `marnie_grimmsnarl`: 11
- `alakazam_psychic`: 10
- `archaludon_metal`: 6
- `ogerpon_toolbox`: 4
- `mega_lucario`: 2
- `hop_trevenant`: 2
- `unknown`: 2
- `starmie_froslass`: 1

Interpretation:

- The top visible public environment is still mostly high-power copied deck shells, not the local Zoroark shell.
- Great Tusk/Crustle was not visible in this expanded public-top sample, so mirror risk matters less than the Marnie/Alakazam/Archaludon/Ogerpon spread.
- Existing local mimics cover the four largest buckets: Marnie, Alakazam, Archaludon, and Ogerpon.

New tested variant:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19`
- Archive: `submission_great_tusk_crustle_targeted19.tar.gz`

Rule idea:

- Keep the setupaz principle only against setup-heavy / hand-heavy matchups: Marnie, Zoroark, and Alakazam.
- Restore the original higher disruption priority against other matchups, especially Archaludon and Ogerpon, where early Boss/Xerosic can buy tempo.
- This is a narrow policy change. The deck list is unchanged from Great Tusk/Crustle.

Primary 20-game confirmation against the four largest public-top buckets:

- Output: `analysis_outputs/matchup_matrix_great_tusk_public19_confirm20.csv`
- Public-top weighted score using bucket weights Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4:
  - `targeted19`: `0.770`
  - `public`: `0.758`
  - `setupaz`: `0.711`
- Unweighted results over those four buckets:
  - `targeted19`: `125 / 160`
  - `public`: `120 / 160`
  - `setupaz`: `113 / 160`

Sanity check:

- Output: `analysis_outputs/matchup_matrix_great_tusk_targeted19_sanity20.csv`
- Against Zoroark, `targeted19` matched setupaz: `23 / 40`.
- Against public Great Tusk, `targeted19` was close but slightly worse in the sanity run, so `submission_great_tusk_crustle_public.tar.gz` remains the mirror-safe fallback.

Package verification:

- `submission_great_tusk_crustle_targeted19.tar.gz` contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke tests completed with `action_errors: 0` against Ogerpon and Zoroark.

Current decision:

- Use `submission_great_tusk_crustle_targeted19.tar.gz` as the next local-best submission candidate if submitting into the currently observed public-top mix.
- Keep `submission_great_tusk_crustle_public.tar.gz` as the fallback if real battle history shows many Great Tusk/Crustle mirrors.

## Iteration 2026-07-03: Expanded Local Meta Opponents

Added two more simple local opponents from the expanded public-top sample:

- `meta_agents/mega_lucario_public_simple`
  - Source deck: Akira-Ninth public sample from episodes `83190473` / `83190499`.
  - Plan: Riolu -> Mega Lucario ex, attach Fighting energy, pressure with Aura Jab and Mega Brave.
- `meta_agents/hop_trevenant_public_simple`
  - Source deck: Yushin Ito public sample from episodes `83190487` / `83190493`.
  - Plan: Hop's Phantump -> Hop's Trevenant, Hop's Snorlax / Hop's Cramorant backup attackers, Hop engine search, Boss/Xerosic/Petrel disruption.

These are still local testing approximations, not exact recreations of the original competitors' policies.

Smoke checks:

- `analysis_outputs/smoke_mega_lucario_vs_targeted19_summary.jsonl`: `action_errors: 0`
- `analysis_outputs/smoke_hop_trevenant_vs_targeted19_summary.jsonl`: `action_errors: 0`

Expanded public-top weighted matrix:

- Output: `analysis_outputs/matchup_matrix_great_tusk_expanded19_candidates20.csv`
- Weights: Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Mega Lucario 2, Hop Trevenant 2.
- Weighted score:
  - `targeted19`: `0.761`
  - `setupaz`: `0.739`
  - `public`: `0.691`
- Unweighted score:
  - `targeted19`: `183 / 240`
  - `setupaz`: `174 / 240`
  - `public`: `170 / 240`

Breakdown for `targeted19`:

- Marnie: `23 / 40`
- Alakazam: `39 / 40`
- Archaludon: `29 / 40`
- Ogerpon: `32 / 40`
- Mega Lucario: `34 / 40`
- Hop Trevenant: `26 / 40`

Rejected follow-up:

- `submission_great_tusk_crustle_setupaz_targeted19_drawengine`
  - Added Dunsparce / Dudunsparce as early setup-deck markers so Marnie and Alakazam would be detected before their main evolution lines appeared.
  - Confirmation output: `analysis_outputs/matchup_matrix_great_tusk_drawengine_candidate20.csv`
  - It did not improve the weighted result: `drawengine` scored `0.738`, while `targeted19` scored `0.748` in the same comparison.
  - Rejected because it added recognition complexity without reproducible gain.
- `submission_great_tusk_crustle_setupaz_targeted19_darkaux`
  - Added Basic Dark Energy / Munkidori / Yveltal as auxiliary Marnie-Zoroark markers, while excluding visible Ogerpon-toolbox markers.
  - First comparison was only slightly ahead and traded Marnie/Ogerpon gains for Archaludon loss.
  - Confirmation output: `analysis_outputs/matchup_matrix_great_tusk_darkaux_confirm4_20.csv`
  - The gain did not reproduce: on the four largest buckets, `targeted19` scored `0.776` weighted while `darkaux` scored `0.740`.
  - Rejected because the extra heuristic was not stable enough to justify replacing the simpler targeted policy.

Current decision:

- Keep `submission_great_tusk_crustle_targeted19.tar.gz` as the active next-submission candidate.
- Keep `submission_great_tusk_crustle_setupaz.tar.gz` and `submission_great_tusk_crustle_public.tar.gz` as fallbacks for different real-queue mixes.

## Iteration 2026-07-03: Hop/Trevenant Trap Rule

Additional rejected follow-ups:

- `submission_great_tusk_crustle_setupaz_targeted19_endguard`
  - Idea: stop high-priority Explorer turns late against setup-suppression matchups when our deck is nearly empty.
  - It improved one focused Marnie run, but did not survive the broader check.
  - Confirmation output: `analysis_outputs/matchup_matrix_great_tusk_endguard_candidate20.csv`
  - Result: `targeted19` scored `0.781` weighted while `endguard` scored `0.722`.
  - Rejected because it delayed the main mill plan too often.
- `submission_great_tusk_crustle_setupaz_targeted19_hopfield`
  - Idea: keep a higher field floor and bench more Great Tusk / Dwebble bodies against Hop/Trevenant.
  - Focused Hop output: `analysis_outputs/focused_hopfield_vs_hop_30_summary.jsonl`
  - Result: `20 / 30`, the same as the focused `targeted19` baseline.
  - Rejected because extra board bodies did not solve the deck-race losses.

Adopted follow-up:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_hoptrap`
- Archive: `submission_great_tusk_crustle_hoptrap.tar.gz`

Rule idea:

- Detect Hop/Trevenant only from visible Hop Pokemon IDs: `304`, `311`, `878`, `879`.
- If Hop is visible, opponent deck is not already near empty, and our deck race is becoming poor, raise Boss's Orders / Lisia's Appeal priority when Explorer is not immediately available.
- Prefer trapping high-retreat or low-energy Hop targets, especially Hop's Snorlax, Hop's Phantump, inactive Hop's Cramorant, and under-energized Hop's Trevenant.
- Keep Explorer plus Great Tusk's Land Collapse as the primary line when it is available.

Focused Hop/Trevenant checks:

- Baseline `targeted19`: `20 / 30`.
- Initial `hoptrap` with broader Hop marker IDs: `25 / 30`.
- Final `hoptrap` with Pokemon-only marker IDs: `23 / 30`, `action_errors: 0`.
- Final focused output: `analysis_outputs/focused_hoptrap_pokemonids_vs_hop_30_summary.jsonl`

Expanded public-top weighted matrix:

- Output: `analysis_outputs/matchup_matrix_great_tusk_hoptrap_pokemonids_candidate20.csv`
- Weights: Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Mega Lucario 2, Hop Trevenant 2.
- Weighted score:
  - `hoptrap`: `0.757`
  - `targeted19`: `0.753`
- Unweighted score:
  - `hoptrap`: `193 / 240`
  - `targeted19`: `176 / 240`

Notes:

- The only intended behavioral change is the Hop-specific trap rule.
- The non-Hop local opponent deck lists do not contain the Hop Pokemon marker IDs, so non-Hop differences in short matrices are treated as random-run variance rather than a real policy change.
- Package smoke from the extracted archive completed with `action_errors: 0`:
  - Hop/Trevenant: `3 / 3`
  - Ogerpon: `2 / 3`

Current decision:

- Use `submission_great_tusk_crustle_hoptrap.tar.gz` as the active next-submission candidate.
- Keep `submission_great_tusk_crustle_targeted19.tar.gz` as the simpler fallback if real battle history shows Hop/Trevenant is rare.

## Iteration 2026-07-03: Marnie Race Rule Check

Observation from `hoptrap` focused Marnie traces:

- Focused output: `analysis_outputs/focused_hoptrap_vs_marnie_40_summary.jsonl`
- Result: `24 / 40`.
- Loss profile:
  - `16` losses total.
  - `13` losses ended with Crustle as our final active.
  - `13` losses were our deck-out before the opponent deck was empty.
  - Wins averaged `16.5` Great Tusk Land Collapse attacks; losses averaged only `2.81`.

Tested follow-up:

- `submission_great_tusk_crustle_setupaz_targeted19_marnierace`
  - Idea: against visible Marnie/Grimmsnarl, turn off Crustle wall mode once a Great Tusk can attack, or when the deck race is close.
  - Focused output: `analysis_outputs/focused_marnierace_vs_marnie_40_summary.jsonl`
  - Focused result improved to `27 / 40`, but the loss profile shifted toward board-loss games.
  - Expanded output: `analysis_outputs/matchup_matrix_great_tusk_marnierace_candidate20.csv`
  - Expanded weighted score did not improve: `hoptrap` scored `0.764`, `marnierace` scored `0.756`.
  - Additional Marnie-only 80-game check was tied: both `hoptrap` and `marnierace` scored `54 / 80`.
  - Rejected because the benefit was not stable enough under the weighted public-top mix.
- `submission_great_tusk_crustle_setupaz_targeted19_marnierace_field`
  - Idea: keep the `marnierace` Great Tusk push, but raise the Marnie field floor to 4 bodies to reduce board wipes.
  - Focused output: `analysis_outputs/focused_marnierace_field_vs_marnie_40_summary.jsonl`
  - Result dropped to `22 / 40`.
  - Rejected because the extra setup increased both board-loss and deck-race failures.

Current decision:

- Keep `submission_great_tusk_crustle_hoptrap.tar.gz` as the active next-submission candidate.
- Do not adopt the Marnie race variants unless real submission logs show Marnie is overwhelmingly common and Hop/Ogerpon are rare.

## Iteration 2026-07-03: Archaludon Rule Check

Observation from `hoptrap` focused Archaludon traces:

- Focused output: `analysis_outputs/focused_hoptrap_vs_archaludon_40_summary.jsonl`
- Result: `29 / 40`.
- Loss profile:
  - `11` losses total.
  - `10` losses ended with no active Pokemon on our side.
  - Only `1` loss was our deck-out.
  - Losses were mostly board-wipe games after Archaludon ex or Duraludon pressure.

Rejected follow-ups:

- `submission_great_tusk_crustle_setupaz_targeted19_archfield`
  - Idea: detect Archaludon and raise the field floor to 4 while boosting Poffin / Poké Pad / Ultra Ball / Great Tusk / Dwebble setup.
  - Focused output: `analysis_outputs/focused_archfield_vs_archaludon_40_summary.jsonl`
  - Result dropped to `18 / 40`.
  - Rejected because extra setup did not prevent board wipes and slowed the deck-race plan.
- `submission_great_tusk_crustle_setupaz_targeted19_archzone`
  - Idea: against visible Archaludon, make Colress's Tenacity for Neutralization Zone outrank Explorer's Guidance.
  - Focused output: `analysis_outputs/focused_archzone_vs_archaludon_40_summary.jsonl`
  - Result was `25 / 40`, below the `hoptrap` baseline.
  - Rejected because delaying Explorer reduced mill pressure and did not solve the Duraludon non-ex route.

Current decision:

- Keep `submission_great_tusk_crustle_hoptrap.tar.gz` as the active next-submission candidate.
- Do not add Archaludon-specific field or Zone overrides without real battle logs showing a different Archaludon policy than the local mimic.

## Iteration 2026-07-03: Ogerpon Trap Rule

Observation from `hoptrap` focused Ogerpon traces:

- Focused output: `analysis_outputs/focused_hoptrap_vs_ogerpon_40_summary.jsonl`
- Result: `34 / 40`.
- Loss profile:
  - `6` losses total.
  - All losses were board-loss games with no active Pokemon on our side.
  - The bad pattern was not deck-out. It was Okidogi / Cornerstone Mask Ogerpon ex converting attacks into a board wipe before Land Collapse finished the opponent's deck.

Rejected follow-up:

- `submission_great_tusk_crustle_setupaz_targeted19_ogerfield`
  - Idea: when Cornerstone Mask Ogerpon ex was active, raise the desired field floor and search more Great Tusk / Dwebble bodies.
  - Focused output: `analysis_outputs/focused_ogerfield_vs_ogerpon_40_summary.jsonl`
  - Result dropped to `32 / 40`.
  - Rejected because extra board building slowed the mill plan and did not reliably prevent board wipes.

Adopted follow-up:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_ogertrap`
- Archive: `submission_great_tusk_crustle_ogertrap.tar.gz`

Rule idea:

- Detect Ogerpon toolbox only from more specific visible IDs: Okidogi `116`, Cornerstone Mask Ogerpon ex `117`, Binacle `1051`, Barbaracle `1052`, and Team Rocket's Watchtower `1256`.
- Do not use generic Solrock/Lunatone IDs as archetype markers because IDs `675` / `676` overlap the local Mega Lucario marker set.
- If Ogerpon toolbox is visible, our deck race is becoming poor, and an Explorer + active Great Tusk turn is not immediately available, raise Boss's Orders / Lisia's Appeal.
- Prefer trapping low-energy Solrock, Lunatone, Binacle, Barbaracle, or Munkidori rather than pulling a charged Okidogi or Ogerpon ex.

Focused Ogerpon checks:

- Initial broad-marker `ogertrap`: `38 / 40`.
- Final narrow-marker `ogertrap`: `37 / 40`, `action_errors: 0`.
- Final focused output: `analysis_outputs/focused_ogertrap_narrow_vs_ogerpon_40_summary.jsonl`

Expanded public-top weighted matrix:

- Output: `analysis_outputs/matchup_matrix_great_tusk_ogertrap_candidate20.csv`
- Weights: Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Mega Lucario 2, Hop Trevenant 2.
- Weighted score:
  - `hoptrap`: `0.774`
  - `ogertrap`: `0.771`
- Unweighted score:
  - `hoptrap`: `195 / 240`
  - `ogertrap`: `199 / 240`
- Ogerpon-specific ordered-pair result:
  - `hoptrap`: `31 / 40`
  - `ogertrap`: `36 / 40`

Adoption rationale:

- The only intended behavioral change is gated by Ogerpon-specific IDs.
- The other local public-meta deck lists do not contain those IDs, so non-Ogerpon differences in the matrix are treated as random-run variance.
- The Ogerpon matchup improvement is large enough to adopt, while the policy remains unchanged against Marnie, Alakazam, Archaludon, Mega Lucario, and Hop/Trevenant unless an Ogerpon-specific card is visible.

Package verification:

- `submission_great_tusk_crustle_ogertrap.tar.gz` contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke tests completed with `action_errors: 0`:
  - Ogerpon toolbox: `3 / 3`
  - Hop/Trevenant: `2 / 3`

Current decision:

- Use `submission_great_tusk_crustle_ogertrap.tar.gz` as the active next-submission candidate.
- Keep `submission_great_tusk_crustle_hoptrap.tar.gz` as the simpler fallback if real battle history shows Ogerpon toolbox is rare and the visible field is strongly Marnie/Alakazam-heavy.

## Iteration 2026-07-03: Marnie Explorer Discipline

Observation from `ogertrap` focused Marnie traces:

- Focused output: `analysis_outputs/focused_ogertrap_vs_marnie_80_summary.jsonl`
- Result: `50 / 80`.
- Loss profile:
  - `30` losses total.
  - `22` losses ended with Crustle as our active Pokemon.
  - `19` losses ended with our deck at `0`.
  - Wins had many more effective Great Tusk / Land Collapse turns; losses were dominated by Crustle staying active while Explorer's Guidance and other supporters did not convert into mill pressure.

Rejected follow-ups:

- `submission_great_tusk_crustle_setupaz_targeted19_marnienowall`
  - Idea: turn off Crustle wall mode entirely against Marnie/Grimmsnarl.
  - Focused output: `analysis_outputs/focused_marnienowall_vs_marnie_80_summary.jsonl`
  - Result dropped to `44 / 80`.
  - Rejected because board-loss games increased too much.
- `submission_great_tusk_crustle_setupaz_targeted19_marnieswitch`
  - Idea: keep wall mode, but preserve Switch for returning from Crustle into a ready Great Tusk.
  - Focused output: `analysis_outputs/focused_marnieswitch_vs_marnie_80_summary.jsonl`
  - Result was `50 / 80`, tied with `ogertrap`.
  - Rejected because it did not improve the matchup.

Adopted follow-up:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_marnieexplorer`
- Archive: `submission_great_tusk_crustle_marnieexplorer.tar.gz`

Rule idea:

- Against visible Marnie/Grimmsnarl, only give Explorer's Guidance high priority when the active Great Tusk can immediately use Land Collapse.
- Suppress the lower-priority "setup Explorer" line in this matchup, because it spends supporter turns and deck resources without reliably producing a boosted mill attack.
- Keep the same Ogerpon trap and Hop/Trevenant trap rules from the previous candidate.

Focused Marnie check:

- `ogertrap`: `50 / 80`.
- `marnieexplorer`: `62 / 80`.
- Final focused output: `analysis_outputs/focused_marnieexplorer_vs_marnie_80_summary.jsonl`

Expanded public-top weighted matrix:

- Output: `analysis_outputs/matchup_matrix_great_tusk_marnieexplorer_candidate20.csv`
- Weights: Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Mega Lucario 2, Hop Trevenant 2.
- Weighted score:
  - `ogertrap`: `0.729`
  - `marnieexplorer`: `0.843`
- Unweighted score:
  - `ogertrap`: `181 / 240`
  - `marnieexplorer`: `207 / 240`
- Marnie ordered-pair result:
  - `ogertrap`: `19 / 40`
  - `marnieexplorer`: `30 / 40`

Adoption rationale:

- The only new rule is gated by Marnie-specific IDs: `646`, `647`, `648`, and `1259`.
- The non-Marnie local public-meta deck lists do not contain those IDs.
- The focused Marnie gain is large and also reproduced in the expanded weighted matrix.

Package verification:

- `submission_great_tusk_crustle_marnieexplorer.tar.gz` contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke tests completed with `action_errors: 0`:
  - Marnie/Grimmsnarl: `2 / 3`
  - Ogerpon toolbox: `0 / 3` in this tiny smoke sample
  - Hop/Trevenant: `2 / 3`

Current decision:

- Use `submission_great_tusk_crustle_marnieexplorer.tar.gz` as the active next-submission candidate.
- Keep `submission_great_tusk_crustle_ogertrap.tar.gz` as the fallback if real battle history contradicts the local Marnie signal.

## Iteration 2026-07-03: Starmie Discussion Check

Checked Kaggle Discussion `709263` in the browser. The visible post had no July update, but its public-history notes were still useful:

- `2026-06-17`: visible top 10 was described as `Crustle-style sustain / wall / deck-out pressure: 10 / 10`.
- `2026-06-18`: visible top 10 had shifted toward Iono lightning tempo, Psychic control, and Crustle hybrids.
- `2026-06-28`: visible top 10 was described as `Starmie-style water/fire/spread tempo: 5 / 10`, `Archaludon-style metal tempo: 3 / 10`, and `Psychic / Alakazam-style control: 2 / 10`.

This differs from the local `2026-07-02` replay sample, where Starmie appeared only once. I treated Starmie as a low-weight July bucket but kept a separate "Starmie-heavy" scenario because the public meta can move quickly.

Added local opponent:

- `meta_agents/starmie_public_simple`
  - Source deck: `83190495_p0` from `analysis_outputs/episode_decks_2026_07_02_sample_19/decks.csv`.
  - Plan: Cinderace setup / Turbo Flare acceleration into Mega Starmie ex, with Mega Signal, Salvatore, Hilda, Lillie, Boss, and Wally.
  - This is a simple local policy, not an exact recreation of the original player's agent.

Starmie matchup signal:

- Output: `analysis_outputs/matchup_matrix_candidates_vs_starmie20.csv`
- Great Tusk `marnieexplorer`: `10 / 40`
- Marnie/Grimmsnarl: `16 / 40`
- Archaludon: `36 / 40`
- Ogerpon toolbox: `5 / 40`

Candidate-choice implication:

- Output: `analysis_outputs/matchup_matrix_great_tusk_archaludon_starmie_meta10.csv`
- July-like weights, adding Starmie as a small bucket (`Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Lucario 2, Hop 2, Starmie 1`):
  - Great Tusk: weighted `0.779`
  - Archaludon: weighted `0.679`
- Discussion 2026-06-28 Starmie-heavy weights (`Starmie 5, Archaludon 3, Alakazam 2`):
  - Great Tusk: weighted `0.445`
  - Archaludon: weighted `0.780`

Interpretation:

- If the real queue resembles the `2026-07-02` sample, Great Tusk remains the better next submission.
- If submitted battle history shows a Starmie-heavy environment, the deck choice should pivot back to Archaludon rather than trying to patch Great Tusk with small rules.

Rejected follow-ups:

- `submission_great_tusk_crustle_setupaz_targeted19_marniemill`
  - Idea: against Marnie/Grimmsnarl, suppress `Giant Tusk` damage attacks and force Great Tusk toward `Land Collapse`.
  - Focused Marnie result improved only slightly: `64 / 80` vs current `62 / 80`.
  - Expanded output: `analysis_outputs/matchup_matrix_great_tusk_marniemill_candidate20.csv`
  - Expanded weighted result was worse: current `0.849`, `marniemill` `0.811`.
  - Rejected.
- `submission_great_tusk_crustle_setupaz_targeted19_starmiepolicy`
  - Idea: against Starmie, suppress setup Explorer, early disruption, and Colress-for-Zone so the deck rushes Land Collapse.
  - Focused Starmie result: `9 / 40`, below/near current `10 / 40`.
  - Rejected.
- `submission_great_tusk_crustle_setupaz_targeted19_starmiefield`
  - Idea: against Starmie, raise the field floor and search more Great Tusk / Dwebble bodies.
  - Focused Starmie result: `10 / 40`, no improvement over current.
  - Rejected.
- `submission_great_tusk_crustle_setupaz_targeted19_herocape`
  - Deck idea: replace `Neutralization Zone` with `Hero's Cape`.
  - Probe output: `analysis_outputs/matchup_matrix_great_tusk_herocape_probe20.csv`
  - Probe weighted result over Marnie/Starmie/Archaludon/Ogerpon weights was worse: current `0.749`, `herocape` `0.656`.
  - Rejected.

Current decision remains:

- Active next-submission candidate: `submission_great_tusk_crustle_marnieexplorer.tar.gz`
- Source directory: `submission_great_tusk_crustle_setupaz_targeted19_marnieexplorer`
- Main known risk: Starmie-heavy real queue. If that appears in submitted battle history, use `meta_agents/archaludon_public` / `submission_meta_archaludon.tar.gz` style as the next pivot baseline.

## Iteration 2026-07-03: Archaludon Starmie-Heavy Pivot

Reason:

- The public Discussion `709263` still points to a possible Starmie-heavy visible top environment (`Starmie 5 / Archaludon 3 / Alakazam 2` on 2026-06-28).
- Great Tusk is broad-meta strong, but local Starmie checks are structurally bad (`10 / 40` in the Starmie matrix).
- Base Archaludon beats Starmie, but it was too weak into Ogerpon because Cornerstone Mask Ogerpon ex blocks damage from Ability Pokemon.

Added candidate:

- Directory: `submission_archaludon_ogerboss`
- Archive: `submission_archaludon_ogerboss.tar.gz`
- Source rule variant: `meta_agents/archaludon_public_ogerblock`

Rule idea:

- Detect Ogerpon toolbox from specific IDs: Okidogi `116`, Cornerstone Mask Ogerpon ex `117`, Binacle `1051`, Barbaracle `1052`, and Team Rocket's Watchtower `1256`.
- Do not evolve Duraludon into Archaludon ex when Cornerstone Mask Ogerpon ex is visible and would wall Ability Pokemon attacks.
- Prefer Duraludon's `Raging Hammer` route into Cornerstone Mask Ogerpon ex.
- When Cornerstone is active and Archaludon can attack, raise Boss's Orders priority to pull non-Cornerstone bench targets.
- Target low-prize / non-blocking Ogerpon toolbox pieces first: Binacle, Munkidori, Solrock, Lunatone, Okidogi, then Barbaracle.

Ogerpon probe:

- Output: `analysis_outputs/matchup_matrix_archaludon_ogerboss_probe20.csv`
- Base Archaludon: `5 / 40`
- Ogerpon-rule Archaludon: `11 / 40`
- This is still unfavorable, but the improvement is large enough to keep as part of the Starmie-heavy pivot.

Expanded comparison:

- Output: `analysis_outputs/matchup_matrix_archaludon_ogerboss_expanded10.csv`
- July-like weights (`Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Mega Lucario 2, Hop 2, Starmie 1`):
  - Great Tusk `marnieexplorer`: `0.832`
  - Archaludon Ogerpon-rule: `0.821`
  - Base Archaludon: `0.653`
- Starmie-heavy weights (`Starmie 5, Archaludon 3, Alakazam 2`):
  - Archaludon Ogerpon-rule: `0.810`
  - Base Archaludon: `0.745`
  - Great Tusk `marnieexplorer`: `0.542`

Package verification:

- `submission_archaludon_ogerboss.tar.gz` contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke check completed with `action_errors: 0` against Ogerpon toolbox.
- Direct directory smoke check completed with `action_errors: 0` against Starmie.

Current decision:

- Keep `submission_great_tusk_crustle_marnieexplorer.tar.gz` as the broad-meta active candidate.
- Keep `submission_archaludon_ogerboss.tar.gz` as the Starmie-heavy pivot candidate.
- If real submission logs show repeated Starmie losses, switch deck family instead of trying more small Great Tusk patches.

## Iteration 2026-07-03: Archaludon Non-Ability Tech

Tested and rejected:

- Directory: `submission_archaludon_ogerboss_zacian2`
- Deck idea: `-2 Jumbo Ice Cream`, `+2 Zacian ex`.
- Rule idea: use no-Ability `Zacian ex` as a Metal attacker that can KO Cornerstone Mask Ogerpon ex with `Slashing Strike`.
- Probe output: `analysis_outputs/matchup_matrix_archaludon_zacian2_probe20.csv`.
- Result:
  - Ogerpon-rule Archaludon vs Ogerpon: `19 / 40` in that run.
  - Zacian2 vs Ogerpon: `15 / 40`.
  - Ogerpon-rule Archaludon vs Starmie: `35 / 40`.
  - Zacian2 vs Starmie: `33 / 40`.
- Rejected because adding Zacian did not improve the target matchup and slightly reduced the Starmie edge. The likely issue is that `Slashing Strike` cannot be chained on consecutive turns and the deck loses recovery slots.

Added candidate:

- Directory: `submission_archaludon_ogerboss_nonex2`
- Archive: `submission_archaludon_ogerboss_nonex2.tar.gz`
- Deck idea: `-2 Jumbo Ice Cream`, `+2 Archaludon` (single-prize, no Ability).
- Rule idea:
  - Against Ogerpon toolbox, search and keep single-prize `Archaludon`.
  - Evolve Duraludon into the non-Ability `Archaludon` when Cornerstone Mask Ogerpon ex is visible.
  - Use `Coated Attack` through Cornerstone Stance, while its next-turn effect blocks Basic Pokemon attack damage.

Focused probe:

- Output: `analysis_outputs/matchup_matrix_archaludon_nonex2_probe20.csv`
- Ogerpon-rule Archaludon vs Ogerpon: `9 / 40`
- Zacian2 vs Ogerpon: `22 / 40`
- Non-ex Archaludon2 vs Ogerpon: `27 / 40`
- Ogerpon-rule Archaludon vs Starmie: `34 / 40`
- Non-ex Archaludon2 vs Starmie: `34 / 40`

Expanded comparison:

- Output: `analysis_outputs/matchup_matrix_archaludon_nonex2_expanded10.csv`
- Public non-Arch buckets (`Marnie 11, Alakazam 10, Ogerpon 4, Mega Lucario 2, Hop 2, Starmie 1`):
  - Great Tusk `marnieexplorer`: `0.838`
  - Ogerpon-rule Archaludon: `0.812`
  - Non-ex Archaludon2: `0.880`
- With actual public Archaludon added at weight 6:
  - Great Tusk `marnieexplorer`: `0.815`
  - Non-ex Archaludon2: `0.800`
  - Ogerpon-rule Archaludon: `0.739`
- Starmie-heavy with actual Archaludon (`Starmie 5, Archaludon 3, Alakazam 2`):
  - Ogerpon-rule Archaludon: `0.718`
  - Non-ex Archaludon2: `0.650`
  - Great Tusk `marnieexplorer`: `0.565`

Package verification:

- `submission_archaludon_ogerboss_nonex2.tar.gz` contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke check completed with `action_errors: 0` against Ogerpon toolbox.

Current decision:

- Broad meta with Archaludon present: keep `submission_great_tusk_crustle_marnieexplorer.tar.gz` as the active candidate.
- Starmie-heavy plus Archaludon-heavy: keep `submission_archaludon_ogerboss.tar.gz` as the safer pivot.
- Non-Arch public buckets or Ogerpon/Starmie/Marnie-heavy logs: `submission_archaludon_ogerboss_nonex2.tar.gz` is now the strongest local candidate.

## Iteration 2026-07-03: Non-ex Archaludon Slot and Rule Refinement

Tested slot variants:

- `submission_archaludon_ogerboss_nonex1`
  - Deck idea: `-1 Jumbo Ice Cream`, `+1 Archaludon`.
- `submission_archaludon_ogerboss_nonex2_cutpad`
  - Deck idea: keep 4 `Jumbo Ice Cream`, add 2 non-ex `Archaludon`, cut 2 `Poke Pad`.

Slot probe:

- Output: `analysis_outputs/matchup_matrix_archaludon_nonex_slot_variants10.csv`
- Weighted over `Ogerpon 4, Starmie 1, Archaludon 6`:
  - Ogerpon-rule Archaludon: `0.577`
  - Non-ex Archaludon1: `0.527`
  - Non-ex Archaludon2: `0.600`
  - Non-ex Archaludon2 cut Poke Pad: `0.505`

Adopted rule refinement in `submission_archaludon_ogerboss_nonex2`:

- Outside the Ogerpon matchup, suppress evolving Duraludon into the single-prize `Archaludon`.
- Reason: the single-prize line is a targeted answer to Cornerstone Mask Ogerpon ex, not the default Archaludon game plan.

Focused confirmation:

- Output: `analysis_outputs/matchup_matrix_archaludon_nonex2_suppressed_probe20.csv`
- Ogerpon-rule Archaludon:
  - Ogerpon: `12 / 40`
  - Starmie: `35 / 40`
  - public Archaludon: `12 / 40`
- Non-ex Archaludon2 with suppressed non-Ogerpon evolution:
  - Ogerpon: `25 / 40`
  - Starmie: `37 / 40`
  - public Archaludon: `20 / 40`

Expanded confirmation:

- Output: `analysis_outputs/matchup_matrix_archaludon_nonex2_suppressed_expanded10.csv`
- July-like weights with actual public Archaludon (`Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Mega Lucario 2, Hop 2, Starmie 1`):
  - Great Tusk `marnieexplorer`: `0.842`
  - Ogerpon-rule Archaludon: `0.776`
  - Non-ex Archaludon2: `0.768`
- Starmie-heavy weights (`Starmie 5, Archaludon 3, Alakazam 2`):
  - Ogerpon-rule Archaludon: `0.755`
  - Non-ex Archaludon2: `0.745`
  - Great Tusk `marnieexplorer`: `0.535`
- Non-Arch public buckets:
  - Great Tusk `marnieexplorer`: `0.890`
  - Non-ex Archaludon2: `0.852`
  - Ogerpon-rule Archaludon: `0.782`

Updated package verification:

- Rebuilt `submission_archaludon_ogerboss_nonex2.tar.gz` after the suppressed-evolution rule patch.
- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke check completed with `action_errors: 0` against Starmie.

Current decision:

- Keep `submission_great_tusk_crustle_marnieexplorer.tar.gz` as the broad-meta active candidate.
- Keep `submission_archaludon_ogerboss.tar.gz` as the Starmie-heavy pivot while Archaludon remains common.
- Keep `submission_archaludon_ogerboss_nonex2.tar.gz` as the Ogerpon/Starmie tech pivot, but do not promote it above Great Tusk unless real logs show low Archaludon and many Ogerpon/Starmie-style games.

## Public Top-Side Check 2026-07-03

Source checked in browser:

- Kaggle leaderboard: `https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/leaderboard`
- Kaggle discussion meta note: `https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/709263`

Visible leaderboard top 10 at the time of the check:

| Rank | Team | Score | Last |
| --- | --- | ---: | --- |
| 1 | tonakaiiii | 1209.0 | 2d |
| 2 | Yushin Ito | 1191.7 | 8d |
| 3 | kazuki0123 | 1178.9 | 3d |
| 4 | yamy893 | 1150.4 | 6d |
| 5 | Akira-Ninth | 1139.7 | 7d |
| 6 | zoroark190 | 1137.9 | 3d |
| 7 | XP3RiX | 1136.4 | 11h |
| 8 | The Debauchery Tea Party | 1130.8 | 4h |
| 9 | btk15049 | 1128.4 | 5h |
| 10 | aidy | 1126.1 | 2d |

Public Game History was opened for the top agent. The visible panel showed recent games against `btk15049`, `XP3RiX`, `Yushin Ito`, `MtN`, and `yamy893`. The embedded viewer exposes replay controls and a simplified board, but the full card-state JSON is passed inside the iframe and the direct external visualizer open was blocked by the browser client. Therefore the concrete top decklist should not be treated as recovered from this check.

Discussion-based public archetype classification:

- 2026-06-28 public note: Starmie-style water/fire/spread tempo `5 / 10`, Archaludon-style metal tempo `3 / 10`, Psychic/Alakazam-style control `2 / 10`.
- Earlier public notes show the visible top 10 shifting quickly: Crustle sustain/wall, Hop mixed control, Mega Lucario fast tempo, Iono lightning, Psychic/Alakazam, and grass/fire/spread hybrids all appeared as meaningful axes at different points.

Local mimic buckets now used:

| Public bucket | Local mimic |
| --- | --- |
| Starmie-style water/fire/spread tempo | `meta_agents/starmie_public_simple` |
| Archaludon-style metal tempo | `meta_agents/archaludon_public` |
| Psychic/Alakazam-style control | `meta_agents/alakazam_psychic_public_simple` |
| Grass/fire/Ogerpon toolbox hybrid | `meta_agents/ogerpon_toolbox_monnosuke_simple` |
| Mega Lucario fast tempo regression | `meta_agents/mega_lucario_public_simple` |
| Hop/Trevenant mixed control regression | `meta_agents/hop_trevenant_public_simple` |
| Crustle sustain/deck-out family | Great Tusk/Crustle candidates and `meta_agents/great_tusk_crustle_public` |

Practical interpretation:

- Do not chase only the rank 1 visible deck. The public meta notes and current leaderboard games both indicate fast movement.
- The evaluation suite should keep at least three main axes: Starmie spread tempo, Archaludon metal tempo, and Alakazam/Psychic control.
- Secondary regression axes should remain Ogerpon toolbox, Lucario fast tempo, Hop mixed control, and Crustle-style long-game sustain.

## Iteration 2026-07-03: Great Tusk Starmie Board-Wipe Rule

Diagnosis run:

- Output: `analysis_outputs/focused_marnieexplorer_vs_starmie_60_summary.jsonl`
- Summary CSV: `analysis_outputs/summary_marnieexplorer_vs_starmie_60.csv`
- Great Tusk `marnieexplorer` vs Starmie: `11 / 60`.
- Loss profile:
  - `44 / 49` losses ended with no active Pokemon.
  - Only `5 / 49` losses were deck-out style.
  - Average `Land Collapse` count: wins `4.64`, losses `2.51`.

Interpretation:

- The Starmie loss is mostly board wipe / Great Tusk chain interruption, not only slow milling.
- The current Great Tusk plan should keep more Basic Great Tusk pressure against Starmie and avoid spending early turns/energy on Crustle wall setup in that matchup.

Implemented candidate:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush`
- Archive: `submission_great_tusk_crustle_starmierush.tar.gz`

Rule changes:

- Detect Starmie by visible card IDs `1030` and `1031`.
- Against Starmie:
  - Raise desired field floor to keep more bodies in play.
  - Disable Crustle wall mode.
  - Prioritize `Great Tusk`, `Ultra Ball`, `Fight Gong`, `Poke Pad`, and board rebuild lines that find or recover Great Tusk.
  - Lower Dwebble/Crustle evolution and energy priority.
  - Lower `Colress's Tenacity` / `Neutral Center` priority so Supporter turns are less likely to displace Explorer-style Great Tusk pressure.

Focused and expanded comparison:

- Focused probe: `analysis_outputs/matchup_matrix_great_tusk_starmierush_probe20.csv`
  - Current vs Starmie: `11 / 40`
  - Starmie-rush vs Starmie: `13 / 40`
- Expanded matrix: `analysis_outputs/matchup_matrix_great_tusk_starmierush_expanded10.csv`
  - July-like weights (`Marnie 11, Alakazam 10, Archaludon 6, Ogerpon 4, Lucario 2, Hop 2, Starmie 1`):
    - Current: `0.785`
    - Starmie-rush: `0.787`
  - Starmie-heavy weights (`Starmie 5, Archaludon 3, Alakazam 2`):
    - Current: `0.340`
    - Starmie-rush: `0.435`

Rejected variant:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush2`
- Idea: also treat Starmie as setup-suppression matchup.
- Probe: `analysis_outputs/matchup_matrix_great_tusk_starmierush2_probe20.csv`
- Result: worse than `starmierush` in the focused Starmie check, so rejected.

Rejected deck tech:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_stretcher`
- Deck idea: `-1 Xerosic's Machinations`, `+1 Night Stretcher`.
- Focused probe: `analysis_outputs/matchup_matrix_great_tusk_starmierush_stretcher_probe20.csv`
- Starmie totals from both seats:
  - Current: `12 / 40`
  - Starmie-rush: `7 / 40`
  - Stretcher: `6 / 40`
- Rejected because the 1-card recovery slot did not improve the focused Starmie run and cuts disruption.

Package verification:

- `submission_great_tusk_crustle_starmierush.tar.gz` archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive has no `__pycache__` or `.pyc`.
- Extracted package smoke check against Starmie: `analysis_outputs/pkgcheck_great_tusk_starmierush_vs_starmie_summary.jsonl`.
- Smoke result: 3 games started, `action_errors: 0`.

Updated current decision:

- Promote `submission_great_tusk_crustle_starmierush.tar.gz` over `submission_great_tusk_crustle_marnieexplorer.tar.gz` as the Great Tusk broad-meta candidate because the change is mostly Starmie-ID gated and the expanded July-like score stayed neutral.
- Keep `submission_archaludon_ogerboss.tar.gz` as the Starmie-heavy/Archaludon-heavy pivot.
- Keep `submission_archaludon_ogerboss_nonex2.tar.gz` as the Ogerpon/Starmie tech pivot, not as the broad default.

## Iteration 2026-07-03: Public Top Deck Buckets and Meta Suite

Browser check:

- Current visible leaderboard top names checked from the Kaggle page: `tonakaiiii`, `Yushin Ito`, `kazuki0123`, `yamy893`, `XP3RiX`, `zoroark190`, `The Debauchery Tea Party`, `btk15049`, `Akira-Ninth`, and `aidy`.
- The leaderboard itself does not expose full decklists.
- Public Discussion `709263` remains the cleanest public abstraction source. Its 2026-06-28 note classifies visible top 10 as:
  - Starmie-style water/fire/spread tempo: `5 / 10`
  - Archaludon-style metal tempo: `3 / 10`
  - Psychic/Alakazam-style control: `2 / 10`

Local public replay sample:

- Source: `analysis_outputs/episode_decks_2026_07_02_sample_19/decks.csv`
- Extracted rows by archetype:
  - `marnie_grimmsnarl`: `11`
  - `alakazam_psychic`: `10`
  - `archaludon_metal`: `6`
  - `ogerpon_toolbox`: `4`
  - `mega_lucario`: `2`
  - `hop_trevenant`: `2`
  - `starmie_froslass`: `1`
  - `unknown`: `2`

Working interpretation:

- Do not copy only one rank-1-looking deck. The public leaderboard and replay sample are inconsistent enough that the safer path is to keep several local mimic buckets.
- The current local mimic set is:
  - Marnie/Grimmsnarl: `submission_marnie_grimmsnarl`
  - Starmie water/fire/spread: `meta_agents/starmie_public_simple`
  - Archaludon metal tempo: `meta_agents/archaludon_public`
  - Psychic/Alakazam control: `meta_agents/alakazam_psychic_public_simple`
  - Ogerpon toolbox: `meta_agents/ogerpon_toolbox_monnosuke_simple`
  - Mega Lucario fast tempo: `meta_agents/mega_lucario_public_simple`
  - Hop/Trevenant mixed control: `meta_agents/hop_trevenant_public_simple`

Added tooling:

- New script: `tools/run_meta_suite.py`
- Purpose: run one or more candidate agents against the fixed public-meta mimic buckets from both seats and write:
  - ordered matchup rows to `analysis_outputs/meta_suite_results.csv`
  - bucket and weighted scenario summary to `analysis_outputs/meta_suite_summary.csv`
- Built-in weighted scenarios:
  - `public_sample_2026_07_02`: Marnie `11`, Alakazam `10`, Archaludon `6`, Ogerpon `4`, Lucario `2`, Hop `2`, Starmie `1`
  - `discussion_starmie_heavy_2026_06_28`: Starmie `5`, Archaludon `3`, Alakazam `2`
  - `equal_public_buckets`: equal weight over all local public buckets

Smoke run:

- Command output:
  - `analysis_outputs/meta_suite_smoke_results.csv`
  - `analysis_outputs/meta_suite_smoke_summary.csv`
- Candidates:
  - `great_tusk_starmierush`
  - `arch_ogerboss`
  - `arch_nonex2`
- Games: `1` per ordered seat, so this is a tool smoke only, not a decision-quality estimate.
- All rows completed with `errors: 0`.

Follow-up comparison run:

- Output:
  - `analysis_outputs/meta_suite_candidates_g5_results.csv`
  - `analysis_outputs/meta_suite_candidates_g5_summary.csv`
- Games: `5` per ordered seat, still noisy but useful as a quick candidate screen.
- Scenario scores:
  - `great_tusk_starmierush`: public sample `0.7694`, Starmie-heavy `0.5300`, equal buckets `0.7429`
  - `arch_ogerboss`: public sample `0.8583`, Starmie-heavy `0.8100`, equal buckets `0.8429`
  - `arch_nonex2`: public sample `0.7389`, Starmie-heavy `0.8500`, equal buckets `0.7857`
- Bucket highlights:
  - `great_tusk_starmierush`: Starmie `3 / 10`, Archaludon `6 / 10`, Marnie `6 / 10`
  - `arch_ogerboss`: Starmie `9 / 10`, Archaludon `6 / 10`, Marnie `10 / 10`
  - `arch_nonex2`: Starmie `10 / 10`, Ogerpon `6 / 10`, Marnie `6 / 10`
- Loss trace summaries:
  - `analysis_outputs/trace_summary_g5_great_tusk_vs_starmie.csv`
  - `analysis_outputs/trace_summary_g5_starmie_vs_great_tusk.csv`
  - `analysis_outputs/trace_summary_g5_great_tusk_vs_archaludon.csv`
  - `analysis_outputs/trace_summary_g5_archaludon_vs_great_tusk.csv`
- Interpretation:
  - Great Tusk still loses many Starmie/Archaludon games through board removal of Great Tusk/Dwebble/Crustle lines.
  - This reinforces the earlier conclusion: if real submission logs show Starmie/Archaludon-heavy opposition, pivoting deck family is more promising than another small Great Tusk patch.
  - Among the already packaged pivots, `submission_archaludon_ogerboss.tar.gz` is the more balanced next candidate; `submission_archaludon_ogerboss_nonex2.tar.gz` is more specialized for Ogerpon/Starmie and should not be the default while Archaludon mirrors remain common.

Rejected Great Tusk micro-variants after this check:

- `submission_great_tusk_crustle_setupaz_targeted19_archboard`
  - Idea: keep a larger board against Archaludon to reduce no-active losses.
  - A-seat focused Archaludon run improved (`44 / 60`), but broader two-seat checks were worse or neutral.
  - Expanded pair check before removing false Cinderace detection: `starmierush` July-like `0.817`, `archboard` `0.785`.
  - After narrowing Archaludon IDs, focused Starmie stayed equal and Archaludon was not reliably better (`starmierush` `28 / 40`, `archboard` `26 / 40`).
  - Rejected.
- `submission_great_tusk_crustle_setupaz_targeted19_starmietrap`
  - Idea: use Boss/Lisia more aggressively to trap unready Staryu/Cinderace instead of hitting powered Mega Starmie ex.
  - Focused Starmie probe improved in one sample (`starmierush` `6 / 40`, `starmietrap` `8 / 40`) but direct candidate games worsened (`starmierush` `23 / 40`, `starmietrap` `17 / 40`).
  - Rejected because it spends Supporter turns too aggressively.
- `submission_great_tusk_crustle_setupaz_targeted19_starmietarget`
  - Idea: keep only the Starmie target-selection part without increasing Boss/Lisia play/search priority.
  - Focused Starmie probe showed possible local upside (`target` `9 / 40` while `starmierush` was `3 / 40` in that noisy run), but expanded pair regression was clearly worse:
    - `starmierush`: July-like `0.875`, Starmie/Arch/Alakazam stress `0.440`, non-Arch `0.910`
    - `starmietarget`: July-like `0.711`, Starmie/Arch/Alakazam stress `0.340`, non-Arch `0.753`
  - Rejected.

Current decision:

- Keep `submission_great_tusk_crustle_starmierush.tar.gz` as the broad-meta package.
- Keep `submission_archaludon_ogerboss.tar.gz` as the Starmie-heavy/Archaludon-heavy pivot.
- Keep `submission_archaludon_ogerboss_nonex2.tar.gz` only as the Ogerpon/Starmie tech pivot.
- Next useful loop: use `tools/run_meta_suite.py` for every new candidate, then inspect the worst bucket traces with `tools/summarize_local_traces.py` before changing rules.

## Iteration 2026-07-03: Archaludon Pivot Rule Refinement

Main same-run comparison:

- Output:
  - `analysis_outputs/meta_suite_main_candidates_g10_results.csv`
  - `analysis_outputs/meta_suite_main_candidates_g10_summary.csv`
- Games: `10` per ordered seat against all local public buckets.

Summary:

| Candidate | Public sample | Starmie-heavy | Equal buckets |
| --- | ---: | ---: | ---: |
| `great_tusk_starmierush` | `0.7611` | `0.4350` | `0.6857` |
| `arch_ogerboss` | `0.7806` | `0.7500` | `0.7857` |
| `arch_nonex2` | `0.7722` | `0.7400` | `0.7786` |

Bucket results:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `great_tusk_starmierush` | `15 / 20` | `18 / 20` | `12 / 20` | `16 / 20` | `14 / 20` | `18 / 20` | `3 / 20` |
| `arch_ogerboss` | `17 / 20` | `19 / 20` | `9 / 20` | `9 / 20` | `20 / 20` | `19 / 20` | `17 / 20` |
| `arch_nonex2` | `17 / 20` | `18 / 20` | `9 / 20` | `11 / 20` | `18 / 20` | `19 / 20` | `17 / 20` |

Interpretation:

- `arch_ogerboss` is now the best balanced local candidate for public-sample and Starmie-heavy assumptions.
- `arch_nonex2` improves Ogerpon slightly, but loses enough elsewhere that it is still only a tech pivot.
- `great_tusk_starmierush` remains strong into Ogerpon and Alakazam, but the Starmie bucket is too bad for a Starmie-heavy queue.

Focused Ogerpon diagnosis for `arch_ogerboss`:

- Output:
  - `analysis_outputs/focused_arch_ogerboss_vs_ogerpon_40_summary.jsonl`
  - `analysis_outputs/focused_ogerpon_vs_arch_ogerboss_40_summary.jsonl`
- Results:
  - `arch_ogerboss` as player 0: `16 / 40`
  - `arch_ogerboss` as player 1: `10 / 40`
- Loss profile:
  - player 0 losses: `22 / 24` ended with no active Pokemon, `13 / 24` had an empty bench, `15 / 24` had opponent prizes at `0`.
  - player 1 losses: `23 / 30` ended with no active Pokemon, `9 / 30` had an empty bench, `18 / 30` had opponent prizes at `0`, `7 / 30` also had own deck at `0`.
- Interpretation:
  - Ogerpon losses are mostly board wipe / prize-race losses, not action errors.
  - The all-in Archaludon ex plan still struggles when Cornerstone Mask Ogerpon ex walls Ability Pokemon. The non-ex Archaludon deck tech helps this specific problem, but has not beaten `arch_ogerboss` on broad weights.

Rejected rule variants:

- `submission_archaludon_ogerboss_nonex2_mirrordiscard`
  - Idea: in `nonex2`, discard non-ex Archaludon more aggressively outside confirmed Ogerpon.
  - Probe output:
    - `analysis_outputs/meta_suite_arch_mirrordiscard_probe10_results.csv`
    - `analysis_outputs/meta_suite_arch_mirrordiscard_probe10_summary.csv`
  - Result: worse than `nonex2` on every checked scenario. Ogerpon fell from `16 / 20` to `12 / 20` in the probe.
  - Rejected. Likely reason: Ogerpon is not always recognized early enough, so the tech card can be discarded before Cornerstone is visible.
- `submission_archaludon_ogerboss_nonex2_mirrorboss`
  - Idea: add Archaludon mirror recognition and use Boss's Orders to KO higher-prize / loaded Duraludon / Relicanth targets even when the active can be KO'd.
  - Probe output:
    - `analysis_outputs/meta_suite_arch_mirrorboss_probe10_results.csv`
    - `analysis_outputs/meta_suite_arch_mirrorboss_probe10_summary.csv`
  - Result: mirror worsened from `13 / 20` to `9 / 20` in that probe. Marnie/Alakazam improved, but the intended target matchup got worse.
  - Rejected. Boss overuse appears to cost tempo in the mirror.
- `submission_archaludon_ogerboss_ogerboard`
  - Idea: without changing the deck, keep a larger Duraludon board against Ogerpon by raising Duraludon bench/search/Night Stretcher priority.
  - Probe output:
    - `analysis_outputs/meta_suite_arch_ogerboard_probe10_results.csv`
    - `analysis_outputs/meta_suite_arch_ogerboard_probe10_summary.csv`
  - Result: Ogerpon did not improve (`9 / 20` for both), and Alakazam dropped from `14 / 20` to `9 / 20`.
  - Rejected. Extra Duraludon board priority does not solve the Cornerstone wall and delays the normal Archaludon plan.

Current decision:

- Promote `submission_archaludon_ogerboss.tar.gz` as the current balanced pivot candidate when real logs show Starmie/Archaludon pressure.
- Keep `submission_great_tusk_crustle_starmierush.tar.gz` only if the observed queue is low-Starmie and high-Ogerpon/Alakazam.
- Keep `submission_archaludon_ogerboss_nonex2.tar.gz` as a specific Ogerpon/Starmie tech candidate, but not the default.

## Iteration 2026-07-03: Archaludon Ogerpon and Mirror Micro-Rules

Ogerpon log split:

- Source:
  - `analysis_outputs/focused_arch_ogerboss_vs_ogerpon_40_summary.jsonl`
  - `analysis_outputs/focused_ogerpon_vs_arch_ogerboss_40_summary.jsonl`
- Main signal:
  - Wins use more `Metal Defender` and `Jumbo Ice Cream`.
  - Losses are more often stuck on Duraludon attacks (`Hammer In` / `Raging Hammer`) and end with no active Pokemon.
  - Some losses also hit own deck `0`, but suppressing draw did not help because it delays the already fragile setup.

Rejected Ogerpon variants:

- `submission_archaludon_ogerboss_ogerexboss`
  - Idea: Cornerstone seen should not always forbid Archaludon ex evolution; allow ex evolution when the active is not Cornerstone or Boss can pull a non-Cornerstone target.
  - Probe:
    - `analysis_outputs/meta_suite_arch_ogerexboss_probe10_results.csv`
    - `analysis_outputs/meta_suite_arch_ogerexboss_probe10_summary.csv`
  - Result:
    - Ogerpon worsened from `7 / 20` to `6 / 20` in the probe.
    - Apparent Archaludon gain is treated as noise because the rule is Ogerpon-gated.
  - Rejected.
- `submission_archaludon_ogerboss_ogerresource`
  - Idea: against Ogerpon, conserve deck by skipping Explorer at deck `<= 16` and Lillie at deck `<= 12`.
  - Probe:
    - `analysis_outputs/meta_suite_arch_ogerresource_probe10_results.csv`
    - `analysis_outputs/meta_suite_arch_ogerresource_probe10_summary.csv`
  - Result:
    - Ogerpon worsened from `10 / 20` to `5 / 20`.
    - Public-sample proxy dropped from `0.7129` to `0.6371`.
  - Rejected. The draw suppression delays setup more than it prevents deck-out.

Archaludon mirror log split:

- Source:
  - `analysis_outputs/focused_arch_ogerboss_vs_archaludon_40_summary.jsonl`
  - `analysis_outputs/focused_archaludon_vs_arch_ogerboss_40_summary.jsonl`
- Main signal:
  - Wins use `Metal Defender` around `4.3` times/game and `Jumbo Ice Cream` around `1.75` to `2.15` times/game.
  - Losses use fewer `Metal Defender` attacks and end with no active Pokemon in nearly all losses.
  - The mirror appears to be decided by reaching stable Archaludon ex chains and healing, but simple Boss targeting and broad early healing did not improve it.

Rejected mirror variant:

- `submission_archaludon_ogerboss_mirrorheal`
  - Idea: explicitly detect Archaludon mirror and allow `Jumbo Ice Cream` at HP `<= 300` instead of the generic threshold.
  - Probe:
    - `analysis_outputs/meta_suite_arch_mirrorheal_probe10_results.csv`
    - `analysis_outputs/meta_suite_arch_mirrorheal_probe10_summary.csv`
  - Result:
    - Archaludon mirror was unchanged at `13 / 20`.
    - Ogerpon sample worsened from `9 / 20` to `6 / 20`.
    - Equal-bucket proxy was slightly lower.
  - Rejected.

Current decision after these micro-rules:

- No new rule promoted.
- Keep `submission_archaludon_ogerboss.tar.gz` as the current balanced Archaludon pivot.
- Keep `submission_archaludon_ogerboss_nonex2.tar.gz` only as a specialized Ogerpon/Starmie tech candidate.
- Ogerpon improvement likely needs a deck-construction change that does not reduce mirror/Alakazam/Marnie strength, not another small play-rule patch.

## Iteration 2026-07-03: Non-Ex Archaludon Slot Tests

Visible public deck buckets used for local imitation:

- Kaggle discussion `709263`, 2026-06-28 public top-10 note:
  - Starmie-style water/fire/spread tempo: `5 / 10`
  - Archaludon-style metal tempo: `3 / 10`
  - Psychic / Alakazam-style control: `2 / 10`
- Local visible replay sample `analysis_outputs/episode_decks_2026_07_02_sample_19/decks.csv`:
  - Marnie / Grimmsnarl: `11`
  - Alakazam psychic: `10`
  - Archaludon metal: `6`
  - Ogerpon toolbox: `4`
  - Mega Lucario: `2`
  - Hop / Trevenant: `2`
  - Starmie: `1`

Reason for the slot test:

- Public Archaludon lists include both pure Archaludon ex builds and builds with non-ex Archaludon `840`.
- The non-ex card directly addresses Cornerstone Mask Ogerpon ex because Coated Attack is not an Ability attack and then prevents Basic Pokemon attack damage.
- Earlier `nonex2` cut two Jumbo Ice Cream and helped Ogerpon only modestly while losing too much overall.

Rejected `840` slot variants:

- `submission_archaludon_ogerboss_nonex2_cutgear`
  - `+2` non-ex Archaludon, `-2` Pokegear, keep four Jumbo Ice Cream.
  - Probe: Ogerpon improved to `12 / 20`, but Marnie fell to `15 / 20` and Archaludon mirror to `8 / 20`.
  - Rejected.
- `submission_archaludon_ogerboss_nonex1_cutgear`
  - `+1` non-ex Archaludon, `-1` Pokegear.
  - Probe: Ogerpon only `10 / 20`, public-sample proxy lower than `ogerboss`.
  - Rejected.
- `submission_archaludon_ogerboss_nonex1_cutfml`
  - `+1` non-ex Archaludon, `-1` Full Metal Lab.
  - Probe improved Ogerpon but hurt Alakazam and mirror.
  - Rejected.
- `submission_archaludon_ogerboss_nonex1_cutlillie`
  - `+1` non-ex Archaludon, `-1` Lillie.
  - Probe was lower than the two-card `840` plans.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutlillie`
  - `+2` non-ex Archaludon, `-2` Lillie.
  - Probe hurt Marnie, mirror, and Ogerpon.
  - Rejected.
- Mixed one-card cuts:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1gear`
  - `submission_archaludon_ogerboss_nonex2_cut1fml1ice`
  - `submission_archaludon_ogerboss_nonex2_cut1fml1pad`
  - Short probe had some promising Ogerpon samples, but full seven-bucket evaluation stayed below `nonex2_cutfml`.
  - Rejected.

Promoted candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cutfml`
- Archive: `submission_archaludon_ogerboss_nonex2_cutfml.tar.gz`
- Deck change from `ogerboss`:
  - `+2` Archaludon `840`
  - `-2` Full Metal Lab `1244`
  - Keep Pokegear `1122` x4 and Jumbo Ice Cream `1147` x4.

Confirmation run:

- Output:
  - `analysis_outputs/meta_suite_arch_nonex2_cutfml_confirm_g20_results.csv`
  - `analysis_outputs/meta_suite_arch_nonex2_cutfml_confirm_g20_summary.csv`
- Games: `20` per seat and matchup, so each bucket is `40` games.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `ogerboss` | `0.7681` | `0.7450` | `0.7607` |
| `nonex2_cutfml` | `0.7826` | `0.7475` | `0.8071` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ogerboss` | `36 / 40` | `33 / 40` | `24 / 40` | `14 / 40` | `38 / 40` | `36 / 40` | `32 / 40` |
| `nonex2_cutfml` | `38 / 40` | `30 / 40` | `18 / 40` | `29 / 40` | `36 / 40` | `38 / 40` | `37 / 40` |

Interpretation:

- The candidate gives up Alakazam and especially Archaludon mirror percentage.
- It gains a lot into Ogerpon and also improves Starmie, Marnie, and Hop in this confirmation run.
- The public-sample gain is modest but positive; the equal-bucket gain is clear.
- This should replace `submission_archaludon_ogerboss.tar.gz` only when the expected queue contains meaningful Ogerpon/Starmie pressure or when avoiding deck-power losses into Ogerpon is prioritized.

Packaging check:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- No `__pycache__` or `.pyc` entries found.
- Smoke test from an extracted archive vs `meta_agents/starmie_public_simple` ran `2` games with `0` action errors.

## Iteration 2026-07-03: Playing Rule Follow-Up

Tooling update:

- `tools/run_meta_suite.py` now supports `--game-out`.
- This writes per-game rows with winner, result, trace path, final active, prize counts, turn, and steps.
- Purpose: make loss audits less ambiguous than the aggregate matchup CSV.
- Smoke output:
  - `analysis_outputs/meta_suite_gameout_smoke_results.csv`
  - `analysis_outputs/meta_suite_gameout_smoke_summary.csv`
  - `analysis_outputs/meta_suite_gameout_smoke_games.csv`

Loss audit:

- Re-ran `nonex2_cutfml` against Archaludon and Alakazam with per-game output:
  - `analysis_outputs/meta_suite_nonex2_lossaudit_results.csv`
  - `analysis_outputs/meta_suite_nonex2_lossaudit_summary.csv`
  - `analysis_outputs/meta_suite_nonex2_lossaudit_games.csv`
- Signal:
  - Some early losses end with no active Pokemon.
  - Many Archaludon losses still end with the opponent on Archaludon ex and our side unable to keep the attacker chain going.
  - This suggested testing setup-bench and mirror-specific rules.

Rejected rule variants:

- `submission_archaludon_ogerboss_nonex2_cutfml_backup`
  - Idea: outside Ogerpon, allow non-ex Archaludon as a backup attacker when no Archaludon ex is available.
  - Probe:
    - `analysis_outputs/meta_suite_nonex_backup_probe10_summary.csv`
  - Result: Alakazam improved in one short probe, but Marnie/Starmie and mirror were worse.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutfml_alakbackup`
  - Idea: restrict backup non-ex Archaludon to Alakazam only.
  - Probe:
    - `analysis_outputs/meta_suite_alakbackup_probe10_summary.csv`
  - Result: did not hold up; Alakazam/Starmie fell in the probe.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutfml_alakboss`
  - Idea: vs Alakazam, Boss a killable higher-prize bench target instead of taking a 1-prize active KO.
  - Confirmation:
    - `analysis_outputs/meta_suite_alakboss_alakazam_g30_summary.csv`
  - Result: Alakazam fell from `48 / 60` to `44 / 60`.
  - Rejected. Active pressure is more important than opportunistic Fezandipiti ex prize targeting in this local mimic.
- `submission_archaludon_ogerboss_nonex2_cutfml_archdetect`
  - Idea: explicitly classify opposing Duraludon / Archaludon ex / non-ex Archaludon as `archaludon`.
  - Result: useful as a rule substrate but not promoted by itself. With no strong mirror rule attached, longer mirror check was slightly lower than baseline.
- `submission_archaludon_ogerboss_nonex2_cutfml_archheal260`
- `submission_archaludon_ogerboss_nonex2_cutfml_archheal300`
  - Idea: with actual Archaludon detection, use Jumbo Ice Cream earlier in the mirror.
  - Confirmation:
    - `analysis_outputs/meta_suite_archheal_archaludon_g30_summary.csv`
  - Result: `archheal300` fell to `30 / 60` against Archaludon while baseline was `33 / 60`.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutfml_archchain`
  - Idea: in the mirror, search for a third Duraludon / Archaludon ex line to avoid attacker-chain collapse.
  - Probe:
    - `analysis_outputs/meta_suite_archchain_probe10_summary.csv`
  - Result: mirror and overall score fell. Extra searching costs too much tempo.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutfml_archboss2prize`
  - Idea: conservative mirror Boss rule: only pull a killable benched Archaludon ex if active KO is lower prize.
  - Probe:
    - `analysis_outputs/meta_suite_archboss2_probe10_summary.csv`
  - Result: worsened mirror and overall.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutfml_keepfml`
  - Idea: with only two Full Metal Lab, keep/take FML in the mirror.
  - Probe:
    - `analysis_outputs/meta_suite_keepfml_probe10_summary.csv`
  - Result: worsened. Protecting FML costs more setup tempo than it saves.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cutfml_setupbench`
  - Idea: setup-bench Duraludon and Relicanth to reduce no-active losses.
  - Confirmation:
    - `analysis_outputs/meta_suite_setupbench_confirm_g20_summary.csv`
  - Result:
    - Mirror improved from `21 / 40` to `25 / 40`.
    - Hop and Starmie improved slightly.
    - Alakazam fell from `36 / 40` to `30 / 40`.
    - Public-sample proxy fell from `0.8201` to `0.7896`.
  - Rejected as default; possible tech only if queue is very low-Alakazam.
- `submission_archaludon_ogerboss_nonex2_cutfml_setupbench1`
  - Idea: setup-bench only one Duraludon, not Relicanth or multiple Duraludon.
  - Probe:
    - `analysis_outputs/meta_suite_setupbench1_g10_summary.csv`
  - Result: Ogerpon improved, but Marnie/Alakazam/Starmie were lower.
  - Rejected.

Current decision:

- Keep `submission_archaludon_ogerboss_nonex2_cutfml.tar.gz` as the current best Ogerpon/Starmie-aware submission candidate.
- Do not promote any playing-rule variant from this pass.
- The most promising future axis is not another micro-rule in the mirror; it is likely either:
  - a cleaner deck slot that restores mirror/Alakazam power without losing Ogerpon, or
  - richer opponent-specific public-meta mimics, so the local target is less noisy.

## Iteration 2026-07-03: FML3 Slot Search

Reason:

- `nonex2_cutfml` gained Ogerpon/Starmie by adding two non-ex Archaludon `840`, but it cut Full Metal Lab from `4` to `2`.
- Mirror and some Alakazam losses suggested that restoring one Full Metal Lab might recover durability.
- The goal was to find a slot that restores FML to `3` without losing too much Ogerpon/Starmie power.

Rejected FML3 variants:

- `submission_archaludon_ogerboss_nonex2_cut1fml1boss`
  - Deck: FML `3`, Boss `3`, non-ex Archaludon `2`.
  - Short probe was strong, but confirmation fell behind baseline:
    - `analysis_outputs/meta_suite_cut1fml1boss_confirm_g20_summary.csv`
    - Public sample: `0.7750` vs `0.8111` for `nonex2_cutfml`
    - Alakazam: `28 / 40` vs `37 / 40`
    - Ogerpon: `26 / 40` vs `28 / 40`
  - Rejected. Boss x4 appears important for Alakazam/Ogerpon lines.
- `submission_archaludon_ogerboss_nonex2_cut1fml1explorer`
  - Deck: FML `3`, Explorer `3`.
  - Probe:
    - `analysis_outputs/meta_suite_fml3_slots_g10_summary.csv`
  - Result: Starmie/Hop fell enough that it was not confirmed further.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cut1fml1stretcher`
  - Deck: FML `3`, Night Stretcher `2`.
  - Probe:
    - `analysis_outputs/meta_suite_fml3_slots_g10_summary.csv`
  - Result: playable but below the best candidate.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cut1fml1energy`
  - Deck: FML `3`, Metal Energy `10`.
  - Probe:
    - `analysis_outputs/meta_suite_fml3_boss4_slots_g10_summary.csv`
  - Result: mirror improved but Starmie/Hop fell.
  - Rejected.
- `submission_archaludon_ogerboss_nonex2_cut1fml1ultraball`
  - Deck: FML `3`, Ultra Ball `3`.
  - Probe:
    - `analysis_outputs/meta_suite_fml3_boss4_slots_g10_summary.csv`
  - Result: low public-sample proxy and weaker setup consistency.
  - Rejected.

Promoted candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`
- Deck change from `nonex2_cutfml`:
  - `+1` Full Metal Lab `1244`
  - `-1` Relicanth `57`
  - Keeps Boss's Orders `1182` x4, non-ex Archaludon `840` x2, Jumbo Ice Cream `1147` x4.

Confirmation:

- Output:
  - `analysis_outputs/meta_suite_cut1fml1relicanth_confirm_g20_results.csv`
  - `analysis_outputs/meta_suite_cut1fml1relicanth_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_cut1fml1relicanth_confirm_g20_games.csv`
- Games: `20` per seat and matchup, so each bucket is `40` games.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `nonex2_cutfml` | `0.7361` | `0.7800` | `0.7929` |
| `cut1fml1relicanth` | `0.7764` | `0.7875` | `0.8143` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `nonex2_cutfml` | `30 / 40` | `31 / 40` | `20 / 40` | `28 / 40` | `36 / 40` | `39 / 40` | `38 / 40` |
| `cut1fml1relicanth` | `32 / 40` | `33 / 40` | `23 / 40` | `27 / 40` | `37 / 40` | `40 / 40` | `36 / 40` |

Interpretation:

- Relicanth-free FML3 improves Marnie, Alakazam, mirror, Lucario, and Hop in this run.
- It gives up a little Ogerpon and Starmie, but not enough to lose the weighted scenarios.
- The local result suggests the single Relicanth was less valuable than the third Full Metal Lab when non-ex Archaludon and Boss x4 are already present.

Packaging check:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- No `__pycache__` or `.pyc` entries found.
- Smoke test from extracted archive vs `meta_agents/archaludon_public` ran `2` games with `0` action errors.

Current decision:

- New preferred local candidate: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.
- Keep previous `submission_archaludon_ogerboss_nonex2_cutfml.tar.gz` as the Ogerpon/Starmie slightly-heavier alternative.

## Iteration 2026-07-03: FML4 Check After Relicanth Cut

Reason:

- After `cut1fml1relicanth` promoted FML from `2` to `3`, the next question was whether full FML `4` could work if Relicanth was already cut.
- Tested three FML4 variants:
  - `submission_archaludon_ogerboss_nonex2_fml4_cutrelicboss`
  - `submission_archaludon_ogerboss_nonex2_fml4_cutrelicenergy`
  - `submission_archaludon_ogerboss_nonex2_fml4_cutrelicultra`

Probe:

- Output:
  - `analysis_outputs/meta_suite_fml4_cutrelic_g10_results.csv`
  - `analysis_outputs/meta_suite_fml4_cutrelic_g10_summary.csv`
  - `analysis_outputs/meta_suite_fml4_cutrelic_g10_games.csv`

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `cut1fml1relicanth` | `0.8319` | `0.8150` | `0.8500` |
| `fml4_cutrelicboss` | `0.8153` | `0.7800` | `0.8429` |
| `fml4_cutrelicenergy` | `0.8042` | `0.8050` | `0.8143` |
| `fml4_cutrelicultra` | `0.7528` | `0.7750` | `0.7929` |

Decision:

- No FML4 variant promoted.
- Full Metal Lab `4` appears to cost too much when it forces a cut to Boss, Energy, or Ultra Ball.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz` as the current preferred local candidate.

## Iteration 2026-07-03: Top Mimic Classification and Non-Ex Count Check

Current public-top deck classification:

- Kaggle Discussion `709263` still provides the cleanest abstract public-top split:
  - `Starmie-style water/fire/spread tempo`: `5 / 10`
  - `Archaludon-style metal tempo`: `3 / 10`
  - `Psychic / Alakazam-style control`: `2 / 10`
- The local public replay sample `analysis_outputs/episode_decks_2026_07_02_sample_19/decks.csv` remains broader:
  - `marnie_grimmsnarl`: `11`
  - `alakazam_psychic`: `10`
  - `archaludon_metal`: `6`
  - `ogerpon_toolbox`: `4`
  - `mega_lucario`: `2`
  - `hop_trevenant`: `2`
  - `starmie_froslass`: `1`
  - `unknown`: `2`

Local mimic set:

| Public bucket | Local mimic |
| --- | --- |
| Marnie / Grimmsnarl | `submission_marnie_grimmsnarl` |
| Starmie water/fire/spread | `meta_agents/starmie_public_simple` |
| Archaludon metal tempo | `meta_agents/archaludon_public` |
| Alakazam psychic control | `meta_agents/alakazam_psychic_public_simple` |
| Ogerpon toolbox / grass-fire hybrid | `meta_agents/ogerpon_toolbox_monnosuke_simple` |
| Mega Lucario fast tempo | `meta_agents/mega_lucario_public_simple` |
| Hop / Trevenant mixed control | `meta_agents/hop_trevenant_public_simple` |

Comparison against copied/mimicked public-top buckets:

- Output:
  - `analysis_outputs/meta_suite_top_mimic_compare_g10_results.csv`
  - `analysis_outputs/meta_suite_top_mimic_compare_g10_summary.csv`
  - `analysis_outputs/meta_suite_top_mimic_compare_g10_games.csv`
- Games: `10` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `great_tusk_starmierush` | `0.8347` | `0.4000` | `0.7286` |
| `arch_ogerboss` | `0.7472` | `0.7250` | `0.7571` |
| `arch_nonex2_cutfml` | `0.7306` | `0.7100` | `0.7429` |
| `arch_fml3_relicless` | `0.7986` | `0.7400` | `0.7929` |

Interpretation:

- Great Tusk can still score well on the July replay-style broad mix, but it went `0 / 20` into the Starmie mimic in this run. That makes it too risky if the real queue resembles the Starmie-heavy Discussion snapshot.
- `arch_fml3_relicless` is the best balanced Archaludon-family candidate in this comparison. It keeps strong Starmie/Alakazam/Marnie performance while retaining a workable Ogerpon line.
- The working approach should remain multi-bucket imitation, not one rank-1 deck overfitting.

Archetype-as-candidate screen:

- Output:
  - `analysis_outputs/meta_suite_archetype_mimic_screen_unique_g5_results.csv`
  - `analysis_outputs/meta_suite_archetype_mimic_screen_unique_g5_summary.csv`
  - `analysis_outputs/meta_suite_archetype_mimic_screen_unique_g5_games.csv`
- Note: candidate names were prefixed with `cand_*` to avoid collisions with built-in opponent bucket names.
- Games: `5` per seat and matchup. This is only a screen, but it checks whether simply switching to another copied public archetype is promising.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `current_arch` | `0.8556` | `0.8400` | `0.8571` |
| `cand_great_tusk` | `0.8306` | `0.3800` | `0.7000` |
| `cand_starmie` | `0.5278` | `0.4200` | `0.6286` |
| `cand_ogerpon` | `0.5250` | `0.3600` | `0.4143` |
| `cand_marnie` | `0.4861` | `0.2500` | `0.5143` |
| `cand_alakazam` | `0.4361` | `0.4400` | `0.4429` |
| `cand_lucario` | `0.4250` | `0.4400` | `0.4429` |
| `cand_hop` | `0.3722` | `0.2400` | `0.3857` |

Interpretation:

- The simple copied public archetype mimics are useful as opponents, but they are not better submission candidates as-is.
- `cand_great_tusk` remains competitive in the July replay-style public sample, but its Starmie bucket was `0 / 10`, so it is not safe under the Discussion Starmie-heavy read.
- `current_arch` is currently the best deck-power choice across both observed meta assumptions.

Rejected rule-only Ogerpon tech:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_keep840`
  - Idea: preserve the first non-ex Archaludon `840` before Ogerpon is known, because Ogerpon may be recognized too late and the tech can be discarded early.
  - Probe output: `analysis_outputs/meta_suite_keep840_probe15_summary.csv`
  - Result:
    - Ogerpon improved from `16 / 30` to `22 / 30`.
    - Alakazam fell from `28 / 30` to `24 / 30`.
    - Archaludon mirror fell from `17 / 30` to `14 / 30`.
    - Public-sample proxy fell from `0.7524` to `0.6984`.
  - Decision: reject as default. Keep only as an Ogerpon-heavy tech idea.

Rejected non-ex Archaludon count variants:

- `submission_archaludon_ogerboss_nonex3_fml3_cutgear`
  - Deck: `840` x3, `Pokegear 3.0` x3.
  - Full seven-bucket output: `analysis_outputs/meta_suite_nonex3_cutgear_full_g10_summary.csv`
  - In one focused four-bucket probe it improved Archaludon/Starmie-heavy.
  - The first full seven-bucket run still trailed current on public-sample and equal-bucket scores:
    - public sample `0.7569` vs current `0.7806`
    - Starmie-heavy `0.7850` vs current `0.7400`
    - equal buckets `0.8071` vs current `0.8143`
  - A later three-candidate full run did not reproduce the Starmie-heavy gain:
    - `nonex3_cutgear` Starmie-heavy `0.6900` vs current `0.8000`
  - Decision: not default; possible Archaludon/Starmie-heavy branch only if real logs support it.
- `submission_archaludon_ogerboss_nonex3_fml3_cutlillie`
  - Deck: `840` x3, `Lillie's Determination` x3.
  - Output: `analysis_outputs/meta_suite_nonex3_slot_full_g10_summary.csv`
  - Result was below current on all weighted scenarios:
    - public sample `0.7597` vs current `0.8153`
    - Starmie-heavy `0.7050` vs current `0.8000`
    - equal buckets `0.7714` vs current `0.8357`
  - Decision: reject.

Current decision:

- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz` as the preferred local candidate.
- Keep `submission_great_tusk_crustle_starmierush.tar.gz` as a broad July-replay-style alternative only when Starmie is rare.
- Keep `submission_archaludon_ogerboss_nonex3_fml3_cutgear` as an un-packaged branch candidate only if submitted logs show an unusually Archaludon/Starmie-heavy queue and Alakazam/Ogerpon are less frequent.

## Iteration 2026-07-03: Live Top Check and Rule Adoption Filter

Reason:

- The current leaderboard had moved since the 2026-06-28 public meta note, so deck power should not be judged from a single old snapshot.
- The goal is to copy broad top-deck families, not exact private lists, then convert stronger play principles into local rules and keep only changes that survive repeated local match logs.

Live leaderboard check:

- Browser-visible top 10 at the time of check:
  - `1` `tonakaiiii` `1257.1`
  - `2` `kazuki0123` `1196.8`
  - `3` `Yushin Ito` `1165.1`
  - `4` `yamy893` `1159.6`
  - `5` `chamboabi` `1145.3`
  - `6` `XP3RiX` `1128.6`
  - `7` `aidy` `1117.1`
  - `8` `btk15049` `1109.9`
  - `9` `pokeka_ryo` `1106.9`
  - `10` `MtN` `1104.0`
- The leaderboard table itself exposes scores and public episode links, but not deck lists. The directly usable public source for archetype labels remains the Discussion meta note plus public Game History inspection.
- The current working imitation buckets remain:
  - Starmie-style water/fire/spread tempo
  - Archaludon-style metal tempo
  - Psychic / Alakazam-style control
  - Hop mixed control
  - Marnie / Grimmsnarl control
  - Ogerpon toolbox
  - Mega Lucario fast tempo

Deck-power decision:

- Do not switch submissions to a copied Starmie, Marnie, Hop, Alakazam, Ogerpon, or Lucario mimic as-is. The local archetype-as-candidate screen showed those copies are useful opponents, but weak submissions without deeper play rules.
- Keep Archaludon as the current main deck-power base because it is the best balanced candidate across public-sample, Starmie-heavy, and equal-bucket assumptions.
- Treat Great Tusk as a low-Starmie branch only; it still collapses into the Starmie mimic.

Rejected Ogerpon-specific rule branches:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_ogerdogi_target`
  - Idea: prioritize Boss targets on Ogerpon boards toward Okidogi.
  - Probe improved some Ogerpon games but weakened public/equal scores.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_ogerdogi_boss`
  - Idea: explicitly Boss and KO benched Okidogi before it snowballs.
  - Confirmation output: `analysis_outputs/meta_suite_ogerdogi_boss_confirm_g20_summary.csv`
  - Result:
    - current public sample `0.8118`, Starmie-heavy `0.7700`, equal `0.8250`
    - dogi_boss public sample `0.7847`, Starmie-heavy `0.7925`, equal `0.8107`
  - Decision: not default. It helps only if the real queue is heavily Archaludon/Starmie and not Ogerpon/Alakazam weighted.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_ogerline3`
  - Idea: keep a third Duraludon/Archaludon body against Ogerpon to reduce no-active losses.
  - Probe output: `analysis_outputs/meta_suite_ogerline3_probe15_summary.csv`
  - Result:
    - current public proxy `0.6683`, Starmie-heavy `0.7167`, equal `0.6917`, Ogerpon `21 / 30`
    - ogerline3 public proxy `0.6190`, Starmie-heavy `0.7000`, equal `0.6500`, Ogerpon `18 / 30`
  - Decision: reject. The extra setup rule slowed tempo more than it fixed board wipe losses.

Full Metal Lab / non-ex Archaludon rule check:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_fmlnonex`
  - Idea: allow Full Metal Lab when non-ex Archaludon is active, not only Duraludon or Archaludon ex.
  - Confirmation output: `analysis_outputs/meta_suite_fmlnonex_confirm_g20_summary.csv`
  - Result:

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `current` | `0.7924` | `0.7850` | `0.8179` |
| `fmlnonex` | `0.7813` | `0.8125` | `0.8071` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `current` | `34 / 40` | `32 / 40` | `25 / 40` | `28 / 40` | `36 / 40` | `39 / 40` | `35 / 40` |
| `fmlnonex` | `34 / 40` | `35 / 40` | `20 / 40` | `23 / 40` | `36 / 40` | `39 / 40` | `39 / 40` |

Decision:

- Reject `fmlnonex` as the default. The Starmie gain is real in this run, but it loses too much in mirror and Ogerpon, and trails current in public-sample and equal-bucket scores.
- Also reject `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_fmlcape_nonex` from the prior probe because adding Hero's Cape targeting for non-ex Archaludon was worse than both current and `fmlnonex`.

Current working loop:

- Classify the top environment into broad deck families first.
- Build local mimics for each family.
- Convert strong-player thinking into rules only when it has a concrete board trigger:
  - prize race math
  - target priority
  - resource preservation
  - setup versus tempo tradeoff
  - special-case matchup detection
- Keep a rule only after it improves the weighted scenarios, not only one favorite matchup.

Current decision:

- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz` as the preferred submission archive.
- No new archive is promoted from this iteration.

## Iteration 2026-07-03: Low-Deck Lillie Probe

Reason:

- Latest Ogerpon and mirror traces still show no-active losses and some long-game deck-out losses.
- Prior attempts to solve this by larger board setup were rejected, so this probe tried a narrower resource rule: use `Lillie's Determination` as a low-deck refill only when enough hand cards can be shuffled back.

Candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_lowdecklillie`
- Rule:
  - If deck count is `<= 3` and the post-Lillie deck can still support the draw, raise Lillie priority to `18000`.
  - This was intended to stay below clear Boss-lethal / Cornerstone-bypass priorities while preventing avoidable deck-out.

Focused probe:

- Output:
  - `analysis_outputs/meta_suite_lowdecklillie_probe15_results.csv`
  - `analysis_outputs/meta_suite_lowdecklillie_probe15_summary.csv`
  - `analysis_outputs/meta_suite_lowdecklillie_probe15_games.csv`
- Opponents: Archaludon, Ogerpon, Starmie.
- Games: `15` per seat and matchup.

| Candidate | Archaludon | Ogerpon | Starmie | Public proxy | Starmie-heavy proxy | Equal selected buckets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `current` | `16 / 30` | `21 / 30` | `28 / 30` | `0.6303` | `0.7833` | `0.7222` |
| `lowdecklillie` | `11 / 30` | `21 / 30` | `26 / 30` | `0.5333` | `0.6792` | `0.6444` |

Decision:

- Reject `lowdecklillie`.
- It did not improve Ogerpon, and it materially hurt mirror and Starmie. The deck-out symptom is real, but spending late supporter turns on refill appears to cost too much tempo.
- Current preferred archive remains `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.

## Iteration 2026-07-03: Non-Ex Archaludon As Search Cost

Reason:

- The deck includes non-ex `Archaludon` mainly for Ogerpon / Cornerstone Mask Ogerpon ex.
- Outside Ogerpon, non-ex `Archaludon` is usually a dead hand card because the agent holds non-ex evolution and prefers Archaludon ex.
- Existing Ultra Ball safety logic did not count this card as a safe discard, so the agent could miss setup tempo or discard less appropriate cards.

Rejected probe before this:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_ogernonexice`
- Idea: allow `Jumbo Ice Cream` on damaged non-ex `Archaludon` in Ogerpon games.
- Probe output: `analysis_outputs/meta_suite_ogernonexice_probe20_summary.csv`
- Result:
  - current public proxy `0.6773`, Starmie-heavy `0.7156`, equal selected `0.7250`
  - ogernonexice public proxy `0.5750`, Starmie-heavy `0.7469`, equal selected `0.6833`
- Decision: reject. It did not improve Ogerpon and hurt the broader selected buckets.

Adopted candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost.tar.gz`

Rule change:

- If Ogerpon is not detected, count non-ex `Archaludon` as a safe discard for Ultra Ball setup.
- If Ogerpon is detected, keep the existing Ogerpon preservation rule:
  - keep non-ex `Archaludon`
  - avoid discarding it
  - still search/evolve it for Cornerstone Mask Ogerpon ex

Probe:

- Output:
  - `analysis_outputs/meta_suite_nonexcost_probe15_summary.csv`
- Games: `15` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `current` | `0.7306` | `0.7333` | `0.7810` |
| `nonexcost` | `0.7741` | `0.7500` | `0.8000` |

Confirmation:

- Output:
  - `analysis_outputs/meta_suite_nonexcost_confirm_g20_results.csv`
  - `analysis_outputs/meta_suite_nonexcost_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_nonexcost_confirm_g20_games.csv`
- Games: `20` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `current` | `0.7819` | `0.7650` | `0.8107` |
| `nonexcost` | `0.8111` | `0.7650` | `0.8179` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `current` | `35 / 40` | `31 / 40` | `23 / 40` | `26 / 40` | `39 / 40` | `38 / 40` | `35 / 40` |
| `nonexcost` | `37 / 40` | `34 / 40` | `21 / 40` | `28 / 40` | `36 / 40` | `38 / 40` | `35 / 40` |

Interpretation:

- The gain reproduced on public-sample weighting.
- Starmie-heavy remained equal, which is acceptable because Starmie is a major public axis.
- Ogerpon did not collapse in confirmation; it improved in this run despite the theoretical risk.
- Mirror and Lucario fell slightly, but not enough to offset Marnie, Alakazam, and Ogerpon gains under the public weights.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- No `__pycache__` or `.pyc` entries were present in the archive listing.
- Extracted archive smoke test vs `meta_agents/archaludon_public` ran `2` games with `0` action errors.

Current decision:

- New preferred local submission archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost.tar.gz`.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz` as the previous stable fallback.

Rejected follow-up:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_archline3`
- Idea:
  - Add explicit `archaludon` matchup detection when opponent Duraludon / Archaludon / Archaludon ex is visible.
  - In that matchup only, search/recover a third Duraludon / Archaludon ex line to reduce no-active mirror losses.
- Probe output: `analysis_outputs/meta_suite_archline3_probe15_summary.csv`
- Result:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Public proxy | Equal selected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nonexcost` | `27 / 30` | `23 / 30` | `15 / 30` | `18 / 30` | `0.7409` | `0.6917` |
| `archline3` | `27 / 30` | `26 / 30` | `13 / 30` | `20 / 30` | `0.7688` | `0.7167` |

Decision:

- Reject `archline3`.
- It failed the intended target: Archaludon mirror dropped from `15 / 30` to `13 / 30`.
- The Alakazam/Ogerpon improvement is likely sampling noise because the new rule only triggers on visible Archaludon-family cards.

## Iteration 2026-07-03: Non-Ex Cost Priority Split

Reason:

- `nonexcost` improved one confirmation run, but later same-size comparisons showed high variance and some instability.
- The question was whether the improvement came from:
  - counting non-ex `Archaludon` as a safe Ultra Ball cost,
  - strongly preferring it as the actual Ultra Ball discard,
  - or also discarding it in generic discard contexts.

Tested split variants:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_ubonly`
  - Keep non-ex `Archaludon` as an Ultra Ball discard target.
  - Remove the generic discard bonus.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub`
  - Keep non-ex `Archaludon` as a safe cost.
  - Lower its Ultra Ball discard priority from `13000` to `9500`.
  - Keep the generic outside-Ogerpon discard rule.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_countonly`
  - Only count non-ex `Archaludon` as safe cost.
  - Do not explicitly prioritize discarding it.

Initial split screen:

- Output: `analysis_outputs/meta_suite_nonexcost_split_g10_summary.csv`
- Games: `10` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `base` | `0.7500` | `0.8100` | `0.7786` |
| `nonexcost` | `0.6875` | `0.6450` | `0.7429` |
| `ubonly` | `0.7694` | `0.6650` | `0.7571` |
| `lowub` | `0.8319` | `0.7950` | `0.8286` |
| `countonly` | `0.7917` | `0.7200` | `0.8071` |

Confirmation:

- Output: `analysis_outputs/meta_suite_lowub_confirm_g20_summary.csv`
- Games: `20` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `base` | `0.7965` | `0.7575` | `0.8107` |
| `nonexcost` | `0.7639` | `0.7025` | `0.7857` |
| `lowub` | `0.7701` | `0.7875` | `0.8036` |

Tie-break:

- Output: `analysis_outputs/meta_suite_lowub_tiebreak_g20_summary.csv`
- Games: `20` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `base` | `0.7576` | `0.6925` | `0.7893` |
| `lowub` | `0.7451` | `0.7200` | `0.7929` |

Aggregate across the available split/confirm/tie-break runs:

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `base` | `0.7746` | `0.7486` | `0.8000` |
| `lowub` | `0.7725` | `0.7620` | `0.8043` |
| `nonexcost` | `0.7675` | `0.7160` | `0.7900` |

Interpretation:

- The aggressive `nonexcost` priority was not stable enough to keep as preferred.
- `lowub` is slightly worse than `base` on the broad public sample aggregate, but better on Starmie-heavy and equal-bucket aggregates.
- Since the visible Discussion meta has repeatedly emphasized Starmie-style decks as a major top bucket, `lowub` is the better current branch for a Starmie/equal-weight assumption.
- If real submitted logs show old broad public-sample behavior with low Starmie, revert to `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.

Package verification:

- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz`
- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- No `__pycache__` or `.pyc` entries were present in the archive listing.
- Extracted archive smoke test vs `meta_agents/archaludon_public` ran `2` games with `0` action errors.

Current decision:

- Preferred for Starmie/equal-weight current-top assumption: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz`.
- Stable broad public-sample fallback: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.
- Demote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost.tar.gz`; it is now a superseded aggressive branch.

Rejected follow-up:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub_alakline3`
- Idea:
  - Many Alakazam losses end with no active Pokemon.
  - After Alakazam is visible, allow a third Duraludon / Archaludon ex line via search and Night Stretcher.
- Probe output: `analysis_outputs/meta_suite_alakline3_probe15_summary.csv`
- Opponents: Marnie, Alakazam, Ogerpon, Starmie.
- Result:

| Candidate | Marnie | Alakazam | Ogerpon | Starmie | Public proxy | Starmie-heavy proxy | Equal selected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lowub` | `25 / 30` | `26 / 30` | `16 / 30` | `29 / 30` | `0.8051` | `0.9381` | `0.8000` |
| `alakline3` | `27 / 30` | `22 / 30` | `13 / 30` | `26 / 30` | `0.7628` | `0.8286` | `0.7333` |

Decision:

- Reject `alakline3`.
- It failed the intended target and worsened Starmie/Ogerpon. Extra body recovery still appears too slow even when scoped to one control matchup.

## Iteration 2026-07-03: Current Top Recheck And Family Pivot

Reason:

- The submitted Archaludon branch was losing on the live ladder, so I rechecked whether the deck-power problem is better solved by copying broader top-deck families rather than making another small Archaludon rule patch.
- The visible leaderboard had moved again from the earlier live check.

Browser-visible leaderboard top 10 at this check:

| Rank | Team | Score | Last |
| ---: | --- | ---: | --- |
| 1 | `tonakaiiii` | `1272.1` | `2d` |
| 2 | `Yushin Ito` | `1197.7` | `8d` |
| 3 | `kazuki0123` | `1173.2` | `3d` |
| 4 | `chamboabi` | `1170.4` | `1h` |
| 5 | `rank5_japanese_name` | `1136.8` | `1h` |
| 6 | `btk15049` | `1127.6` | `7h` |
| 7 | `aidy` | `1121.2` | `2d` |
| 8 | `yamy893` | `1119.6` | `6d` |
| 9 | `XP3RiX` | `1116.2` | `14h` |
| 10 | `Akira-Ninth` | `1115.1` | `7d` |

Limit:

- The leaderboard exposes scores and public Game History buttons, but not full deck lists.
- Opening the external `ptcgvis.heroz.jp` visualizer from the in-app browser failed with a browser policy / site-load block, so this iteration uses:
  - current visible leaderboard names and scores,
  - the public Discussion archetype notes,
  - local public-top deck mimics already extracted from public episodes.

Deck-family classification kept for local work:

| Family | Local mimic / candidate role |
| --- | --- |
| Marnie / Grimmsnarl control | `submission_marnie_variant_tonakaiiii`, `submission_marnie_variant_kazuki_*`, `submission_marnie_grimmsnarl` |
| Great Tusk / Crustle deck-out | `submission_great_tusk_crustle_setupaz_targeted19_*` |
| Archaludon metal tempo | `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth*`, `meta_agents/archaludon_public` |
| Starmie water/fire/spread tempo | `meta_agents/starmie_public_simple` |
| Alakazam psychic control | `meta_agents/alakazam_psychic_public_simple` |
| Ogerpon toolbox | `meta_agents/ogerpon_toolbox_monnosuke_simple` |
| Hop / Trevenant mixed control | `meta_agents/hop_trevenant_public_simple` |
| Mega Lucario fast tempo | `meta_agents/mega_lucario_public_simple` |

Top-family screen:

- Output:
  - `analysis_outputs/meta_family_scout_g6_results.csv`
  - `analysis_outputs/meta_family_scout_g6_summary.csv`
  - `analysis_outputs/meta_family_scout_g6_games.csv`
- Games: `6` per seat and matchup, so this is a screen, not final proof.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `crustle_starmie` | `0.8287` | `0.4000` | `0.7381` |
| `arch_lowub` | `0.6713` | `0.7417` | `0.7381` |
| `marnie_tonakai` | `0.4954` | `0.5083` | `0.5000` |
| `marnie_kazuki` | `0.4676` | `0.5500` | `0.5119` |

Interpretation:

- Copying Marnie/Grimmsnarl directly is not good enough locally, despite Marnie-like lists being visible near the top.
- Great Tusk / Crustle is the strongest low-Starmie broad-meta copy.
- Archaludon is still the safer branch when Starmie is common.

Great Tusk variant recheck:

- Output:
  - `analysis_outputs/meta_family_gt_vs_arch_g8_results.csv`
  - `analysis_outputs/meta_family_gt_vs_arch_g8_summary.csv`
  - `analysis_outputs/meta_family_gt_vs_arch_g8_games.csv`
- Games: `8` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `gt_starmierush` | `0.9201` | `0.6188` | `0.8304` |
| `arch_lowub` | `0.7656` | `0.7937` | `0.8214` |
| `gt_ogertrap` | `0.8056` | `0.5125` | `0.7321` |
| `gt_marnieexplorer` | `0.7639` | `0.4688` | `0.6875` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gt_starmierush` | `15 / 16` | `16 / 16` | `14 / 16` | `15 / 16` | `14 / 16` | `14 / 16` | `5 / 16` |
| `arch_lowub` | `13 / 16` | `13 / 16` | `7 / 16` | `12 / 16` | `15 / 16` | `16 / 16` | `16 / 16` |
| `gt_ogertrap` | `12 / 16` | `16 / 16` | `10 / 16` | `14 / 16` | `16 / 16` | `10 / 16` | `4 / 16` |
| `gt_marnieexplorer` | `10 / 16` | `16 / 16` | `11 / 16` | `13 / 16` | `12 / 16` | `13 / 16` | `2 / 16` |

Package check:

- Archive: `submission_great_tusk_crustle_starmierush.tar.gz`
- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- No `__pycache__` or `.pyc` entries were present in the archive listing.
- Extracted archive smoke test vs `meta_agents/starmie_public_simple` ran `2` games with `0` action errors.

Current decision:

- If changing deck because the submitted Archaludon branch is losing into the current broad visible field, use `submission_great_tusk_crustle_starmierush.tar.gz` as the next broad-meta submission candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz` as the Starmie-heavy / equal-bucket pivot.
- Do not submit copied Marnie/Grimmsnarl as-is. It is useful as a meta bucket, but not strong enough locally without a deeper answer to Archaludon and Ogerpon.
- The next feedback loop after submission should classify losses first. If losses show repeated Starmie, pivot back to Archaludon; if losses show Marnie/Ogerpon/Alakazam/Archaludon mix, keep iterating Great Tusk rules.

Rejected follow-up:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nocrustle`
- Idea:
  - Starmie losses showed repeated board-wipe losses where `Dwebble` / `Crustle` became extra prizes.
  - Against visible Starmie, reduce `Buddy-Buddy Poffin`, `Dwebble`, `Crustle`, Crustle evolution, Crustle energy attachment, and Dwebble/Crustle recovery priority.
  - Preserve the Great Tusk search / energy plan.
- Focused Starmie probe:
  - Output: `analysis_outputs/meta_suite_gt_nocrustle_starmie_probe10_summary.csv`
  - `starmierush`: `1 / 20`
  - `nocrustle`: `5 / 20`
- Confirmation:
  - Output: `analysis_outputs/meta_suite_gt_nocrustle_confirm_g15_summary.csv`
  - Games: `15` per seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `starmierush` | `0.8361` | `0.4733` | `0.7619` |
| `nocrustle` | `0.8222` | `0.4033` | `0.7476` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `starmierush` | `24 / 30` | `30 / 30` | `19 / 30` | `28 / 30` | `28 / 30` | `26 / 30` | `5 / 30` |
| `nocrustle` | `26 / 30` | `28 / 30` | `15 / 30` | `30 / 30` | `29 / 30` | `25 / 30` | `4 / 30` |

Decision:

- Reject `nocrustle`.
- The focused Starmie gain did not reproduce at confirmation size.
- The change also made the important Archaludon and Starmie-heavy scenarios worse. Dwebble/Crustle are liabilities into Starmie, but suppressing the line too hard removes needed fallback bodies and search value.

Rejected Archaludon follow-up:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub_dupnonex`
- Idea:
  - The non-ex `Archaludon` is an Ogerpon answer, but current `lowub` can spend it before Ogerpon is visible.
  - Keep the first non-ex `Archaludon` while the matchup is still `generic`.
  - Still allow it as a search/discard cost when a non-Ogerpon matchup is known, or when a duplicate non-ex `Archaludon` is in hand.
- Probe output:
  - `analysis_outputs/meta_suite_dupnonex_probe10_results.csv`
  - `analysis_outputs/meta_suite_dupnonex_probe10_summary.csv`
  - `analysis_outputs/meta_suite_dupnonex_probe10_games.csv`
- Opponents: Marnie, Alakazam, Archaludon, Ogerpon, Starmie.
- Games: `10` per seat and matchup.

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Starmie | Public proxy | Starmie-heavy proxy | Equal selected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lowub` | `16 / 20` | `16 / 20` | `13 / 20` | `12 / 20` | `18 / 20` | `0.7500` | `0.8050` | `0.7500` |
| `dupnonex` | `17 / 20` | `16 / 20` | `5 / 20` | `15 / 20` | `17 / 20` | `0.7094` | `0.6600` | `0.7000` |

Decision:

- Reject `dupnonex`.
- It improved Ogerpon, but the Archaludon mirror collapsed too much. Holding the first non-ex `Archaludon` in unknown matchups costs early Ultra Ball tempo and line consistency.

## Iteration 2026-07-03: Public Mimic Recheck and Marnie/Starmie Rule Probes

Archaludon lowub Marnie-specific probes:

- Directories:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub_marniedetect`
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub_marnieice210`
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub_marnieboss`
- Ideas:
  - Detect Marnie/Grimmsnarl from IDs `646`, `647`, `648`, and `649`.
  - Lower Jumbo Ice Cream threshold to `210` against Marnie.
  - When a low-prize Active is already KO-able, use Boss's Orders on a KO-able benched `Marnie's Grimmsnarl ex` instead.
- Focused Marnie outputs:
  - `analysis_outputs/meta_suite_marniedetect_marnie_g20_summary.csv`
  - `analysis_outputs/meta_suite_marnie_split_g20_summary.csv`

| Candidate | Marnie |
| --- | ---: |
| `lowub` | `36 / 40` |
| `marnieice210` | `33 / 40` |
| `marnieboss` | `34 / 40` |

Decision:

- Reject all three Marnie-specific probes.
- The baseline already wins the Marnie bucket at a high rate, and both the heal-threshold and Boss-priority changes reduced it.

Public mimic candidate screen:

- Output:
  - `analysis_outputs/meta_suite_public_mimics_screen_g6_summary.csv`
  - `analysis_outputs/meta_suite_public_mimics_screen_g6_results.csv`
  - `analysis_outputs/meta_suite_public_mimics_screen_g6_games.csv`
- Games: `6` per ordered seat and matchup, so this is a screen only.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `gt_starmierush` | `0.8009` | `0.4417` | `0.7143` |
| `lowub` | `0.7083` | `0.7500` | `0.7500` |
| `arch_public` | `0.7222` | `0.7583` | `0.7262` |
| `starmie_public` | `0.6343` | `0.4667` | `0.6905` |
| `ogerpon_public` | `0.6273` | `0.3167` | `0.5119` |
| `marnie_public` | `0.4259` | `0.3750` | `0.4762` |
| `alakazam_public` | `0.3958` | `0.3833` | `0.4762` |

Interpretation:

- The public-copy agents are useful opponent buckets, but none beats the current Great Tusk / Archaludon candidates as a submission candidate.
- `starmie_public` has real deck power into Ogerpon, Lucario, Hop, and Alakazam, but it is too weak into Archaludon and only middling into Marnie.
- `arch_public` is close on Starmie-heavy assumptions, but its Ogerpon bucket was very poor in this screen, so it is not a better pivot than the Ogerpon-aware Archaludon branches.

Rejected Starmie follow-up:

- Directory: `submission_starmie_public_archtarget`
- Idea:
  - Start from `meta_agents/starmie_public_simple`.
  - Against visible Archaludon, use Boss's Orders to pick off KO-able `Duraludon`, `Relicanth`, `Cinderace`, or damaged `Archaludon ex`.
- Focused output:
  - `analysis_outputs/meta_suite_starmie_archtarget_arch_g20_summary.csv`
- Result:
  - `starmie_base` vs Archaludon: `2 / 40`.
  - `starmie_archtarget` vs Archaludon: `3 / 40`.

Decision:

- Reject `starmie_archtarget`.
- The rule nudged one seat but did not fix the structural Archaludon problem. A Starmie submission would need a much deeper deck/agent rebuild, not a small target-selection patch.

## Iteration 2026-07-03: Archaludon Non-Ex Cost Gating

Reason:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth` and `lowub` use the same deck.
- Their only important difference is whether non-ex `Archaludon` `840` can be counted and selected as an Ultra Ball / discard cost outside Ogerpon.
- Prior runs suggested `lowub` helps Starmie/Ogerpon assumptions but can give up broad public-sample stability.

Rejected Alakazam-preserve probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub_keepala840`
- Idea:
  - Keep the `lowub` cost rules generally.
  - But when Alakazam is visible, preserve non-ex `Archaludon` the same way Ogerpon does.
- Probe output:
  - `analysis_outputs/meta_suite_keepala840_probe15_summary.csv`
- Result:

| Candidate | Alakazam | Archaludon | Ogerpon | Starmie | Public proxy | Starmie-heavy proxy | Equal selected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lowub` | `28 / 30` | `11 / 30` | `21 / 30` | `26 / 30` | `0.7238` | `0.7300` | `0.7167` |
| `keepala840` | `24 / 30` | `9 / 30` | `19 / 30` | `25 / 30` | `0.6270` | `0.6667` | `0.6417` |

Decision:

- Reject `keepala840`.
- Alakazam's `Powerful Hand` places damage counters based on hand size, so non-ex `Archaludon`'s Basic-damage prevention is not the right answer. The card is better as setup cost in this matchup.

Adopted broad/equal Archaludon probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_starmiecost`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_starmiecost.tar.gz`
- Idea:
  - Start from the stable `cut1fml1relicanth` rules.
  - Only allow non-ex `Archaludon` as a safe discard / Ultra Ball cost when Starmie is visible.
  - Preserve base behavior for Marnie, Alakazam, Archaludon, Lucario, and Hop.

Probe:

- Output: `analysis_outputs/meta_suite_starmiecost_probe10_summary.csv`
- Result: `starmiecost` led all three scenario aggregates in the 10-game/seat screen.

Confirmation:

- Output:
  - `analysis_outputs/meta_suite_starmiecost_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_starmiecost_confirm_g20_results.csv`
  - `analysis_outputs/meta_suite_starmiecost_confirm_g20_games.csv`
- Games: `20` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `base` | `0.8118` | `0.7825` | `0.8214` |
| `lowub` | `0.7875` | `0.7725` | `0.8214` |
| `starmiecost` | `0.8458` | `0.7675` | `0.8500` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base` | `39 / 40` | `32 / 40` | `23 / 40` | `23 / 40` | `38 / 40` | `39 / 40` | `36 / 40` |
| `lowub` | `36 / 40` | `30 / 40` | `23 / 40` | `27 / 40` | `38 / 40` | `40 / 40` | `36 / 40` |
| `starmiecost` | `39 / 40` | `36 / 40` | `20 / 40` | `29 / 40` | `40 / 40` | `39 / 40` | `35 / 40` |

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_starmiecost_summary.csv`
  - Opponents: Ogerpon and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_starmiecost.tar.gz` as the new broad/equal Archaludon-family candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz` only as a pure Starmie-heavy / Ogerpon-favoring pivot.
- Keep `submission_great_tusk_crustle_starmierush.tar.gz` as the low-Starmie broad-meta branch.

Follow-up correction:

- Additional same-candidate-order and single-candidate checks showed that non-Starmie bucket differences are mostly evaluation variance.
- The only intentional `starmiecost` behavior difference is in the Starmie matchup, and that bucket did not improve when runs were aggregated.
- Aggregate across `meta_suite_starmiecost_probe10`, `meta_suite_starmiecost_confirm_g20`, and single-candidate `g12`:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie | Public sample | Starmie-heavy | Equal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base` | `72 / 84` | `70 / 84` | `49 / 84` | `54 / 84` | `78 / 84` | `82 / 84` | `75 / 84` | `0.7927` | `0.7881` | `0.8163` |
| `starmiecost` | `81 / 84` | `76 / 84` | `44 / 84` | `58 / 84` | `82 / 84` | `83 / 84` | `73 / 84` | `0.8433` | `0.7726` | `0.8452` |

Corrected decision:

- Do not treat `starmiecost` as a proven improvement.
- It remains a runnable archive, but the causal Starmie-specific rule did not improve the intended bucket.
- Preferred Archaludon candidates remain:
  - Broad stable fallback: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.
  - Ogerpon/Starmie-tilted branch: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz`.

## Iteration 2026-07-03: Public Archaludon Notebook and FML4 Non-Ex1 Probe

Notebook screen:

- Public notebook output `notebook_output/masamikobayashi_archaludon` is identical to `meta_agents/archaludon_public`.
- Screen output:
  - `analysis_outputs/meta_suite_notebook_agents_screen_g8_summary.csv`
- It confirmed the known shape: pure public Archaludon is strong into Starmie/Marnie/Hop/Lucario but very weak into Ogerpon.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `masami_arch` | `0.7743` | `0.8125` | `0.7857` |
| `arch_base` | `0.7292` | `0.6625` | `0.7679` |
| `gt_starmierush` | `0.7743` | `0.5813` | `0.7589` |
| `koushikrudra` | `0.6580` | `0.6562` | `0.6696` |

Rejected FML4 non-ex1 probe:

- Directory: `submission_archaludon_ogerboss_nonex1_cutrelic`
- Idea:
  - Start from the existing non-ex1 Ogerpon rules.
  - Use public Archaludon-style FML4 durability.
  - Replace only `Relicanth` with one non-ex `Archaludon`, keeping all four Full Metal Lab.
- Probe output:
  - `analysis_outputs/meta_suite_nonex1_cutrelic_probe10_summary.csv`

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_public` | `0.7486` | `0.7700` | `0.7357` |
| `ogerboss` | `0.7167` | `0.7500` | `0.7643` |
| `nonex1_cutrelic` | `0.7556` | `0.6450` | `0.7714` |
| `nonex2_relicless` | `0.7472` | `0.8200` | `0.7857` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `nonex1_cutrelic` | `20 / 20` | `14 / 20` | `7 / 20` | `12 / 20` | `20 / 20` | `19 / 20` | `16 / 20` |
| `nonex2_relicless` | `16 / 20` | `17 / 20` | `10 / 20` | `9 / 20` | `19 / 20` | `19 / 20` | `20 / 20` |

Decision:

- Reject `nonex1_cutrelic`.
- It improved Ogerpon compared with pure public Archaludon, but lost too much Starmie-heavy value and did not beat the existing non-ex2 relicless branch.

## Iteration 2026-07-03: Great Tusk Starmie Override Audit

Reason:

- `submission_great_tusk_crustle_setupaz_targeted19_starmierush` and public notebook output `notebook_output/koushikrudra_i-have-one-rear-card` use the same deck list.
- The public notebook implementation had a better Starmie signal in the notebook-agent screen, despite weaker broad performance.
- The key difference was playing rules: current `starmierush` had many Starmie-specific overrides that forced extra Great Tusk bodies and suppressed Dwebble/Crustle wall lines.

Candidate:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride`
- Archive: `submission_great_tusk_crustle_starmierush_nostarmieoverride.tar.gz`
- Change:
  - Keep all current non-Starmie targeted rules.
  - Make `facing_starmie()` return `False`, disabling only the Starmie-specific overrides.

Focused Starmie check:

- Output:
  - `analysis_outputs/meta_suite_gt_nostarmieoverride_starmie_g30_summary.csv`
  - `analysis_outputs/meta_suite_gt_nostarmieoverride_starmie_g30_results.csv`
- Games: `30` per ordered seat against the Starmie mimic.

| Candidate | Starmie |
| --- | ---: |
| `starmierush` | `9 / 60` |
| `nostarmieoverride` | `19 / 60` |
| `koushikrudra` | `16 / 60` |

Confirmation:

- Output:
  - `analysis_outputs/meta_suite_gt_nostarmieoverride_confirm_g15_summary.csv`
  - `analysis_outputs/meta_suite_gt_nostarmieoverride_confirm_g15_results.csv`
- Games: `15` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `starmierush` | `0.8000` | `0.4100` | `0.7095` |
| `nostarmieoverride` | `0.8472` | `0.5633` | `0.7714` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `starmierush` | `25 / 30` | `27 / 30` | `18 / 30` | `28 / 30` | `22 / 30` | `26 / 30` | `3 / 30` |
| `nostarmieoverride` | `27 / 30` | `28 / 30` | `21 / 30` | `25 / 30` | `29 / 30` | `22 / 30` | `10 / 30` |

Interpretation:

- The causal Starmie bucket improvement is real in both focused and broader checks.
- Non-Starmie bucket differences are mostly evaluation variance because the code path only changes when Starmie is visible.
- The earlier Starmie-specific "rush" rules were overfitted in the wrong direction: forcing extra Great Tusk bodies and suppressing the Crustle line made the matchup worse.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_gt_nostarmieoverride_summary.csv`
  - Opponents: Ogerpon and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_great_tusk_crustle_starmierush_nostarmieoverride.tar.gz` over `submission_great_tusk_crustle_starmierush.tar.gz` as the Great Tusk branch.
- Keep Great Tusk as the low-Starmie / broad-meta branch, but this new variant is less fragile when Starmie appears.

## Iteration 2026-07-03: Great Tusk Starmie KO-Mode Audit

Reason:

- Starmie loss traces showed occasional `Giant Tusk` attacks from Great Tusk.
- In the Starmie matchup, the primary route is deck-out via `Land Collapse`; non-terminal damage attacks often spend a turn without advancing that route.
- The previous `nostarmieoverride` branch intentionally disabled the broad Starmie-specific override. This audit keeps that decision and adds only a thin Starmie package detector for KO-mode suppression.

Tooling note:

- Added `--fair-seeds` to `tools/run_meta_suite.py` to reuse the same game-id schedule for candidates.
- This is useful for trace naming and matchup ordering, but `game_id` is not the engine RNG seed. Treat candidate comparisons as repeated-sample estimates, not perfectly paired deterministic tests.

Candidates:

- `nogiantstarmie`
  - Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie`
  - Archive: `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie.tar.gz`
  - Deck: unchanged from `nostarmieoverride`.
  - Code change:
    - Add `seeing_starmie_package()` using visible Starmie IDs.
    - In `should_ko_mode()`, return `False` when the Starmie package is visible.
    - Do not re-enable the old `facing_starmie()` overrides.
- `stretcher`
  - Idea: replace one `Xerosic's Machinations` with `Night Stretcher`.
  - Result: not enough benefit; worse in follow-up Starmie and broad checks.
- `nogiant_nogust`
  - Idea: combine KO-mode suppression with lower early `Boss's Orders` / `Lisia's Appeal` priority into Starmie.
  - Result: worse than `nogiantstarmie`; early gust is not the main leak.

Focused Starmie checks:

- Output:
  - `analysis_outputs/meta_suite_gt_starmie_fair_g60_summary.csv`
  - `analysis_outputs/meta_suite_gt_noguststarmie_starmie_g50_summary.csv`

| Candidate | Starmie check A | Starmie check B |
| --- | ---: | ---: |
| `nostarmieoverride` | `27 / 120` | `23 / 100` |
| `nogiantstarmie` | `36 / 120` | `40 / 100` |
| `stretcher` | `28 / 120` | n/a |
| `nogiant_nogust` | n/a | `31 / 100` |

Broad check:

- Output:
  - `analysis_outputs/meta_suite_gt_nogiantstarmie_confirm_fair_g20_summary.csv`
- Games: `20` per ordered seat and matchup.
- The broad sample did not show a higher overall score for `nogiantstarmie`, but the only intended behavioral change is gated on visible Starmie IDs.
- Non-Starmie differences should be treated as evaluation noise unless a visible card-id overlap is found.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_gt_nogiantstarmie_summary.csv`
  - Opponents: Ogerpon and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie.tar.gz` over `submission_great_tusk_crustle_starmierush_nostarmieoverride.tar.gz` as the Great Tusk branch.
- Reject `stretcher` and `nogiant_nogust` for now.

## Iteration 2026-07-03: Champion Family Recheck After KO-Mode Patch

Purpose:

- Recheck the current best Great Tusk, Archaludon, and Marnie-family candidates after the Great Tusk Starmie KO-mode patch.
- Decide which family should receive the next local tuning pass.

Output:

- `analysis_outputs/meta_suite_champion_recheck_g10_summary.csv`
- `analysis_outputs/meta_suite_champion_recheck_g10_results.csv`
- `analysis_outputs/meta_suite_champion_recheck_g10_games.csv`

Candidates:

- `gt_nogiant`: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie`
- `arch_broad`: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth`
- `arch_lowub`: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub`
- `marnie_xerosic1`: `submission_marnie_variant_kazuki_boss2_xerosic1_rules`

Scenario result:

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `gt_nogiant` | `0.8250` | `0.6350` | `0.7786` |
| `arch_broad` | `0.7264` | `0.6450` | `0.7643` |
| `arch_lowub` | `0.7944` | `0.7700` | `0.8286` |
| `marnie_xerosic1` | `0.5444` | `0.4400` | `0.5714` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gt_nogiant` | `16 / 20` | `19 / 20` | `13 / 20` | `19 / 20` | `19 / 20` | `13 / 20` | `10 / 20` |
| `arch_broad` | `18 / 20` | `12 / 20` | `10 / 20` | `13 / 20` | `20 / 20` | `19 / 20` | `15 / 20` |
| `arch_lowub` | `17 / 20` | `15 / 20` | `13 / 20` | `16 / 20` | `18 / 20` | `20 / 20` | `17 / 20` |
| `marnie_xerosic1` | `10 / 20` | `15 / 20` | `6 / 20` | `3 / 20` | `18 / 20` | `20 / 20` | `8 / 20` |

Interpretation:

- Public-sample weighting still favors Great Tusk because Marnie, Alakazam, and Ogerpon are large visible buckets and `gt_nogiant` is strong into all three locally.
- Starmie-heavy and equal-bucket assumptions favor `arch_lowub`.
- Copied/tuned Marnie remains useful as an opponent family, but not as the submission candidate in this local suite.
- Archaludon lowub's remaining weakness is mostly public-weight tradeoff, not one obvious micro-rule. Prior lowub probes against Marnie, Alakazam, Ogerpon, and Starmie mostly showed tradeoffs or noise.

Current candidate map:

- Public-like / Marnie-Alakazam-Ogerpon mix: `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie.tar.gz`.
- Starmie-heavy or equal-meta pivot: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz`.
- Stable Archaludon fallback: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.
- Marnie family: keep as local opponent / fallback only; do not submit copied Marnie without a deeper answer to Archaludon and Ogerpon.

## Iteration 2026-07-03: Great Tusk Recovery Slot Check

Reason:

- `gt_nogiant` still loses some Archaludon and Hop games by running out of board before the opponent decks out.
- Archaludon loss traces often had the opponent deck at only `1-4` cards remaining, while our side ended with no active Pokemon.
- This suggested testing one recovery card, but the slot matters because cutting hand disruption hurt earlier Starmie/tempo checks.

Rejected rule/deck probes:

- `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_hoplate`
  - Idea: delay Hop/Trevenant trap from `me.deckCount <= opponent.deckCount + 8` to `+4`.
  - Output: `analysis_outputs/meta_suite_gt_hoplate_hop_g60_summary.csv`
  - Result: Hop fell from `103 / 120` to `92 / 120`.
  - Decision: reject. Early trap turns are still needed against Hop.
- `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher`
  - Deck: `-1` Xerosic's Machinations, `+1` Night Stretcher.
  - Outputs:
    - `analysis_outputs/meta_suite_gt_nogiant_stretcher_arch_g60_summary.csv`
    - `analysis_outputs/meta_suite_gt_nogiant_stretcher_confirm_g20_summary.csv`
  - Result: Archaludon improved in one focused run, but the broad check fell, especially Hop.
  - Decision: reject. Cutting Xerosic costs too much disruption/tempo.
- `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutice`
  - Deck: `-1` Jumbo Ice Cream, `+1` Night Stretcher.
  - Output: `analysis_outputs/meta_suite_gt_stretcher_slots_probe_g25_summary.csv`
  - Result: worse than both baseline and Terrakion-cut Stretcher in the slot screen.
  - Decision: reject. The one healing card is still valuable enough to keep.

Promoted candidate:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr`
- Archive: `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz`
- Deck change from `gt_nogiant`:
  - `-1` Terrakion `607`
  - `+1` Night Stretcher `1097`
- Code: unchanged from `gt_nogiant`.

Targeted checks:

- Archaludon focused:
  - Output: `analysis_outputs/meta_suite_gt_nogiant_stretcher_arch_g60_summary.csv`
  - `gt_nogiant`: `71 / 120`
  - Xerosic-cut Stretcher: `81 / 120`
- Terrakion-cut Stretcher probe:
  - Output: `analysis_outputs/meta_suite_gt_stretcher_cutterr_probe_g40_summary.csv`
  - `gt_nogiant`: Archaludon `51 / 80`, Lucario `67 / 80`, Hop `69 / 80`
  - `stretcher_cutterr`: Archaludon `56 / 80`, Lucario `71 / 80`, Hop `66 / 80`

Broad confirmation:

- Output:
  - `analysis_outputs/meta_suite_gt_stretcher_cutterr_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_gt_stretcher_cutterr_confirm_g20_results.csv`
- Games: `20` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `gt_nogiant` | `0.7882` | `0.5500` | `0.7393` |
| `stretcher_cutterr` | `0.8396` | `0.5850` | `0.7714` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gt_nogiant` | `29 / 40` | `39 / 40` | `24 / 40` | `33 / 40` | `34 / 40` | `34 / 40` | `14 / 40` |
| `stretcher_cutterr` | `32 / 40` | `38 / 40` | `31 / 40` | `37 / 40` | `35 / 40` | `30 / 40` | `13 / 40` |

Aggregate over the direct comparison runs:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie | Public proxy | Starmie-heavy proxy | Equal buckets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gt_nogiant` | `29 / 40` | `39 / 40` | `184 / 290` | `33 / 40` | `145 / 170` | `143 / 170` | `30 / 90` | `0.7932` | `0.5520` | `0.7410` |
| `stretcher_cutterr` | `32 / 40` | `38 / 40` | `201 / 290` | `37 / 40` | `152 / 170` | `139 / 170` | `28 / 90` | `0.8304` | `0.5535` | `0.7701` |

Interpretation:

- Night Stretcher is useful, but only when it replaces the low-weight emergency Terrakion slot.
- The gain is mainly Archaludon/Ogerpon/Marnie/Lucario resilience.
- Hop and Starmie fall slightly, but not enough to offset the public/equal aggregate gains.
- Because the code is unchanged, this is a deck-construction improvement rather than a new play-rule risk.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_gt_nogiant_stretcher_cutterr_summary.csv`
  - Opponents: Archaludon, Hop, and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz` as the Great Tusk public-like candidate.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie.tar.gz` as the slightly more Starmie/Hop-preserving fallback.
- Current map:
  - Public-like / Marnie-Alakazam-Ogerpon-Archaludon mix: `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz`.
  - Starmie-heavy or equal-meta pivot: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz`.
  - Stable Archaludon fallback: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.

## Iteration 2026-07-03: Family Pivot After Public Discussion Recheck

Context:

- The currently visible Kaggle Discussion note still supports a possible Starmie-heavy top environment:
  - `2026-06-28`: Starmie-style water/fire/spread tempo `5 / 10`
  - Archaludon-style metal tempo `3 / 10`
  - Psychic / Alakazam-style control `2 / 10`
- The submitted Great Tusk branch is strong in low-Starmie public-like buckets, but it remains structurally weak into Starmie.

Rejected Great Tusk follow-up:

- Directory: `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_archrules`
- Idea:
  - Against visible Archaludon-package cards, use `Night Stretcher` earlier to keep Great Tusk bodies available.
- Focused Archaludon output:
  - `analysis_outputs/meta_suite_gt_archrules_arch_g70_summary.csv`
  - `stretcher_cutterr`: `91 / 140`
  - `archrules`: `104 / 140`
- Broad confirmation output:
  - `analysis_outputs/meta_suite_gt_archrules_confirm_g20_summary.csv`
- Broad result:

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `stretcher_cutterr` | `0.8431` | `0.5650` | `0.7821` |
| `archrules` | `0.7861` | `0.4625` | `0.7214` |

Decision:

- Reject `archrules`.
- The Archaludon-focused gain did not survive the full-bucket check, and Starmie/Hop/Marnie side effects were too large.

Family comparison:

- Output:
  - `analysis_outputs/meta_suite_family_pivot_g20_summary.csv`
  - `analysis_outputs/meta_suite_family_pivot_g20_results.csv`
  - `analysis_outputs/meta_suite_family_pivot_g20_games.csv`
- Games: `20` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `gt_stretcher_cutterr` | `0.8194` | `0.5300` | `0.7464` |
| `arch_broad` | `0.8083` | `0.7900` | `0.8321` |
| `arch_lowub` | `0.7826` | `0.7175` | `0.8000` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gt_stretcher_cutterr` | `34 / 40` | `37 / 40` | `26 / 40` | `34 / 40` | `36 / 40` | `30 / 40` | `12 / 40` |
| `arch_broad` | `36 / 40` | `32 / 40` | `24 / 40` | `29 / 40` | `37 / 40` | `39 / 40` | `36 / 40` |
| `arch_lowub` | `35 / 40` | `32 / 40` | `21 / 40` | `28 / 40` | `36 / 40` | `40 / 40` | `32 / 40` |

Interpretation:

- If the real queue is still Marnie/Alakazam/Ogerpon-heavy and low-Starmie, `gt_stretcher_cutterr` remains defensible.
- If the current losses are caused by Starmie / Archaludon / Alakazam-style top-meta pressure, `arch_broad` is the better next submission candidate.
- `arch_lowub` did not beat the stable broad Archaludon branch in this rerun, so keep it as a tilted fallback rather than the first pivot.

Package verification:

- Rebuilt archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`
- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_arch_broad_family_pivot_summary.csv`
  - Opponents: Starmie, Archaludon, and Alakazam.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Updated candidate map:

- Next submission when current queue feels Starmie/Archaludon/Alakazam-heavy: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz`.
- Low-Starmie public-like fallback: `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz`.
- Ogerpon/Starmie-tilted but less stable fallback: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_nonexcost_lowub.tar.gz`.

## Iteration 2026-07-03: Archaludon Mirror Night Stretcher Rule

Reason:

- The family-pivot rerun made `arch_broad` the preferred Starmie/Archaludon/Alakazam-heavy candidate, but its weakest bucket was the Archaludon mirror.
- Mirror loss traces often showed Duraludon / Archaludon ex lines repeatedly going to discard before the attacker chain was fully stable.
- Earlier broad "third line" search rules were too slow, so this probe only changes `Night Stretcher` timing after the opponent has shown Archaludon-family cards.

Candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher.tar.gz`
- Deck: unchanged from `cut1fml1relicanth`.
- Code changes:
  - Add Archaludon-family recognition from visible IDs `{169, 190, 840}`.
  - In that matchup only, allow `Night Stretcher` earlier when a Duraludon / Archaludon ex rebuild line is in discard and the current line count is thin.
  - In `Night Stretcher` target selection, prefer Archaludon ex or Duraludon over generic fallbacks.

Focused Archaludon checks:

- Outputs:
  - `analysis_outputs/meta_suite_arch_mirrorstretcher_arch_g60_summary.csv`
  - `analysis_outputs/meta_suite_arch_mirrorstretcher_arch_g80b_summary.csv`
- Combined focused result:

| Candidate | Archaludon |
| --- | ---: |
| `arch_broad` | `127 / 280` |
| `mirrorstretcher` | `140 / 280` |

Full-bucket confirmation:

- Output:
  - `analysis_outputs/meta_suite_arch_mirrorstretcher_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_arch_mirrorstretcher_confirm_g20_results.csv`
- Games: `20` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_broad` | `0.7437` | `0.7200` | `0.7857` |
| `mirrorstretcher` | `0.7403` | `0.7550` | `0.7929` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_broad` | `30 / 40` | `33 / 40` | `19 / 40` | `27 / 40` | `38 / 40` | `40 / 40` | `33 / 40` |
| `mirrorstretcher` | `32 / 40` | `28 / 40` | `22 / 40` | `29 / 40` | `37 / 40` | `38 / 40` | `36 / 40` |

Interpretation:

- The targeted Archaludon bucket improvement reproduced across focused checks.
- Non-Archaludon bucket differences in the full confirmation are mostly sampling noise, because the new rule is gated on visible Archaludon-family IDs and the other local buckets do not contain those IDs.
- The public-weight proxy was essentially flat, while Starmie-heavy and equal-bucket proxies improved.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_arch_mirrorstretcher_summary.csv`
  - Opponents: Archaludon, Ogerpon, Starmie, and Alakazam.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher.tar.gz` as the current Starmie/Archaludon/Alakazam-heavy submission candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth.tar.gz` as the previous stable Archaludon fallback.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz` as the low-Starmie public-like fallback.

Rejected Ogerpon follow-up:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_ogersoftblock`
- Idea:
  - The existing Ogerpon rule fully blocks Archaludon ex evolution once Cornerstone Mask Ogerpon ex is visible.
  - This probe kept non-ex Archaludon as first choice, but allowed fallback Archaludon ex evolution / selection / preservation when no non-ex Archaludon was accessible.
- Focused output:
  - `analysis_outputs/meta_suite_arch_ogersoftblock_oger_g60_summary.csv`
- Result:

| Candidate | Ogerpon |
| --- | ---: |
| `mirrorstretcher` | `80 / 120` |
| `ogersoftblock` | `74 / 120` |

Seat split:

| Ordered pair | Candidate wins |
| --- | ---: |
| `mirrorstretcher` vs Ogerpon | `38 / 60` |
| `ogersoftblock` vs Ogerpon | `43 / 60` |
| Ogerpon vs `mirrorstretcher` | `42 / 60` |
| Ogerpon vs `ogersoftblock` | `31 / 60` |

Decision:

- Reject `ogersoftblock`.
- It helped one ordered seat but hurt the other much more. Gating on local player index would likely overfit the simulator seat/order rather than improve the general policy.
- Keep the stricter Cornerstone rule for now.

## Iteration 2026-07-03: Archaludon Alakazam Micro-Probes

Reason:

- After promoting `mirrorstretcher`, the next plausible weak bucket was Alakazam psychic control.
- Loss traces often ended with Alakazam `743` using high hand-size damage and our Duraludon / Archaludon ex line disappearing from board.
- Two conservative Alakazam-only probes were tested before changing the promoted candidate.

Rejected Alakazam Night Stretcher probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_alakstretcher`
- Idea:
  - Reuse the Archaludon mirror `Night Stretcher` rebuild logic against visible Alakazam-family cards.
  - Recover Duraludon / Archaludon ex earlier when the current line count is thin.
- Focused output:
  - `analysis_outputs/meta_suite_arch_alakstretcher_alak_g60_summary.csv`
- Result:

| Candidate | Alakazam |
| --- | ---: |
| `mirrorstretcher` | `100 / 120` |
| `alakstretcher` | `100 / 120` |

Decision:

- Reject `alakstretcher`.
- It shifted wins between ordered seats but did not improve the aggregate Alakazam bucket.

Rejected Alakazam Boss prize probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_alakbossprize`
- Idea:
  - When Active Alakazam is KO-able, use `Boss's Orders` on a KO-able benched `Fezandipiti ex` for a two-prize turn.
- Focused output:
  - `analysis_outputs/meta_suite_arch_alakbossprize_alak_g60_summary.csv`
- Result:

| Candidate | Alakazam |
| --- | ---: |
| `mirrorstretcher` | `101 / 120` |
| `alakbossprize` | `96 / 120` |

Decision:

- Reject `alakbossprize`.
- Taking the Active Alakazam off the board is more important than a greedy two-prize Boss line in this local matchup.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher.tar.gz` as the current Starmie/Archaludon/Alakazam-heavy candidate.

## Iteration 2026-07-03: Archaludon Mirror and Slot Follow-Up

Reason:

- `mirrorstretcher` remained the best Starmie/Archaludon/Alakazam-heavy candidate, but the Archaludon mirror was still the main weak bucket.
- Mirror loss traces often ended with no Duraludon / Archaludon ex chain left on our side.
- Several narrow mirror rules and one-card deck-slot changes were tested before changing the promoted candidate.

Rejected mirror-focused probes:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_relicfml4`
  - Deck: restore the older Relicanth / FML4 shell.
  - Focused mirror checks were effectively tied with current after aggregation, not a clear improvement.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_relicice3`
  - Deck: `+1` Relicanth, `-1` Jumbo Ice Cream.
  - Focused output: `analysis_outputs/meta_suite_arch_relic_slots_arch_g60_summary.csv`
  - Result: `58 / 120` vs current `64 / 120`.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_first`
  - Rule: choose first instead of second.
  - Focused output: `analysis_outputs/meta_suite_arch_first_arch_g60_summary.csv`
  - Result: `50 / 120` vs current `65 / 120`.
  - Decision: reject. Going second for Cinderace acceleration remains important.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_setupdura1`
  - Rule: bench exactly one Duraludon during setup.
  - Focused Archaludon/Alakazam output: `analysis_outputs/meta_suite_arch_setupdura1_arch_alak_g50_summary.csv`
  - Result: Alakazam rose slightly (`77 / 100` vs `75 / 100`), but Archaludon fell (`41 / 100` vs `44 / 100`).
  - Decision: reject.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_archcost840`
  - Rule: after Archaludon is visible, treat non-ex Archaludon `840` as Ultra Ball / discard cost.
  - Focused output: `analysis_outputs/meta_suite_arch_archcost840_arch_g80_summary.csv`
  - Result: `67 / 160` vs current `83 / 160`.
  - Decision: reject. The `840` copy is not just dead cost; spending it too readily hurts the line.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_mirrornonex`
  - Rule: allow non-ex Archaludon evolution as a one-prize mirror attacker.
  - Focused output: `analysis_outputs/meta_suite_arch_mirrornonex_arch_g80_summary.csv`
  - Result: `72 / 160` vs current `76 / 160`.
  - Decision: reject. The lower damage loses too much tempo.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_stretch4_cutice`
  - Deck: `+1` Night Stretcher, `-1` Jumbo Ice Cream.
  - Full output: `analysis_outputs/meta_suite_arch_stretch4_confirm_g20_summary.csv`
  - Result: public proxy `0.7479` vs current `0.8035`; mirror `12 / 40` vs current `17 / 40`.
  - Decision: reject.
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_fml4_cutice`
  - Deck: `+1` Full Metal Lab, `-1` Jumbo Ice Cream.
  - Focused output: `analysis_outputs/meta_suite_arch_fml4_cutice_arch_g70_summary.csv`
  - Result: `50 / 140` vs current `62 / 140`.
  - Decision: reject.

Near-slot screen:

- Output:
  - `analysis_outputs/meta_suite_arch_slot_screen_g8_summary.csv`
  - `analysis_outputs/meta_suite_arch_slot_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_arch_energy12_key_g50_summary.csv`
- Screened one-card deck changes:
  - `energy12_cutice`: `+1` Metal Energy, `-1` Jumbo Ice Cream.
  - `nonex3_cutice`: `+1` non-ex Archaludon `840`, `-1` Jumbo Ice Cream.
  - `energy12_cutgear`: `+1` Metal Energy, `-1` Pokegear.
  - `fml4_cutgear`: `+1` Full Metal Lab, `-1` Pokegear.

Confirmed slot comparison:

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `mirrorstretcher` | `0.7590` | `0.7125` | `0.7857` |
| `energy12_cutice` | `0.8063` | `0.7475` | `0.8214` |
| `nonex3_cutice` | `0.7583` | `0.7175` | `0.7857` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mirrorstretcher` | `38 / 40` | `28 / 40` | `18 / 40` | `25 / 40` | `37 / 40` | `39 / 40` | `35 / 40` |
| `energy12_cutice` | `37 / 40` | `34 / 40` | `17 / 40` | `32 / 40` | `37 / 40` | `37 / 40` | `36 / 40` |
| `nonex3_cutice` | `35 / 40` | `32 / 40` | `16 / 40` | `26 / 40` | `37 / 40` | `39 / 40` | `35 / 40` |

Additional key-bucket check:

- Opponents: Alakazam, Archaludon, Ogerpon.
- Games: `50` per ordered seat and matchup.
- Output: `analysis_outputs/meta_suite_arch_energy12_key_g50_summary.csv`
- Result:
  - `mirrorstretcher`: Alakazam `85 / 100`, Archaludon `46 / 100`, Ogerpon `63 / 100`.
  - `energy12_cutice`: Alakazam `82 / 100`, Archaludon `48 / 100`, Ogerpon `61 / 100`.
- Interpretation:
  - The second run was mixed, but it did not show a large collapse.
  - Combined with the full confirmation, the common key buckets still slightly favor `energy12_cutice`: Alakazam `116 / 140` vs `113 / 140`, Archaludon `65 / 140` vs `64 / 140`, Ogerpon `93 / 140` vs `88 / 140`.

Adopted candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice.tar.gz`
- Deck change from `mirrorstretcher`:
  - `+1` Metal Energy `8`
  - `-1` Jumbo Ice Cream `1147`
  - Final counts: Metal Energy `12`, Jumbo Ice Cream `3`, Full Metal Lab `3`, non-ex Archaludon `2`, Night Stretcher `3`.
- Code: unchanged from `mirrorstretcher`.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_arch_energy12_cutice_summary.csv`
  - Opponents: Archaludon, Alakazam, Ogerpon, and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice.tar.gz` as the current Starmie/Archaludon/Alakazam-heavy submission candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher.tar.gz` as the previous stable fallback.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz` as the low-Starmie public-like fallback.

## Iteration 2026-07-03: Archaludon Mirror Relicanth Boss Rule

Reason:

- After adopting `energy12_cutice`, the remaining weak bucket was still Archaludon mirror.
- Loss trace summaries showed several games where the opponent used `Raging Hammer`, often with public Archaludon lists that include `Relicanth`.
- The candidate tests a narrow mirror-only rule: when the Active is not already KO-able and the opponent has benched `Relicanth`, use `Boss's Orders` to remove it before it keeps enabling evolved attackers' `Raging Hammer`.

Candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic.tar.gz`
- Deck: unchanged from `energy12_cutice`.
- Code changes:
  - In Archaludon mirror only, raise `Boss's Orders` priority when opponent benched `Relicanth` exists and Active is not already KO-able.
  - In Boss target selection, prioritize opponent `Relicanth` in that mirror-specific case.

Focused mirror check:

- Output: `analysis_outputs/meta_suite_arch_bossrelic_arch_g80_summary.csv`
- Games: `80` per ordered seat.

| Candidate | Archaludon |
| --- | ---: |
| `energy12` | `67 / 160` |
| `archbossrelic` | `73 / 160` |

Full-bucket confirmation:

- Output:
  - `analysis_outputs/meta_suite_arch_bossrelic_confirm_g20_summary.csv`
  - `analysis_outputs/meta_suite_arch_bossrelic_confirm_g20_results.csv`
  - `analysis_outputs/meta_suite_arch_bossrelic_confirm_g20_games.csv`
- Games: `20` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `energy12` | `0.7528` | `0.7375` | `0.7786` |
| `archbossrelic` | `0.8153` | `0.7425` | `0.8214` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `energy12` | `33 / 40` | `33 / 40` | `18 / 40` | `25 / 40` | `36 / 40` | `38 / 40` | `35 / 40` |
| `archbossrelic` | `36 / 40` | `38 / 40` | `17 / 40` | `26 / 40` | `39 / 40` | `40 / 40` | `34 / 40` |

Interpretation:

- The targeted mirror-focused check improved from `67 / 160` to `73 / 160`.
- The full-bucket Archaludon cell was noisy and showed `17 / 40` vs `18 / 40`, but the combined Archaludon evidence still favors `archbossrelic`: `90 / 200` vs `85 / 200`.
- Non-Archaludon bucket differences are not causal because the new rule only triggers after visible Archaludon-family cards. Treat them as sampling variation, not as proof of broad rule impact.
- The rule is card-game-natural: if the opponent list relies on Relicanth to convert damage into Raging Hammer KOs, spending Boss to remove it can reduce the opponent's burst line.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_arch_bossrelic_summary.csv`
  - Opponents: Archaludon, Alakazam, Ogerpon, and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic.tar.gz` as the current Starmie/Archaludon/Alakazam-heavy submission candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice.tar.gz` as the previous fallback.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz` as the low-Starmie public-like fallback.

## Iteration 2026-07-03: Top-Mimic Family Recheck and Safe Relicanth Boss

Reason:

- The visible public top decks should be copied at the archetype level, not treated as one fixed list.
- Kaggle Discussion `709263` still framed the 2026-06-28 visible top 10 as Starmie / water-fire spread tempo, Archaludon metal tempo, and Alakazam psychic control.
- The local latest public episode sample remains 2026-07-02. The extracted 38 decks were:
  - `marnie_grimmsnarl`: 11
  - `alakazam_psychic`: 10
  - `archaludon_metal`: 6
  - `ogerpon_toolbox`: 4
  - `mega_lucario`: 2
  - `hop_trevenant`: 2
  - `unknown`: 2
  - `starmie_froslass`: 1

Interpretation:

- The public data supports multiple copied deck families, not a single best shell.
- Current local mimics cover the major families: Marnie, Alakazam, Archaludon, Ogerpon, Lucario, Hop, and Starmie.
- The main decision is between broad-public weighting, where Great Tusk can still look strong, and Starmie/Archaludon/Alakazam-heavy weighting, where Archaludon is safer.

Safety patch:

- The prior `archbossrelic` rule could over-prioritize opponent `Relicanth` in Archaludon mirrors.
- New directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe`
- New archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`
- Code changes:
  - Do not use the Relicanth Boss shortcut when a lethal benched target is available.
  - Only trigger the shortcut when Relicanth is actually KO-able by the planned Archaludon attack route.
  - Lower Relicanth's Boss target score below killable main attackers / ex targets, so it does not overwrite stronger prize-map targets.

Safe Relicanth focused mirror check:

- Output: `analysis_outputs/meta_suite_arch_bossrelic_safe_arch_g80_summary.csv`
- Games: `80` per ordered seat.

| Candidate | Archaludon |
| --- | ---: |
| `energy12` | `78 / 160` |
| `archbossrelic` | `75 / 160` |
| `archbossrelic_safe` | `82 / 160` |

Broad side-effect check:

- Output: `analysis_outputs/meta_suite_arch_bossrelic_safe_confirm_g20_summary.csv`
- Games: `20` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `energy12` | `0.8153` | `0.7725` | `0.8250` |
| `archbossrelic` | `0.7597` | `0.7325` | `0.7857` |
| `archbossrelic_safe` | `0.7868` | `0.7575` | `0.8071` |

Notes:

- The safe rule is gated to visible Archaludon-family IDs, so non-Archaludon bucket differences should be treated as simulator variance unless repeated.
- Combining the new Archaludon-focused and broad Archaludon cells gives `archbossrelic_safe` a small mirror edge over `energy12`.
- The unsafe `archbossrelic` rule is no longer preferred.

Family recheck:

- Output: `analysis_outputs/meta_suite_family_current_top_mimic_g10_summary.csv`
- Games: `10` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.8333` | `0.7600` | `0.8429` |
| `arch_energy12` | `0.8056` | `0.7650` | `0.8286` |
| `great_tusk` | `0.8458` | `0.5950` | `0.8000` |
| `marnie` | `0.4437` | `0.3375` | `0.4964` |
| `starmie` | `0.6160` | `0.5550` | `0.6821` |

Decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the current Starmie/Archaludon/Alakazam-heavy candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice.tar.gz` as the simpler stable fallback.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz` as the low-Starmie public-sample fallback.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries after rebuilding with exclusions.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_arch_bossrelic_safe_summary.csv`
  - Opponents: Archaludon, Alakazam, Ogerpon, and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

Rejected follow-up: own Relicanth slot

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_relic1_cutice`
- Deck change from `archbossrelic_safe`: `+1 Relicanth`, `-1 Jumbo Ice Cream`.
- Motivation: copy more of the public Archaludon mirror plan by enabling our own Raging Hammer line.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_relic1_arch_g60_summary.csv`
  - `arch_safe`: `52 / 120`
  - `safe_relic1`: `67 / 120`
- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_relic1_confirm_g20_summary.csv`

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.7931` | `0.7325` | `0.8000` |
| `safe_relic1` | `0.6924` | `0.6575` | `0.7357` |

Decision:

- Reject `safe_relic1`.
- The focused mirror gain did not survive broad confirmation; the lower healing count and extra low-HP bench liability are too costly.
- Keep `archbossrelic_safe` as the promoted candidate.

## Iteration 2026-07-03: Post-Safe Micro-Probes

Reason:

- After promoting `archbossrelic_safe`, the remaining plausible improvement areas were Ogerpon and Archaludon mirror play sequencing.
- The goal was to test narrow play-rule changes rather than change the deck shell again.

Rejected Ogerpon Night Stretcher probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_ogerstretcher`
- Idea:
  - In Ogerpon matchups, use `Night Stretcher` to rebuild the non-ex Archaludon answer after it is KO'd.
  - Prefer recovering non-ex `Archaludon` when a `Duraludon` is in play, otherwise recover `Duraludon`.
- Focused output:
  - `analysis_outputs/meta_suite_arch_ogerstretcher_oger_g60_summary.csv`
- Result:

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `88 / 120` |
| `ogerstretcher` | `81 / 120` |

Seat split:

| Ordered pair | Candidate wins |
| --- | ---: |
| `arch_safe` vs Ogerpon | `41 / 60` |
| Ogerpon vs `arch_safe` | `47 / 60` |
| `ogerstretcher` vs Ogerpon | `45 / 60` |
| Ogerpon vs `ogerstretcher` | `36 / 60` |

Decision:

- Reject `ogerstretcher`.
- The rule helped one ordered seat but hurt the other more. It likely spends Stretcher too slowly or disrupts the normal attacker chain.

Rejected Archaludon Boss priority probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_boss170`
- Idea:
  - When an attack is ready and opponent `Relicanth` is KO-able, raise the mirror Relicanth `Boss's Orders` priority from `15500` to `17000`, above `Explorer's Guidance`.
- Focused output:
  - `analysis_outputs/meta_suite_arch_boss170_arch_g60_summary.csv`
- Result:

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `61 / 120` |
| `boss170` | `53 / 120` |

Seat split:

| Ordered pair | Candidate wins |
| --- | ---: |
| `arch_safe` vs Archaludon | `25 / 60` |
| Archaludon vs `arch_safe` | `36 / 60` |
| `boss170` vs Archaludon | `32 / 60` |
| Archaludon vs `boss170` | `21 / 60` |

Decision:

- Reject `boss170`.
- Raising Boss above draw/setup improves one ordered seat but loses too much in the reverse order.

Candidate decision rerun:

- Output:
  - `analysis_outputs/meta_suite_candidate_decision_g30_summary.csv`
- Games: `30` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.8130` | `0.7683` | `0.8310` |
| `arch_energy12` | `0.7838` | `0.7633` | `0.8119` |
| `great_tusk` | `0.7898` | `0.5483` | `0.7500` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `56 / 60` | `48 / 60` | `35 / 60` | `41 / 60` | `57 / 60` | `60 / 60` | `52 / 60` |
| `arch_energy12` | `47 / 60` | `54 / 60` | `30 / 60` | `44 / 60` | `54 / 60` | `60 / 60` | `52 / 60` |
| `great_tusk` | `45 / 60` | `56 / 60` | `34 / 60` | `55 / 60` | `53 / 60` | `49 / 60` | `23 / 60` |

Decision:

- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the current promoted candidate.
- `great_tusk` is still useful as a low-Starmie fallback, but the latest `g30` run no longer beats `arch_safe` even under the 2026-07-02 public-sample weighting.
- `arch_energy12` remains the simpler fallback, but `arch_safe` has the best current aggregate evidence.

## Iteration 2026-07-03: Alakazam Third Line Search

Reason:

- In `analysis_outputs/meta_suite_candidate_decision_g30_summary.csv`, `arch_safe` was still only `48 / 60` against Alakazam.
- Loss trace summaries showed many losses ending with the opposing Alakazam at `80-140` HP while our side had no Active Pokemon left.
- The likely failure mode is not target choice but running out of Duraludon / Archaludon ex bodies before the final Alakazam is removed.

Candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz`
- Deck: unchanged from `archbossrelic_safe`.
- Code change:
  - When `detect_matchup(obs) == "alakazam"`, make `need_duraludon()` and `need_archaludon()` search toward a third Duraludon / Archaludon ex line instead of stopping at two.
  - The rule is matchup-gated; it should not intentionally affect Starmie, Marnie, Ogerpon, Hop, Lucario, or Archaludon unless Alakazam-family cards are visible.

Focused Alakazam check:

- Output: `analysis_outputs/meta_suite_arch_alakline3_alak_g80_summary.csv`
- Games: `80` per ordered seat.

| Candidate | Alakazam |
| --- | ---: |
| `arch_safe` | `123 / 160` |
| `alakline3` | `130 / 160` |

Broad confirmation:

- Output: `analysis_outputs/meta_suite_arch_alakline3_confirm_g30_summary.csv`
- Games: `30` per ordered seat and matchup.

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.7625` | `0.7483` | `0.8000` |
| `alakline3` | `0.8037` | `0.7200` | `0.8119` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `50 / 60` | `47 / 60` | `30 / 60` | `41 / 60` | `57 / 60` | `58 / 60` | `53 / 60` |
| `alakline3` | `50 / 60` | `56 / 60` | `30 / 60` | `41 / 60` | `59 / 60` | `59 / 60` | `46 / 60` |

Interpretation:

- The target matchup improved in both the focused and full checks.
- The Starmie bucket fell in the full check, but the new rule is strictly Alakazam-detection gated and the Starmie local deck has no Alakazam-family markers. Treat that difference as run variance rather than causal unless it reproduces under a Starmie-focused check with a rule trigger.
- Public-sample and equal-bucket proxies favor `alakline3`; Starmie-heavy proxy still slightly favors the previous `arch_safe`.

Decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the current public-sample / Alakazam-aware candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the more conservative Starmie-heavy fallback.

Package verification:

- Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Archive listing had no `__pycache__` or `.pyc` entries.
- Extracted archive smoke test:
  - Output: `analysis_outputs/package_smoke_arch_alakline3_summary.csv`
  - Opponents: Archaludon, Alakazam, Ogerpon, and Starmie.
  - Games: `2` per ordered seat and matchup.
  - Errors: `0`.

## Iteration 2026-07-03: Post-Alakline3 Regression and Ogerpon Probes

Starmie regression check:

- `alakline3` only changes `need_duraludon()` / `need_archaludon()` after Alakazam-family cards are visible.
- The Starmie public mimic has no Alakazam-family IDs, but the `g30` broad confirmation showed a lower Starmie bucket for `alakline3`.
- Focused output: `analysis_outputs/meta_suite_arch_alakline3_starmie_g100_summary.csv`
- Games: `100` per ordered seat.

| Candidate | Starmie |
| --- | ---: |
| `arch_safe` | `177 / 200` |
| `alakline3` | `169 / 200` |

Interpretation:

- The difference is real in this focused run but not causally explained by the rule gate; the local engine is not explicitly seeded by `game_id`, so candidate comparisons retain stochastic variance.
- Keep `arch_safe` as a Starmie-heavy fallback, but do not revert the public-sample candidate because `alakline3` has a large Alakazam gain.

Rejected Archaludon mirror line-search probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_archline3`
- Idea:
  - Extend the Alakazam third-line search rule to Archaludon mirrors.
- Focused output: `analysis_outputs/meta_suite_arch_alakline3_archline3_arch_g100_summary.csv`
- Result:

| Candidate | Archaludon |
| --- | ---: |
| `alakline3` | `96 / 200` |
| `archline3` | `89 / 200` |

Decision:

- Reject `archline3`.
- Extra search helps one seat but hurts the reverse order; it likely spends tempo on bodies instead of attack/heal timing.

Rejected Ogerpon non-ex healing probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_ogernonexheal`
- Idea:
  - Allow `Jumbo Ice Cream` on damaged non-ex `Archaludon` in Ogerpon games.
- Focused Ogerpon output: `analysis_outputs/meta_suite_arch_alakline3_ogernonexheal_oger_g80_summary.csv`
  - `alakline3`: `107 / 160`
  - `ogernonexheal`: `109 / 160`
- Broad output: `analysis_outputs/meta_suite_arch_alakline3_ogernonexheal_confirm_g20_summary.csv`

| Candidate | Public sample | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `alakline3` | `0.7951` | `0.7800` | `0.8179` |
| `ogernonexheal` | `0.7861` | `0.7750` | `0.7893` |

Decision:

- Reject `ogernonexheal`.
- The focused gain was tiny and did not survive broad confirmation.

Rejected Full Metal Lab non-ex Active probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_fmlnonexactive`
- Idea:
  - Treat non-ex `Archaludon` as a valid Metal Active for `Full Metal Lab` play.
- Focused output: `analysis_outputs/meta_suite_arch_alakline3_fmlnonexactive_oger_g80_summary.csv`
- Result:

| Candidate | Ogerpon |
| --- | ---: |
| `alakline3` | `115 / 160` |
| `fmlnonexactive` | `109 / 160` |

Decision:

- Reject `fmlnonexactive`.
- Although the rule is conceptually correct, playing the Stadium in those windows appears to cost more tempo than it saves.

Rejected Hero's Cape non-ex probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_ogercape840`
- Idea:
  - In Ogerpon games only, allow `Hero's Cape` on non-ex `Archaludon`.
- Focused output: `analysis_outputs/meta_suite_arch_alakline3_ogercape840_oger_g80_summary.csv`
- Result:

| Candidate | Ogerpon |
| --- | ---: |
| `alakline3` | `106 / 160` |
| `ogercape840` | `105 / 160` |

Decision:

- Reject `ogercape840`.
- Spending the ACE SPEC on non-ex Archaludon did not improve the Ogerpon bucket.

Current decision:

- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the current public-sample / Alakazam-aware candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the Starmie-heavy fallback.
- The remaining Ogerpon gains likely require deck construction changes or real submitted-match feedback rather than another one-line Ogerpon play-rule tweak.

## Iteration 2026-07-03: Current Leaderboard Check and Top20 Public Sample

Kaggle visible Leaderboard was checked on 2026-07-03 from the in-app browser.

Visible top 10 at that check:

1. `tonakaiiii` - `1276.8`
2. `kazuki0123` - `1209.1`
3. `Yushin Ito` - `1198.5`
4. `BluezLee` - `1147.3`
5. `undertaker3409` - `1131.1`
6. `XP3RiX` - `1130.9`
7. `btk15049` - `1124.5`
8. `aidy` - `1118.0`
9. `pokeka_ryo` - `1116.4`
10. `zoroark190` - `1110.5`

The Leaderboard exposes public Game History buttons and episode IDs, but not full deck lists directly. The daily public episode dataset index was refreshed and still ended at `2026-07-02`, so the latest usable bulk replay sample remains the 2026-07-02 dataset.

Downloaded one additional 2026-07-02 sample episode and extracted a 20-episode deck sample:

- Input: `data/episodes/2026-07-02-sample`
- Output: `analysis_outputs/episode_decks_2026_07_02_sample_20`

Updated deck buckets from 40 extracted decks:

- `marnie_grimmsnarl`: 12
- `alakazam_psychic`: 11
- `archaludon_metal`: 6
- `ogerpon_toolbox`: 4
- `mega_lucario`: 2
- `hop_trevenant`: 2
- `unknown`: 2
- `starmie_froslass`: 1

Added a new evaluation scenario to `tools/run_meta_suite.py`:

- `public_sample_2026_07_02_top20`
- Weights: Marnie 12, Alakazam 11, Archaludon 6, Ogerpon 4, Lucario 2, Hop 2, Starmie 1.
- The two unknown decks are excluded because there is no local mimic bucket.

Also fixed `tools/run_meta_suite.py` so candidate aliases cannot collide with public-meta bucket names. A candidate named exactly `marnie` or `starmie` corrupts summary aggregation because those names are also opponent bucket IDs. The script now raises a clear error and requires aliases such as `cand_marnie=...`.

Rejected Alakazam Night Stretcher rebuild probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_alakstretcher`
- Focused Alakazam output: `analysis_outputs/meta_suite_arch_alakline3_alakstretcher_alak_g80_summary.csv`

| Candidate | Alakazam |
| --- | ---: |
| `alakline3` | `133 / 160` |
| `alakstretcher` | `130 / 160` |

Decision:

- Reject `alakstretcher`.
- It spends Night Stretcher on rebuilding the Alakazam matchup line but did not improve the focused matchup.

Family recheck with top20 scenario:

- Output: `analysis_outputs/meta_suite_top20_family_recheck_unique_g10_summary.csv`
- Games: `10` per ordered seat and matchup.

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_alakline3` | `0.7197` | `0.6550` | `0.7500` |
| `arch_safe` | `0.7750` | `0.7300` | `0.8071` |
| `cand_marnie` | `0.4724` | `0.3950` | `0.4714` |
| `great_tusk` | `0.8500` | `0.4750` | `0.7214` |
| `cand_starmie` | `0.6211` | `0.4050` | `0.6357` |

Interpretation:

- Directly switching to the local Marnie or Starmie mimic is not justified under current rules. The public top lists are powerful, but our local policies for those decks are still much weaker than the top competitors' policies.
- Great Tusk still scores well under broad public-sample weighting, but its Starmie bucket remains a serious failure mode.
- Archaludon remains the best practical deck family for a submission candidate because it is strong into Marnie/Alakazam-style top buckets while not collapsing as badly into Starmie-heavy weighting.

Archaludon candidate confirmation:

- Output: `analysis_outputs/meta_suite_arch_safe_vs_alakline3_top20_confirm_g30_summary.csv`
- Games: `30` per ordered seat and matchup.

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_alakline3` | `0.7851` | `0.7700` | `0.8262` |
| `arch_safe` | `0.8018` | `0.7917` | `0.8238` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_alakline3` | `49 / 60` | `48 / 60` | `32 / 60` | `50 / 60` | `56 / 60` | `58 / 60` | `54 / 60` |
| `arch_safe` | `51 / 60` | `54 / 60` | `29 / 60` | `40 / 60` | `57 / 60` | `59 / 60` | `56 / 60` |

Current practical read:

- Do not pivot to Marnie or Starmie just because those decks appear near the top. Deck power matters, but local policy quality matters just as much.
- `arch_safe` regained a small edge in the newest top20/Starmie-heavy confirmation, while `arch_alakline3` still has prior evidence for better Alakazam handling and better Ogerpon in this run.
- Keep both Archaludon archives ready:
  - Conservative / Starmie-heavy: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`
  - Alakazam-aware public-sample: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz`
- The next high-value improvement is not another blind deck pivot. It is either:
  - improving local Marnie policy until it stops collapsing into Archaludon/Ogerpon, or
  - using real submitted battle logs to decide whether `arch_safe` or `arch_alakline3` matches the live queue better.

## Iteration 2026-07-04: Targeted Rule Probes After Top20 Recheck

Latest public episode data check:

- Refreshed the public episode index on 2026-07-04.
- The Kaggle public daily episode index still ended at `2026-07-02`.
- Re-downloading `latest` therefore returned the same 20 files in `data/episodes/2026-07-02-sample`.
- Continue using `analysis_outputs/episode_decks_2026_07_02_sample_20` and `public_sample_2026_07_02_top20` as the current public replay proxy.

Trace review:

- Generated focused trace summaries for current `arch_safe` losses:
  - `analysis_outputs/trace_summary_arch_safe_vs_archaludon_g30.csv`
  - `analysis_outputs/trace_summary_archaludon_vs_arch_safe_g30.csv`
  - `analysis_outputs/trace_summary_arch_safe_vs_ogerpon_g30.csv`
  - `analysis_outputs/trace_summary_ogerpon_vs_arch_safe_g30.csv`
- Archaludon mirror losses often end with our board empty while an opposing `Archaludon ex` remains.
- Ogerpon losses often involve `Cornerstone Mask Ogerpon ex` forcing the non-ex `Archaludon` plan, while `Okidogi` or evolved side attackers keep pressure up.

Rejected Ogerpon threat Boss probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_ogerthreatboss`
- Idea:
  - In Ogerpon games, change Boss target priority from `Binacle` first to real attackers first: `Barbaracle`, then `Okidogi`, then support Pokemon.
- Focused output: `analysis_outputs/meta_suite_arch_safe_ogerthreat_oger_g100_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `138 / 200` |
| `ogerthreat` | `133 / 200` |

Decision:

- Reject `ogerthreat`.
- Pulling bigger attackers is too slow when non-ex `Archaludon` only hits `120`; the previous tendency to take killable small targets was better.

Rejected Ogerpon killable-only Boss probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_ogerbosskillable`
- Idea:
  - When `Cornerstone Mask Ogerpon ex` is Active, only use `Boss's Orders` if a benched non-Cornerstone target is KO-able by the planned attack route.
  - Otherwise keep attacking Cornerstone directly instead of spending Boss on a non-KO pivot.
- Focused Ogerpon output: `analysis_outputs/meta_suite_arch_safe_ogerbosskillable_oger_g100_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `144 / 200` |
| `ogerbosskillable` | `147 / 200` |

Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_ogerbosskillable_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.7796` | `0.7775` | `0.8071` |
| `ogerbosskillable` | `0.7757` | `0.6875` | `0.7750` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `35 / 40` | `34 / 40` | `16 / 40` | `26 / 40` | `37 / 40` | `39 / 40` | `39 / 40` |
| `ogerbosskillable` | `38 / 40` | `33 / 40` | `13 / 40` | `25 / 40` | `35 / 40` | `39 / 40` | `34 / 40` |

Decision:

- Reject `ogerbosskillable`.
- The focused gain was small and did not reproduce in the broad check; the Starmie-heavy and equal-bucket summaries became worse.
- The rule is Ogerpon-gated, so non-Ogerpon movement is mostly simulator variance, but the target bucket itself also failed the broad confirmation.

Rejected delayed Alakazam third-line probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_late`
- Idea:
  - Keep the Alakazam third Duraludon / Archaludon ex line search, but trigger it only after at least two opposing Alakazam-line Pokemon are visible.
  - This tests whether the original `alakline3` rule was over-searching too early.
- Focused output: `analysis_outputs/meta_suite_arch_alaklate_alak_g100_summary.csv`

| Candidate | Alakazam |
| --- | ---: |
| `arch_safe` | `163 / 200` |
| `alakline3` | `164 / 200` |
| `alaklate` | `162 / 200` |

Decision:

- Reject `alaklate`.
- Delaying the third-line search removed the small focused edge of the original `alakline3` rule.

Current decision:

- No new rule from this iteration is promoted.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the conservative current candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the Alakazam-aware fallback; its newest focused Alakazam edge was only `+1 / 200`, so the conservative archive remains easier to justify without real submitted battle logs.

## Iteration 2026-07-04: Narrow Boss Rule Backchecks

Reason:

- The remaining local losses for the conservative Archaludon candidate are concentrated in Archaludon mirrors and Ogerpon.
- Previous broad Ogerpon Boss restrictions were too heavy, so this pass tested a narrower rule that only avoids Boss when the active Cornerstone Ogerpon is already KO-able.
- The Archaludon mirror Relicanth Boss shortcut was also backchecked by removing it, to confirm whether the current shortcut still earns its slot.

Rejected Ogerpon active-KO Boss skip:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_ogerskipactiveko`
- Idea:
  - If `Cornerstone Mask Ogerpon ex` is Active and the planned attack route already KOs it, save `Boss's Orders`.
  - Otherwise keep the current behavior of using Boss to bypass Cornerstone when a non-Cornerstone bench target exists.
- Focused Ogerpon output: `analysis_outputs/meta_suite_arch_safe_ogerskipactiveko_oger_g80_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `112 / 160` |
| `ogerskipactiveko` | `114 / 160` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_ogerskipactiveko_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.7908` | `0.8075` | `0.8250` |
| `ogerskipactiveko` | `0.7895` | `0.7575` | `0.8179` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `33 / 40` | `33 / 40` | `24 / 40` | `27 / 40` | `38 / 40` | `39 / 40` | `37 / 40` |
| `ogerskipactiveko` | `34 / 40` | `32 / 40` | `23 / 40` | `28 / 40` | `38 / 40` | `40 / 40` | `34 / 40` |

Decision:

- Reject `ogerskipactiveko` as the promoted candidate.
- The Ogerpon improvement reproduced but was very small (`+2 / 160` focused, `+1 / 40` broad).
- Since Ogerpon is only a weight-4 bucket in the latest top20 proxy, this is not enough to offset the weaker scenario summaries.

Rejected Archaludon no-Relicanth-shortcut backcheck:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_norelicshortcut`
- Idea:
  - Remove the mirror-specific `Boss's Orders` shortcut for KO-able opposing `Relicanth`.
  - Let the normal Boss target scoring handle Relicanth instead.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_norelicshortcut_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `88 / 160` |
| `norelicshortcut` | `80 / 160` |

Decision:

- Reject `norelicshortcut`.
- The current safe Relicanth Boss shortcut still improves the mirror; removing it lowered the focused mirror score by `8 / 160`.

Current decision:

- No new rule from this pass is promoted.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the conservative current candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the Alakazam-aware fallback.

## Iteration 2026-07-04: Scored Trace Review and Resource Probes

Tooling:

- Added optional scored decision traces to `tools/run_local_battle.py`.
- When run with `--trace-scores`, each trace row now includes top scored options, selected option flags, scores, and rule reasons if the agent exposes `score_option()`.
- `tools/ptcg_common.py` now attaches the loaded module and agent directory to the callable wrapper so the tracer can score options without modifying submission agents.
- Compatibility smoke check through `tools/run_meta_suite.py` passed:
  - `analysis_outputs/tool_smoke_trace_scores_compat_summary.csv`

Scored trace review:

- Generated scored traces:
  - `analysis_outputs/scored_traces_arch_safe_vs_ogerpon_g3`
  - `analysis_outputs/scored_traces_arch_safe_vs_archaludon_g3`
- In the Archaludon mirror loss, the trace showed a concrete resource issue:
  - Opponent had benched `Relicanth`.
  - Our active could not KO the opposing active `Archaludon ex`.
  - We played `Ultra Ball` first and discarded a `Boss's Orders`, even though the current mirror rule wants Boss for KO-able `Relicanth`.

Rejected mirror Boss-preserve discard probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_keepbossrelic`
- Idea:
  - In Archaludon mirrors, if the active is not KO-able but opposing benched `Relicanth` is KO-able, do not discard `Boss's Orders`.
  - This tests preserving the existing Relicanth Boss shortcut without raising Boss play priority above normal setup.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_keepbossrelic_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `67 / 160` |
| `keepbossrelic` | `80 / 160` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_keepbossrelic_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.8079` | `0.7600` | `0.8143` |
| `keepbossrelic` | `0.7283` | `0.6725` | `0.7429` |

Decision:

- Reject `keepbossrelic`.
- The focused mirror gain did not survive broad confirmation. The rule also made the Archaludon bucket worse in the broad check (`14 / 40` to `11 / 40`), suggesting the preserved Boss can still clog discard choices or delay more important resources.

Rejected active-KO Lillie probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_lillieactiveko`
- Idea:
  - Current rule suppresses `Lillie's Determination` whenever `Boss's Orders` is in hand and an attacker is ready.
  - Relax that only when the active opponent is already KO-able, our hand is small (`<= 4`), and deck count is safe (`>= 12`).
- Focused Archaludon/Ogerpon/Starmie screen: `analysis_outputs/meta_suite_arch_safe_lillieactiveko_probe_g40_summary.csv`

| Candidate | Archaludon | Ogerpon | Starmie |
| --- | ---: | ---: | ---: |
| `arch_safe` | `34 / 80` | `50 / 80` | `69 / 80` |
| `lillieactiveko` | `36 / 80` | `52 / 80` | `74 / 80` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_lillieactiveko_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.8454` | `0.7400` | `0.8429` |
| `lillieactiveko` | `0.7829` | `0.7150` | `0.8000` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `36 / 40` | `36 / 40` | `23 / 40` | `34 / 40` | `36 / 40` | `40 / 40` | `31 / 40` |
| `lillieactiveko` | `36 / 40` | `33 / 40` | `15 / 40` | `30 / 40` | `36 / 40` | `39 / 40` | `35 / 40` |

Decision:

- Reject `lillieactiveko`.
- The focused screen looked promising, especially into Starmie, but broad confirmation lost too much Alakazam, Archaludon, Ogerpon, and Hop equity.

Current decision:

- No new rule from this pass is promoted.
- The scored-trace tooling is useful and should remain for future loss reviews.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the conservative current candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the Alakazam-aware fallback.

## Iteration 2026-07-04: Cornerstone Retreat Probe

Motivation:

- Ogerpon scored traces showed losses where `Archaludon ex` was Active into active `Cornerstone Mask Ogerpon ex`.
- `Metal Defender` is blocked there, and the existing retreat route can still see the Active `Archaludon ex` as an attack-ready Pokemon, so it does not necessarily retreat to a non-Ability attacker.
- This probe tested a narrow player-quality rule: do not keep attacking into a blocker; retreat the blocked Ability attacker only when a benched non-Ability `Archaludon` or `Duraludon` can attack.

Rejected Ogerpon blocked-ex retreat probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_ogerretreatblockedex`
- Idea:
  - When Ogerpon is detected, opposing Active is `117`, our Active is `Archaludon ex`, retreat is legal, and a benched `Archaludon` or `Duraludon` has an attack route, raise Retreat priority.
  - In the follow-up `TO_ACTIVE` selection, prefer the same attack-ready non-Ability target.
- Smoke check completed with `action_errors: 0`.
- Focused Ogerpon output: `analysis_outputs/meta_suite_arch_safe_ogerretreat_oger_g80_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `101 / 160` |
| `ogerretreat` | `106 / 160` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_ogerretreat_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.7632` | `0.7425` | `0.8107` |
| `ogerretreat` | `0.7829` | `0.7375` | `0.8000` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `32 / 40` | `31 / 40` | `20 / 40` | `31 / 40` | `39 / 40` | `39 / 40` | `35 / 40` |
| `ogerretreat` | `34 / 40` | `34 / 40` | `19 / 40` | `27 / 40` | `37 / 40` | `39 / 40` | `34 / 40` |

- The g20 broad check contradicted the g80 focused Ogerpon signal, so the Ogerpon bucket was rerun at higher sample size.
- Expanded Ogerpon output: `analysis_outputs/meta_suite_arch_safe_ogerretreat_oger_g160_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `236 / 320` |
| `ogerretreat` | `214 / 320` |

Decision:

- Reject `ogerretreat`.
- The initial focused gain was not stable. With more Ogerpon games, the rule clearly worsened the matchup.
- The likely cause is that retreating spends too much attached energy and gives up the high-HP `Archaludon ex` body too early, even when the current attack is blocked.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: Mirror Resource Discipline Probes

Motivation:

- Archaludon mirror remains the weakest stable bucket for the conservative candidate.
- Loss summaries repeatedly show `Duraludon` / `Archaludon ex` lines going to discard and the board emptying before the final prize exchange.
- Previous third-line search, Relicanth Boss, and Boss-preserve probes did not survive confirmation, so this pass tested two narrower play-discipline rules.

Rejected mirror low-hand Lillie probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archlillielowhand`
- Idea:
  - In Archaludon mirrors only, if hand count is `<= 4` and deck count is `>= 12`, allow `Lillie's Determination` before the existing "save Lillie when Boss is in hand and attacker is ready" suppression.
  - This tests whether rebuilding the line is more important than preserving Boss in low-resource mirror turns.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archlillie_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `77 / 160` |
| `archlillie` | `74 / 160` |

Decision:

- Reject `archlillie`.
- The extra draw timing worsened the focused mirror result. It likely breaks Boss / attack tempo more often than it repairs the line.

Rejected mirror endgame bench-liability probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archendbenchguard`
- Idea:
  - In Archaludon mirrors only, when the opponent has `<= 1` prize left, our Active is `Archaludon ex` with HP `> 220`, and we already have a bench, avoid playing extra `Duraludon` or `Relicanth`.
  - This tests a late-game "do not create a Boss target" rule.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archendbench_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `79 / 160` |
| `archendbench` | `82 / 160` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_archendbench_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.7842` | `0.7675` | `0.8214` |
| `archendbench` | `0.8046` | `0.7025` | `0.7964` |

Bucket detail:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Lucario | Hop | Starmie |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_safe` | `35 / 40` | `31 / 40` | `20 / 40` | `30 / 40` | `37 / 40` | `40 / 40` | `37 / 40` |
| `archendbench` | `36 / 40` | `36 / 40` | `18 / 40` | `26 / 40` | `37 / 40` | `39 / 40` | `31 / 40` |

Decision:

- Reject `archendbench`.
- The focused mirror gain was too small and did not reproduce in the broad Archaludon cell.
- The Starmie-heavy scenario dropped sharply. Because the rule is mirror-gated, non-mirror bucket movement is mostly stochastic, but the intended Archaludon cell also fell in confirmation.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: Mirror Attack Selection Probes

Motivation:

- The current attack score mostly ranks attacks by visible damage.
- In Archaludon mirrors, `Relicanth` can let `Archaludon ex` use `Raging Hammer`.
- A natural play rule is to avoid overusing `Raging Hammer` when `Metal Defender` already takes the KO, preserving the default main attack line.

Rejected unsafe Metal Defender KO preference:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archprefermdko`
- Idea:
  - In Archaludon mirrors, if our Active is `Archaludon ex`, selected attack is `Raging Hammer`, and raw `Metal Defender` damage can KO the opposing Active, lower `Raging Hammer` below `Metal Defender`.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archprefermd_arch_g100_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `85 / 200` |
| `archprefermd` | `99 / 200` |

- Broad confirmation g20 output: `analysis_outputs/meta_suite_arch_safe_archprefermd_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_safe` | `0.8072` | `0.7325` | `0.8179` |
| `archprefermd` | `0.7789` | `0.8025` | `0.8071` |

- Broad confirmation g30 output: `analysis_outputs/meta_suite_arch_safe_archprefermd_confirm_g30_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets | Archaludon |
| --- | ---: | ---: | ---: | ---: |
| `arch_safe` | `0.8215` | `0.7983` | `0.8333` | `37 / 60` |
| `archprefermd` | `0.8197` | `0.7417` | `0.8262` | `24 / 60` |

Decision:

- Reject `archprefermd`.
- The focused gain did not reproduce. The rule also ignored `Full Metal Lab` damage reduction, so it could prefer `Metal Defender` in spots where raw `220` looked like a KO but the actual damage could be `190`.

Rejected FML-aware safe Metal Defender KO preference:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archprefermdkosafe`
- Idea:
  - Same as above, but only prefer `Metal Defender` if it still KOs after applying `Full Metal Lab` reduction to Metal targets.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archmdsafe_arch_g100_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `95 / 200` |
| `archmdsafe` | `90 / 200` |

Decision:

- Reject `archmdsafe`.
- The safer condition improved one ordered seat but hurt the reverse order more. `Raging Hammer` overkill appears to be less harmful than the extra attack restriction in this local mirror.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: FML-Aware Boss KO Probe

Motivation:

- The failed Metal Defender preference probe exposed a real modeling issue: many local KO estimates use raw `effective_damage()` and do not subtract `Full Metal Lab` damage reduction.
- Even if attack selection should not be restricted, Boss decisions may still be wrong if the agent thinks the opposing Active is KO-able when `Full Metal Lab` makes it survive.
- This probe only changes Boss / target-selection KO estimates, not attack scoring.

Rejected FML-aware Boss KO estimate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archfmlbossko`
- Idea:
  - Add `estimated_attack_damage_to()` and `planned_attack_kos()` helpers.
  - If `Full Metal Lab` is in play and the target is a Metal Pokemon (`Duraludon`, `Archaludon`, or `Archaludon ex`), subtract `30` from estimated damage.
  - Use the FML-aware KO helper in Boss play priority and Boss target scoring.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archfmlboss_arch_g100_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `92 / 200` |
| `archfmlboss` | `96 / 200` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_archfmlboss_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets | Archaludon |
| --- | ---: | ---: | ---: | ---: |
| `arch_safe` | `0.7605` | `0.7000` | `0.7786` | `14 / 40` |
| `archfmlboss` | `0.7421` | `0.6900` | `0.7786` | `14 / 40` |

Decision:

- Reject `archfmlboss`.
- The focused Archaludon gain was small and did not reproduce in the broad Archaludon cell.
- The FML-aware estimate is more semantically accurate, but the changed Boss choices did not improve local outcomes enough to justify promotion.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: FML-Aware Ice Cream Guard

Motivation:

- `should_skip_ice_cream()` has a narrow guard that avoids `Jumbo Ice Cream` when healing would lose a `Raging Hammer` KO.
- That guard also used raw `effective_damage()` and ignored `Full Metal Lab` damage reduction.
- This probe tested whether making only that recovery decision FML-aware improves the Archaludon mirror.

Rejected FML-aware Ice Cream guard:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archfmliceguard`
- Idea:
  - Add `ice_guard_damage_to()` for the `Jumbo Ice Cream` Raging Hammer guard.
  - If `Full Metal Lab` is in play and the target is a Metal Pokemon, subtract `30` from the estimated damage.
  - Leave Boss scoring and attack scoring unchanged.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archfmlice_arch_g100_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `103 / 200` |
| `archfmlice` | `96 / 200` |

Decision:

- Reject `archfmlice`.
- The FML-aware guard appears to stop healing too often in local mirrors.
- Since the focused mirror result was clearly worse, no broad confirmation was run.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: Delay FML When It Loses Active KO

Motivation:

- `Full Metal Lab` is valuable defensively, but in Archaludon mirrors it can also reduce our outgoing damage into opposing Metal Pokemon.
- A plausible play rule is to avoid playing `Full Metal Lab` before attacking if doing so turns a current Active KO into a non-KO.
- This is a timing rule, not a deck-slot change; previous FML3/FML4 slot checks are separate evidence.

Rejected delayed-FML KO-preservation probe:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archdelayfmlko`
- Idea:
  - In Archaludon mirrors only, if `Full Metal Lab` is not already in play and playing it would reduce a planned Active KO below the opponent Active's remaining HP, lower FML play priority.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archdelayfml_arch_g100_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `91 / 200` |
| `archdelayfml` | `85 / 200` |

Decision:

- Reject `archdelayfml`.
- Preserving the immediate KO did not outperform the existing durability-first FML timing in local mirrors.
- Since the focused mirror result was worse, no broad confirmation was run.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: Mirror Low-Deck Explorer Discipline

Motivation:

- Some Archaludon mirror losses go very long and end with our deck near `0`.
- The current hard rule only suppresses `Explorer's Guidance` at deck count `<= 10`.
- Loss summaries showed games where `Explorer's Guidance` was still played repeatedly before the deck became critically low.

Rejected mirror low-deck Explorer suppression:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_archexplorer15`
- Idea:
  - In Archaludon mirrors only, if deck count is `<= 15` and a planned Archaludon attack is already available, suppress `Explorer's Guidance`.
  - This tests attacking with the current board instead of spending more deck resources in late mirrors.
- Smoke check completed with `action_errors: 0`.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_archexplorer15_arch_g100_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `91 / 200` |
| `archexplorer15` | `95 / 200` |

- Broad confirmation output: `analysis_outputs/meta_suite_arch_safe_archexplorer15_confirm_g20_summary.csv`

| Candidate | Public sample top20 | Starmie-heavy discussion | Equal buckets | Archaludon |
| --- | ---: | ---: | ---: | ---: |
| `arch_safe` | `0.7921` | `0.7500` | `0.8036` | `14 / 40` |
| `archexplorer15` | `0.7882` | `0.7300` | `0.7964` | `19 / 40` |

- Expanded Archaludon output: `analysis_outputs/meta_suite_arch_safe_archexplorer15_arch_g200_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `181 / 400` |
| `archexplorer15` | `177 / 400` |

Decision:

- Reject `archexplorer15`.
- The smaller Archaludon checks looked promising, but the larger Archaludon run reversed the signal.
- The late Explorer plays are a visible symptom, but suppressing them at `<= 15` appears to cost too much setup or recovery tempo.
- Keep `arch_safe` as the conservative current candidate.

## Iteration 2026-07-04: Evaluation Seeding Audit

Motivation:

- Several narrow rule probes looked good in 40-200 game checks but reversed in larger checks.
- `tools/run_meta_suite.py --fair-seeds` reuses the same game-id schedule across candidates, but earlier notes already warned that the local engine is not explicitly seeded by `game_id`.
- Reducing evaluation noise would make rule iteration more reliable.

Tooling change:

- Added `--seed-base` to `tools/run_local_battle.py`.
  - When set, each game records `seed = seed_base + game_index`.
  - Python's global `random` and loaded agent-module `random` objects are seeded with that value.
- Added `--seed-base` passthrough to `tools/run_meta_suite.py`.
  - The optional per-game CSV now includes a `seed` column.
- Syntax check passed:
  - `py -3.11 -m py_compile tools\run_local_battle.py tools\run_meta_suite.py tools\ptcg_common.py`

Smoke checks:

- Seeded local battle:
  - `py -3.11 tools\run_local_battle.py --agent-a ...arch_safe --agent-b meta_agents\archaludon_public --games 1 --seed-base 4242`
  - Completed with `action_errors: 0` and recorded `seed: 4242`.
- Seeded meta-suite smoke:
  - `analysis_outputs/smoke_seeded_meta_suite_summary.csv`
  - `analysis_outputs/smoke_seeded_meta_suite_games.csv`

Determinism check:

- Re-ran the same seeded 2-game Archaludon smoke into:
  - `analysis_outputs/smoke_seeded_meta_suite_summary_2.csv`
  - `analysis_outputs/smoke_seeded_meta_suite_games_2.csv`
- The game results and hashes did not match the first run.

Conclusion:

- Python-side randomness is now controlled and recorded, but the underlying `cg` engine still appears to use non-seeded internal randomness for shuffle / game initialization.
- Treat `--seed-base` as useful metadata and protection against agent fallback randomness, not as a guarantee of deterministic replays.
- Promotion decisions should continue to require larger focused reruns and broad confirmation; 40-game and 160-game signals can still be misleading.

## Iteration 2026-07-04: Public Meta Refresh and Chandelure Bucket

Motivation:

- The latest public episode index still only exposes data through `2026-07-02`.
- The previous classification had two `unknown` decks in the 2026-07-02 public sample.
- The user asked to avoid losing on deck power, so the visible top-side deck families should be explicitly classified and represented in local evaluation.

Refresh:

- Downloaded a fresh `latest` sample into `data/episodes_refresh_2026_07_04/2026-07-02-sample`.
- Output confirmed `pokemon-tcg-ai-battle-episodes-2026-07-02`; no newer public daily dataset was available from the index.
- Re-extracted deck families into `analysis_outputs/episode_decks_refresh_2026_07_04_latest_sample_19_v2`.

Updated visible public sample classification:

| Archetype | Decks |
| --- | ---: |
| `marnie_grimmsnarl` | 11 |
| `alakazam_psychic` | 10 |
| `archaludon_metal` | 6 |
| `ogerpon_toolbox` | 4 |
| `mega_lucario` | 2 |
| `hop_trevenant` | 2 |
| `chandelure_psychic_control` | 2 |
| `starmie_froslass` | 1 |

Added tooling / local meta opponent:

- Added `chandelure_psychic_control` markers to `tools/extract_episode_decks.py` using public replay IDs `{97, 98, 164, 494}`.
- Added `meta_agents/chandelure_psychic_control_simple`.
  - Deck list comes from the refreshed public replay sample.
  - Agent is a simple Psychic-control mimic: set up Litwick / Chandelure, use Comfey and disruption cards, and score `Mind Ruler` approximately from opponent hand size.
- Added `chandelure` to `tools/run_meta_suite.py`.
- Added `chandelure: 2` to both `public_sample_2026_07_02` and `public_sample_2026_07_02_top20` scenario weights.
- Smoke check:
  - `analysis_outputs/smoke_arch_safe_vs_chandelure_summary.csv`
  - Completed with `action_errors: 0`.

## Iteration 2026-07-04: Ogerpon Promote and Backup Bench Probes

Rejected Ogerpon non-ex promotion priority:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_ogerpromote`
- Idea:
  - In Ogerpon games where `Cornerstone Mask Ogerpon ex` is visible, promote non-ex `Archaludon` / `Duraludon` over `Cinderace`.
  - This came from scored traces where `Cinderace` was promoted into a Cornerstone board and did no useful damage.
- Focused Ogerpon output: `analysis_outputs/meta_suite_arch_safe_ogerpromote_oger_g80_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `arch_safe` | `117 / 160` |
| `ogerpromote` | `105 / 160` |

Decision:

- Reject `ogerpromote`.
- The local trace symptom was real, but forcing Cinderace down removed too much pivot value.

Rejected emergency backup bench rule:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_backupbench`
- Idea:
  - If our bench is empty and Active is inside the opponent's estimated maximum damage, bench a Pokemon before items / draw.
  - This tested a basic PTCG principle: do not lose immediately to no Active.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_safe_backupbench_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_safe` | `90 / 160` |
| `backupbench` | `74 / 160` |

Decision:

- Reject `backupbench`.
- The rule looked strategically sensible, but in this engine / deck it disrupted tempo and worsened the mirror.

## Iteration 2026-07-04: Candidate Recheck With Chandelure Bucket

Compared:

- Conservative candidate: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe`
- Alakazam-aware candidate: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3`

Important implementation note:

- `arch_alakline3` only changes:
  - `need_duraludon()`
  - `need_archaludon()`
- The change is gated on `detect_matchup(obs) == "alakazam"`, and asks for a third Duraludon / Archaludon ex line after Alakazam-family cards are visible.
- Differences outside Alakazam-like games should therefore be treated mostly as local engine noise.

Outputs:

- `analysis_outputs/meta_suite_arch_safe_vs_alakline3_plus_chandelure_g30_summary.csv`
- `analysis_outputs/meta_suite_arch_safe_vs_alakline3_plus_chandelure_g40_summary.csv`

`g40` summary:

| Candidate | Public sample | Public top20 | Starmie-heavy | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `arch_safe` | `0.7579` | `0.7612` | `0.7087` | `0.7891` |
| `arch_alakline3` | `0.7668` | `0.7706` | `0.7175` | `0.7875` |

Combined `g30 + g40` bucket rates:

| Bucket | `arch_safe` | `arch_alakline3` |
| --- | ---: | ---: |
| Marnie | `117 / 140` | `123 / 140` |
| Alakazam | `117 / 140` | `118 / 140` |
| Archaludon | `65 / 140` | `59 / 140` |
| Ogerpon | `88 / 140` | `101 / 140` |
| Lucario | `132 / 140` | `125 / 140` |
| Hop | `137 / 140` | `134 / 140` |
| Starmie | `120 / 140` | `120 / 140` |
| Chandelure | `115 / 140` | `116 / 140` |

Combined public-sample weighted estimate:

| Candidate | Combined public sample |
| --- | ---: |
| `arch_safe` | `0.7682` |
| `arch_alakline3` | `0.7821` |

Current decision:

- Promote `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the current public-sample candidate.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz` as the conservative fallback if live submitted logs show an Archaludon-mirror-heavy queue.
- Do not promote either rejected micro-rule.

## Iteration 2026-07-04: Alakline3 Mirror Sequencing Probes

Context:

- Current public-sample candidate is `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3`.
- The weakest local bucket is still Archaludon mirror.
- Prior broad checks already rejected global "choose first", setup benching, non-ex mirror attacker, low-hand Lillie, end-bench guards, Metal Defender preference, FML timing, and low-deck Explorer suppression.

Rejected emergency Ultra Ball backup search:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_ubbench`
- Idea:
  - In late / vulnerable no-bench states, raise `Ultra Ball` priority from the existing low `bench empty` score to search a backup Pokemon before Boss / attack.
  - This came from scored traces where the agent had `Ultra Ball`, no bench, and then lost by board wipe.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_alakline3_ubbench_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_alakline3` | `79 / 160` |
| `ubbench` | `70 / 160` |

Seat split:

| Ordered pair | Candidate wins |
| --- | ---: |
| `arch_alakline3` vs Archaludon | `37 / 80` |
| Archaludon vs `arch_alakline3` | `42 / 80` |
| `ubbench` vs Archaludon | `43 / 80` |
| Archaludon vs `ubbench` | `27 / 80` |

Decision:

- Reject `ubbench`.
- It improved one ordered seat but collapsed the reverse seat, suggesting the extra Ultra Ball urgency spends too many resources when going second.

Rejected no-bench mirror one-prize Boss suppression:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_noboss1pempty`
- Idea:
  - In Archaludon mirrors only, if we have no bench, cannot KO the opposing Active, and Boss can only take a non-lethal one-prize bench KO, save Boss instead.
  - This targeted traces where taking a benched Duraludon left the opposing Archaludon ex intact and our board empty.
- Focused Archaludon output: `analysis_outputs/meta_suite_arch_alakline3_noboss1p_arch_g80_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `arch_alakline3` | `82 / 160` |
| `noboss1pempty` | `74 / 160` |

Decision:

- Reject `noboss1pempty`.
- The local trace symptom was real, but one-prize Boss turns are still necessary often enough that suppressing them hurts the mirror.

Current decision:

- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the current public-sample candidate.
- Keep the conservative `arch_safe` archive as a fallback for live logs that are heavily Archaludon-mirror weighted.
- No new play-rule candidate from this pass is promoted.

## Iteration 2026-07-04: Visible Top Deck Imitation Recheck

Browser / public-source observations:

- Kaggle Leaderboard on 2026-07-04 showed the current visible top rows as `tonakaiiii`, `kazuki0123`, `Yushin Ito`, `渡邊征央`, `Akira-Ninth`, and other high-1100 / low-1200 score teams.
- Clicking the first row's public episode control added `submissionId=54198810&episodeId=83634460` to the Leaderboard URL, but the external visualizer did not return a directly usable replay page for that ID from local HTTP.
- The public top episode index still ended at `pokemon-tcg-ai-battle-episodes-2026-07-02`; no newer daily dataset was available from the manifest refresh.
- Reclassifying the latest downloaded 2026-07-02 sample gave:

| Archetype | Decks |
| --- | ---: |
| `marnie_grimmsnarl` | 11 |
| `alakazam_psychic` | 10 |
| `archaludon_metal` | 6 |
| `ogerpon_toolbox` | 4 |
| `mega_lucario` | 2 |
| `hop_trevenant` | 2 |
| `chandelure_psychic_control` | 2 |
| `starmie_froslass` | 1 |

Discussion `716207` takeaways:

- The post argues that `Cornerstone Mask Ogerpon ex` is a strong counter to Ability-reliant Archaludon, but pure Ogerpon is too slow or too fragile into Starmie and Lucario.
- The suggested direction is a Teal Mask / Energy Switch toolbox that moves Grass acceleration into matchup-specific attackers.
- Attached public CSVs were downloaded to `data/public_decks/discussion_716207`.
- The attached lists fall into these rough families:
  - Ogerpon multi-mask disruption.
  - Cornerstone Ogerpon wall with Shedinja / Sylveon style support.
  - Teal Mask Ogerpon plus Meganium / Forest of Vitality grass evolution.
  - Hydrapple / Sinistcha grass evolution shells.
  - Raging Bolt / Kangaskhan / Energy Switch multi-type toolbox.

Top-copy candidate screen:

- Output:
  - `analysis_outputs/meta_suite_topcopy_vs_arch_g20_summary.csv`
  - `analysis_outputs/meta_suite_topcopy_vs_arch_g20_results.csv`
- Games: `20` per ordered seat, `--fair-seeds`.

| Candidate | Public sample | Starmie-heavy | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_alakline3` | `0.7908` | `0.7600` | `0.8250` |
| `great_tusk_starmierush` | `0.8118` | `0.5025` | `0.7500` |
| `marnie_kazuki_xerosic1` | `0.5382` | `0.4050` | `0.5938` |
| `marnie_tonakaiiii` | `0.5289` | `0.4100` | `0.5750` |

Important bucket results:

| Candidate | Marnie | Alakazam | Archaludon | Ogerpon | Starmie | Chandelure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `arch_alakline3` | `35 / 40` | `30 / 40` | `23 / 40` | `31 / 40` | `35 / 40` | `32 / 40` |
| `great_tusk_starmierush` | `32 / 40` | `38 / 40` | `25 / 40` | `36 / 40` | `10 / 40` | `27 / 40` |
| `marnie_kazuki_xerosic1` | `25 / 40` | `23 / 40` | `7 / 40` | `10 / 40` | `19 / 40` | `39 / 40` |
| `marnie_tonakaiiii` | `21 / 40` | `27 / 40` | `5 / 40` | `15 / 40` | `19 / 40` | `36 / 40` |

Interpretation:

- The top visible names and 2026-07-02 public sample support Marnie / Alakazam / Archaludon / Ogerpon as the main visible families.
- Directly copying our local Marnie variants is not enough. Their local policies collapse into Archaludon and Ogerpon, so top Marnie strength is likely not deck list alone.
- Great Tusk remains the best low-Starmie public-sample imitation branch, but it is structurally weak into Starmie.
- Archaludon remains the safer all-weather branch because it does not collapse into the Starmie-heavy scenario.

Great Tusk Starmie fallback check:

- Output:
  - `analysis_outputs/meta_suite_gt_variants_starmie_g60_summary.csv`
  - `analysis_outputs/meta_suite_arch_vs_gt_nogiant_g20_summary.csv`

Focused Starmie:

| Candidate | Starmie |
| --- | ---: |
| `gt_cutterr` | `39 / 120` |
| `gt_nogiant` | `49 / 120` |
| `arch_alakline3` | `107 / 120` |

Full `gt_nogiant` recheck:

| Candidate | Public sample | Starmie-heavy | Equal buckets |
| --- | ---: | ---: | ---: |
| `arch_alakline3` | `0.7868` | `0.6625` | `0.7938` |
| `gt_nogiant` | `0.7888` | `0.5275` | `0.7375` |

Current decision:

- Do not switch to the local Marnie copies as-is.
- Keep `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3.tar.gz` as the safest general candidate.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie.tar.gz` as the low-Starmie / public-sample imitation candidate.
- Keep `submission_great_tusk_crustle_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr.tar.gz` only as a more aggressive public-sample branch; its latest Starmie focused check was weaker than `gt_nogiant`.
- If live submitted logs show many Starmie-style losses, do not use Great Tusk. Stay on Archaludon.

## 2026-07-04 Chandelure rule pass

Goal: convert a visible strong-player idea into a narrow rule. Chandelure's Mind Ruler scales with our hand size, and recent local Chandelure losses were mostly from either taking a large hand-size hit or decking out while trying to dig through the control game.

Changes tested:

- Detect Chandelure from `Litwick` / `Chandelure` / `Lampent` public IDs: `{97, 98, 494}`.
- Versus Chandelure, prioritize `Lillie's Determination` when our hand is at least 7 cards, lowering our hand back toward 6.
- Versus Chandelure, stop using `Explorer's Guidance` once our deck is at 25 cards or fewer.

Focused Chandelure checks:

| Candidate | Chandelure |
| --- | ---: |
| `arch_alakline3` | `130 / 160` |
| `chand7` | `145 / 160` |
| `chand8` | `134 / 160` |
| `chand9` | `140 / 160` |
| `chand7_deck25` | `153 / 160` |
| `chand7_deck30` | `151 / 160` |

Trace check:

- Output: `analysis_outputs/trace_scores_chandlillie7_vs_chandelure_a`
- `Chandelure: Lillie lowers Mind Ruler damage` appeared as a scored candidate 97 times and was selected 33 times in 20 traced games.
- Remaining traced losses were deck-out losses, which motivated the Chandelure-only Explorer stop at deck count `<= 25`.

Broad check:

- Output:
  - `analysis_outputs/meta_suite_arch_chandlillie7_deck25_broad_g30_summary.csv`
  - `analysis_outputs/meta_suite_arch_chandlillie7_deck25_broad_g30_results.csv`
- Result: Chandelure bucket improved from `45 / 60` to `54 / 60`; equal-public-buckets improved from `0.8313` to `0.8396`.
- The weighted public sample moved down in this run because non-Chandelure buckets varied despite no intended behavior change in those buckets. Treat this as local stochastic noise unless repeated live logs show a regression.

Current decision:

- Adopt `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25` as the next Archaludon-family candidate for local testing.
- Keep the previous `arch_alakline3` archive as the conservative fallback until more broad or live evidence accumulates.

## 2026-07-04 Public Ogerpon deck imitation pass

User submitted the current candidate and reported that it reached the bronze-medal range. Treat that as useful live evidence that the Archaludon-family direction is viable.

Public Discussion `716207` CSVs were classified into these rough families:

- `Raging_Bolt_Ogerpon.csv` / `Clefairy_Ogerpon.csv`: Teal Mask Ogerpon, Energy Switch, Area Zero, Mega Kangaskhan / Raging Bolt toolbox.
- `Cornerstone_Mask_Ogerpon.csv`: Cornerstone Mask Ogerpon wall with Nincada / Ninjask / Shedinja and Sylveon support.
- `Ogerpon_Meganium*.csv`, `Hydrapple_Ogerpon.csv`, `Sinistcha_Ogerpon.csv`: Teal Mask Ogerpon plus grass evolution engines.
- `Ogerpon.csv`: multi-mask disruption shell.

Added local meta opponents:

- `meta_agents/ogerpon_raging_bolt_public_simple`
  - Deck source: `data/public_decks/discussion_716207/Raging_Bolt_Ogerpon.csv`
  - Local smoke: error-free.
- `meta_agents/ogerpon_cornerstone_public_simple`
  - Deck source: `data/public_decks/discussion_716207/Cornerstone_Mask_Ogerpon.csv`
  - Local smoke: error-free.

Updated `tools/run_meta_suite.py`:

- Added buckets `ogerpon_raging_bolt` and `ogerpon_cornerstone`.
- Added scenario `discussion_ogerpon_toolbox_2026_07_04`.

Focused checks:

| Candidate | Raging Bolt Ogerpon | Cornerstone Ogerpon |
| --- | ---: | ---: |
| `arch_alakline3` | `117 / 120` | `95 / 120` |
| `chand7_deck25` | `118 / 120` | `94 / 120` |

Cornerstone follow-up:

- Idea: add a third non-ex `Archaludon` (`840`) by cutting one `Jumbo Ice Cream` (`1147`).
- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_corner8403`
- Result: `corner8403` dropped to `115 / 160` against Cornerstone, while `chand7_deck25` was `130 / 160`.
- Decision: reject `corner8403`. The extra non-ex body did not compensate for losing one healing card.

Updated broad check with new buckets:

- Output: `analysis_outputs/meta_suite_updated_buckets_arch_vs_chand_g20_summary.csv`

| Candidate | Public sample | Starmie-heavy | Ogerpon-toolbox scenario | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `arch_alakline3` | `0.7757` | `0.7875` | `0.7769` | `0.8100` |
| `chand7_deck25` | `0.7164` | `0.7425` | `0.7404` | `0.7975` |

Interpretation:

- The Chandelure-specific branch remains causally scoped: Chandelure IDs `{97, 98, 494}` only appear in the Chandelure meta deck.
- Non-Chandelure movement in broad runs is likely local stochastic variance rather than a direct implementation effect.
- Live Kaggle result reaching bronze is stronger evidence than one broad local run, but live match logs should decide whether to keep the Chandelure branch or fall back to `arch_alakline3`.

## 2026-07-04 Archaludon mirror Relicanth Boss priority

Live note:

- User submitted `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25`.
- It reached the bronze-medal range, so treat this branch as the current live baseline.

Hypothesis:

- In Archaludon mirror, opposing `Relicanth` enables damage-counter style attacks without evolving.
- The existing mirror rule already found KO-able opposing Relicanth, but its score was `15500`, below normal `Explorer's Guidance` at `16000`.
- Raising this score to `19000` lets the agent use Boss before spending the supporter on Explorer when Relicanth can be removed.

Change:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_mirrorrelicboss19`
- One-line change: `Boss: remove mirror Relicanth` score `15500 -> 19000`.

Focused Archaludon mirror checks:

| Seed base | Baseline | `mirrorrelicboss19` |
| --- | ---: | ---: |
| `default` | `63 / 160` | `81 / 160` |
| `9700` | `79 / 160` | `80 / 160` |
| `13700` | `74 / 160` | `81 / 160` |
| Total | `216 / 480` | `242 / 480` |

Broad spot check:

- Output: `analysis_outputs/meta_suite_mirrorrelicboss19_broad_g20_summary.csv`
- Equal public buckets were `0.8200` baseline vs `0.8150` for `mirrorrelicboss19`.
- The changed branch is scoped to detected Archaludon matchup. Non-Archaludon bucket movement in this small broad check is treated as noise unless repeated live logs show the same regression.

Current decision:

- Adopt `mirrorrelicboss19` as the next local candidate, not as an immediate live replacement until submission limits allow.
- Keep the bronze-reaching `chand7_deck25` archive as the known live baseline.

## 2026-07-04 Ogerpon Active-KO Boss Skip Recheck

Goal:

- Recheck the earlier Ogerpon-only idea on top of the current `chand7_deck25_mirrorrelicboss19` branch.
- Rule: if `Cornerstone Mask Ogerpon ex` is Active and our planned attack already KOs it, save `Boss's Orders` instead of pulling a benched non-Cornerstone target.

Directory:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_mirrorrelicboss19_ogerskipactiveko`

Focused Ogerpon-family check:

- Output: `analysis_outputs/meta_suite_mirror19_ogerskip_oger3_g60_summary.csv`

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon |
| --- | ---: | ---: | ---: |
| `mirrorrelicboss19` | `70 / 120` | `118 / 120` | `90 / 120` |
| `oger_skip_active_ko` | `72 / 120` | `118 / 120` | `90 / 120` |

Expanded normal Ogerpon check:

- Output: `analysis_outputs/meta_suite_mirror19_ogerskip_oger_g120_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `mirrorrelicboss19` | `163 / 240` |
| `oger_skip_active_ko` | `164 / 240` |

Decision:

- Reject as a promoted candidate.
- The rule is strategically sensible and appears narrow, but the measured gain is only `+1 / 240` in the expanded check. That is not enough to justify replacing the cleaner `mirrorrelicboss19` next-candidate archive.

## 2026-07-04 Alakazam Xerosic Probe After MirrorRelicBoss19

Motivation:

- Current broad scan still showed Alakazam below the very strong buckets, and weighted public samples give Alakazam a large share.
- Scored loss traces showed Alakazam wins coming from very large hand-size `Powerful Hand` damage and our board eventually running out of Active Pokemon.
- Since `Powerful Hand` scales from the Alakazam player's hand, the plausible direct answer was hand disruption rather than more healing.

Candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_mirrorrelicboss19_xerosic1_cutlillie`
- Deck change: `-1 Lillie's Determination (1227)`, `+1 Xerosic's Machinations (1197)`.
- Rule change:
  - Play `Xerosic's Machinations` at high priority versus Alakazam when opponent hand count is at least `12`.
  - Preserve / take Xerosic versus Alakazam when opponent hand count is high.

Focused Alakazam output:

- `analysis_outputs/meta_suite_mirror19_xerosic1_alak_g80_summary.csv`

| Candidate | Alakazam |
| --- | ---: |
| `mirrorrelicboss19` | `141 / 160` |
| `xerosic1_cutlillie` | `139 / 160` |

Decision:

- Reject `xerosic1_cutlillie`.
- The hand-disruption idea is strategically coherent, but cutting a draw supporter and spending the supporter turn on Xerosic did not improve the local Alakazam result.

## 2026-07-04 Submitted Baseline vs MirrorRelicBoss19 Broad Recheck

Purpose:

- Recheck whether `mirrorrelicboss19` should replace the submitted bronze-reaching `chand7_deck25` branch as the general next submission, not only as an Archaludon mirror patch.

Output:

- `analysis_outputs/meta_suite_submitted_vs_mirror19_broad_g20_seed71000_summary.csv`

| Candidate | Public sample | Starmie-heavy | Ogerpon toolbox | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `0.7974` | `0.7225` | `0.7635` | `0.8350` |
| `mirrorrelicboss19` | `0.7711` | `0.7700` | `0.7615` | `0.8250` |

Key bucket cells:

| Candidate | Alakazam | Archaludon | Ogerpon | Starmie | Cornerstone Ogerpon |
| --- | ---: | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `37 / 40` | `10 / 40` | `32 / 40` | `37 / 40` | `29 / 40` |
| `mirrorrelicboss19` | `34 / 40` | `15 / 40` | `28 / 40` | `39 / 40` | `31 / 40` |

Interpretation:

- `mirrorrelicboss19` keeps reproducing an Archaludon-mirror edge, and it also raises the Starmie-heavy proxy in this run because that proxy contains Archaludon weight.
- The one-line behavior change is gated by `detect_matchup(obs) == "archaludon"`, so non-Archaludon bucket differences are mostly local simulator variance unless repeated live logs show the same movement.
- The submitted `chand7_deck25` branch remains the known live broad baseline because it already reached bronze range.

Current submission stance:

- Keep submitted `chand7_deck25` as the safest known live baseline.
- Keep `mirrorrelicboss19.tar.gz` as the next candidate when live losses or visible queue feel Archaludon / Starmie-heavy.
- Do not replace the live baseline solely from this broad recheck.

## 2026-07-04 Relicanth Boss Priority Score Sweep

Goal:

- Test whether a lower Relicanth Boss priority can keep the intended Archaludon mirror benefit with less risk than `19000`.
- All variants start from the submitted `chand7_deck25` branch and only change the `Boss: remove mirror Relicanth` score.

Candidates:

- `boss155`: submitted baseline, score `15500`.
- `boss170`: score `17000`.
- `boss180`: score `18000`.
- `boss190`: score `19000`.

Focused Archaludon output:

- `analysis_outputs/meta_suite_relicboss_scores_arch_g80_seed81000_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `boss155` | `84 / 160` |
| `boss170` | `77 / 160` |
| `boss180` | `64 / 160` |
| `boss190` | `75 / 160` |

Decision:

- Reject `boss170` and `boss180`.
- The earlier `boss190` improvement did not reproduce in this sweep. Treat `mirrorrelicboss19` as a conditional, live-log-driven pivot rather than a clean local promotion.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Cornerstone Boss Target Priority Probe

Goal:

- Check whether the new public Cornerstone Ogerpon proxy should prefer evolved threat targets over low-HP basics when using `Boss's Orders`.
- This was motivated by loss traces where the current rule often pulled `Nincada` or `Eevee` while `Ninjask`, `Shedinja`, or `Sylveon` were available.

Candidate:

- `cornerboss_threat`: start from submitted `chand7_deck25`.
- In Ogerpon-targeting Boss scoring, raise priorities for `Ninjask (713)`, `Shedinja (748)`, `Sylveon (134)`, and `Nincada (712)` ahead of the older generic Ogerpon side-target ordering.

Focused Cornerstone output:

- `analysis_outputs/meta_suite_cornerboss_threat_cornerstone_g80_summary.csv`

| Candidate | Cornerstone Ogerpon |
| --- | ---: |
| `submitted_chand7_deck25` | `124 / 160` |
| `cornerboss_threat` | `116 / 160` |

Decision:

- Reject `cornerboss_threat`.
- The local engine preferred the existing behavior, which often takes the lowest-HP reachable target rather than spending Boss on evolved support threats.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Archaludon Mirror 3-Line Search Probe

Goal:

- Test whether pure Archaludon mirror improves by searching a third `Duraludon / Archaludon ex` line, similar to the existing Alakazam-specific rule.
- This targets games where the first two ex attackers are traded off and the deck needs a clean rebuild.

Candidate:

- `mirrorline3`: start from submitted `chand7_deck25`.
- For `detect_matchup(obs) == "archaludon"`, make `need_duraludon()` and `need_archaludon()` target three total ex lines instead of two.

Focused Archaludon output:

- `analysis_outputs/meta_suite_mirrorline3_arch_g80_seed95000_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `submitted_chand7_deck25` | `75 / 160` |
| `mirrorline3` | `69 / 160` |

Decision:

- Reject `mirrorline3`.
- The extra third-line search appears to cost more tempo than it gains in the mirror.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Chandelure Explorer Threshold Probe

Goal:

- Test whether the Chandelure-specific `Explorer's Guidance` stop can be relaxed from deck count `<= 25` to `<= 20`.
- The idea was to allow more setup before the deck-out guard starts, while still avoiding the late Chandelure control loss pattern.

Candidate:

- `chand7_deck20`: start from submitted `chand7_deck25`.
- Only change the Chandelure-specific Explorer stop threshold from `25` to `20`.

Focused Chandelure output:

- `analysis_outputs/meta_suite_chanddeck20_chandelure_g80_seed97000_summary.csv`

| Candidate | Chandelure |
| --- | ---: |
| `chand7_deck25` | `146 / 160` |
| `chand7_deck20` | `139 / 160` |

Seat split:

| Ordered pair | Candidate wins |
| --- | ---: |
| `chand7_deck25` vs Chandelure | `73 / 80` |
| Chandelure vs `chand7_deck25` | `73 / 80` |
| `chand7_deck20` vs Chandelure | `73 / 80` |
| Chandelure vs `chand7_deck20` | `66 / 80` |

Decision:

- Reject `chand7_deck20`.
- The current `deck25` threshold remains better, especially when Chandelure is the first-listed agent in the ordered seat.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Archaludon Mirror Bench 1-Metal Evolution Probe

Goal:

- Test whether Archaludon mirror improves by evolving a benched `Duraludon` with only one Metal Energy in discard when a current Archaludon attack is already available.
- The idea was to start a backup `Archaludon ex` line earlier instead of waiting for two Metal Energy in discard.

Candidate:

- `mirrorbench1alloy`: start from submitted `chand7_deck25`.
- In `score_evolve()`, if `detect_matchup(obs) == "archaludon"`, target is benched `Duraludon`, one Metal is in discard, and a planned Archaludon attack exists, score the evolution at `9000`.

Focused Archaludon output:

- `analysis_outputs/meta_suite_mirrorbench1alloy_arch_g80_seed98000_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `submitted_chand7_deck25` | `80 / 160` |
| `mirrorbench1alloy` | `66 / 160` |

Seat split:

| Ordered pair | Candidate wins |
| --- | ---: |
| `submitted_chand7_deck25` vs Archaludon | `40 / 80` |
| Archaludon vs `submitted_chand7_deck25` | `40 / 80` |
| `mirrorbench1alloy` vs Archaludon | `36 / 80` |
| Archaludon vs `mirrorbench1alloy` | `30 / 80` |

Decision:

- Reject `mirrorbench1alloy`.
- Spending the one available discard Metal on a partial bench evolution costs more than the earlier backup body gains.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Cornerstone Early Detection Probe

Goal:

- Improve the public Cornerstone Ogerpon proxy by detecting the deck before `Cornerstone Mask Ogerpon ex (117)` itself is visible.
- The current `OGERPON_LINE` only detects older Ogerpon toolbox markers: `{116, 117, 1051, 1052, 1256}`.
- The public Cornerstone list often shows `Nincada`, `Ninjask`, `Shedinja`, `Eevee`, or `Sylveon` first, so the agent may delay taking/searching the non-ex `Archaludon` answer.

Candidates:

- `cornerdetect`: add `Sylveon (134)`, `Nincada (712)`, `Ninjask (713)`, and `Shedinja (748)` to `OGERPON_LINE`.
- `cornerdetect_ninja`: safer variant that only adds `Nincada (712)`, `Ninjask (713)`, and `Shedinja (748)`.

Focused Cornerstone outputs:

- `analysis_outputs/meta_suite_cornerdetect_cornerstone_g80_seed99000_summary.csv`
- `analysis_outputs/meta_suite_cornerdetect_cornerstone_g160_seed101000_summary.csv`
- `analysis_outputs/meta_suite_cornerdetect_ninja_cornerstone_g80_seed104000_summary.csv`

| Run | `submitted_chand7_deck25` | `cornerdetect` | `cornerdetect_ninja` |
| --- | ---: | ---: | ---: |
| `g80 seed99000` | `115 / 160` | `126 / 160` | - |
| `g160 seed101000` | `249 / 320` | `257 / 320` | - |
| `g80 seed104000` | `128 / 160` | `125 / 160` | `121 / 160` |
| Combined comparable | `492 / 640` | `508 / 640` | - |

Ogerpon-family spot check:

- `analysis_outputs/meta_suite_cornerdetect_oger3_g60_seed100000_summary.csv`

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Ogerpon-toolbox scenario |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `82 / 120` | `120 / 120` | `96 / 120` | `0.8630` |
| `cornerdetect` | `79 / 120` | `116 / 120` | `99 / 120` | `0.8509` |

Broad spot check:

- `analysis_outputs/meta_suite_cornerdetect_broad_g20_seed102000_summary.csv`

| Candidate | Public sample | Starmie-heavy | Ogerpon toolbox | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `0.8441` | `0.7300` | `0.8288` | `0.8625` |
| `cornerdetect` | `0.8217` | `0.7800` | `0.8058` | `0.8525` |

Decision:

- Keep submitted `chand7_deck25` as the safest known live baseline.
- Keep packaged `cornerdetect` as a conditional Cornerstone/Shedinja/Sylveon-tech candidate, not a clean broad replacement.
- Reject `cornerdetect_ninja`; the safer detection set did not preserve the Cornerstone signal.
- Created archive:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_cornerdetect.tar.gz`
- Smoke check:
  - `analysis_outputs/smoke_cornerdetect_summary.jsonl`
  - `action_errors: 0`

## 2026-07-04 Explorer Hero's Cape Wait Probe

Goal:

- Test whether `Explorer's Guidance` is over-prioritizing `Hero's Cape` when no `Archaludon ex` is currently available to hold it.
- Baseline scores `Explorer: Hero's Cape` at `27000` with an ex target and `22000` without one, which can put Cape above line pieces during setup.

Candidate:

- `capewait`: start from submitted `chand7_deck25`.
- Change the no-target Explorer Cape score from `22000` to `3000`, while keeping the visible `Archaludon ex` target score at `27000`.

Broad outputs:

- `analysis_outputs/meta_suite_capewait_broad_g20_seed105000_summary.csv`
- `analysis_outputs/meta_suite_capewait_broad_g20_seed106000_summary.csv`

First broad spot check:

| Candidate | Public sample | Starmie-heavy | Ogerpon toolbox | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `0.7599` | `0.7400` | `0.7962` | `0.8300` |
| `capewait` | `0.7737` | `0.7250` | `0.7750` | `0.8250` |

Second broad spot check:

| Candidate | Public sample | Starmie-heavy | Ogerpon toolbox | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `0.8289` | `0.8000` | `0.8192` | `0.8625` |
| `capewait` | `0.7724` | `0.7450` | `0.7673` | `0.8150` |

Combined key buckets:

| Candidate | Archaludon | Ogerpon | Alakazam | Chandelure |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `41 / 80` | `57 / 80` | `64 / 80` | `77 / 80` |
| `capewait` | `35 / 80` | `49 / 80` | `64 / 80` | `75 / 80` |

Decision:

- Reject `capewait`.
- The first public-sample improvement did not reproduce, and the repeated damage to Archaludon / Ogerpon is too large for a broad change.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Ogerpon Cape-on-Duraludon Probe

Goal:

- Test whether Ogerpon losses are worsened by attaching `Hero's Cape` to `Duraludon`.
- Scored Ogerpon loss traces showed repeated `promote Duraludon` and some `Hero's Cape on Duraludon` actions before board wipe losses.

Candidate:

- `ogernocapedura`: start from submitted `chand7_deck25`.
- In Ogerpon matchups only, suppress `Hero's Cape` attachment to `Duraludon`.

Focused normal Ogerpon output:

- `analysis_outputs/meta_suite_ogernocapedura_oger_g80_seed108000_summary.csv`

| Candidate | Ogerpon |
| --- | ---: |
| `submitted_chand7_deck25` | `102 / 160` |
| `ogernocapedura` | `103 / 160` |

Ogerpon-family output:

- `analysis_outputs/meta_suite_ogernocapedura_oger3_g60_seed109000_summary.csv`

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Ogerpon-toolbox scenario |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `87 / 120` | `118 / 120` | `86 / 120` | `0.8370` |
| `ogernocapedura` | `70 / 120` | `116 / 120` | `105 / 120` | `0.8509` |

Decision:

- Reject `ogernocapedura` as a broad or normal-Ogerpon candidate.
- The rule appears to improve Cornerstone but badly hurts the normal Ogerpon proxy.
- If live logs are specifically Cornerstone-heavy, prefer the cleaner `cornerdetect` branch rather than this Cape restriction.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Ogerpon Second Non-Ex Archaludon Search Probe

Goal:

- Test whether Ogerpon games improve by searching the second in-deck non-ex `Archaludon (840)` after Ogerpon is known.
- Loss traces often showed repeated `Duraludon` promotion after the non-ex answer was removed, suggesting a possible need to find the second copy.

Candidate:

- `ogernonex2search`: start from submitted `chand7_deck25`.
- Change `need_nonex_archaludon()` so that in Ogerpon matchups it stays true while `count_in_play(obs, ARCHALUDON) < 2`.

Ogerpon-family output:

- `analysis_outputs/meta_suite_ogernonex2search_oger3_g60_seed110000_summary.csv`

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Ogerpon-toolbox scenario |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `93 / 120` | `118 / 120` | `99 / 120` | `0.8843` |
| `ogernonex2search` | `72 / 120` | `118 / 120` | `85 / 120` | `0.8065` |

Decision:

- Reject `ogernonex2search`.
- The visible symptom was real, but actively searching the second non-ex Archaludon costs too much tempo and worsens both normal Ogerpon and Cornerstone.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Duraludon Raging Hammer Evolution Guard Probe

Goal:

- Test whether the agent should avoid evolving Active `Duraludon` into `Archaludon ex` when `Duraludon`'s current `Raging Hammer` would KO the opposing Active but `Metal Defender` would not.
- This targets a possible attack-route loss from evolving out of a damage-scaling attack.

Candidate:

- `evolveguardrh`: start from submitted `chand7_deck25`.
- In `score_evolve()`, suppress Active `Duraludon -> Archaludon ex` only when `Raging Hammer` is a KO and raw `Metal Defender` is not.

Focused Archaludon output:

- `analysis_outputs/meta_suite_evolveguardrh_arch_g80_seed111000_summary.csv`

| Candidate | Archaludon |
| --- | ---: |
| `submitted_chand7_deck25` | `79 / 160` |
| `evolveguardrh` | `77 / 160` |

Decision:

- Reject `evolveguardrh`.
- The natural-looking Raging Hammer preservation rule did not improve the mirror; evolving remains better often enough that the restriction is not worth keeping.
- Keep submitted `chand7_deck25` as the broad baseline.

## 2026-07-04 Ogerpon Active-Cornerstone Evolution Probe

Goal:

- Test whether the Ogerpon rule was too conservative by blocking `Duraludon -> Archaludon ex` whenever `Cornerstone Mask Ogerpon ex (117)` was seen anywhere.
- The new rule blocks `Archaludon ex` evolution only when the opposing Active is currently `Cornerstone Mask Ogerpon ex`.

Candidates:

- `ogerexactive`: active-Cornerstone-only block, keeping the original Ogerpon marker set.
- `ogerexactive_cornerdetect`: combines `ogerexactive` with the earlier `cornerdetect` marker expansion for `Sylveon`, `Nincada`, `Ninjask`, and `Shedinja`.

Focused Ogerpon-family outputs:

- `analysis_outputs/meta_suite_ogerexactive_oger3_g60_seed112000_summary.csv`
- `analysis_outputs/meta_suite_ogerexactive_oger3_g80_seed113000_summary.csv`
- `analysis_outputs/meta_suite_ogerexactive_cornerdetect_oger3_g60_seed114000_summary.csv`
- `analysis_outputs/meta_suite_ogerexactive_cornerdetect_oger3_g80_seed116000_summary.csv`

Comparable combined Ogerpon-family totals for `ogerexactive` vs `ogerexactive_cornerdetect`:

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Equal Ogerpon-family |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `192 / 280` | `274 / 280` | `207 / 280` | `673 / 840` |
| `ogerexactive` | `203 / 280` | `269 / 280` | `215 / 280` | `687 / 840` |
| `ogerexactive_cornerdetect` | `194 / 280` | `271 / 280` | `223 / 280` | `688 / 840` |

Broad spot check:

- `analysis_outputs/meta_suite_ogerexactive_broad_g20_seed115000_summary.csv`

| Candidate | Public sample | Starmie-heavy | Ogerpon toolbox | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `submitted_chand7_deck25` | `0.8086` | `0.7075` | `0.7885` | `0.8325` |
| `ogerexactive` | `0.8151` | `0.7700` | `0.8038` | `0.8475` |
| `ogerexactive_cornerdetect` | `0.8191` | `0.8250` | `0.8077` | `0.8525` |

Decision:

- Keep `ogerexactive_cornerdetect` as the next local submission candidate when live logs suggest Cornerstone/Shedinja/Sylveon or broad Ogerpon-toolbox pressure.
- Keep `ogerexactive` as the safer normal-Ogerpon variant because it scored better against the normal Ogerpon proxy.
- Both candidates improved over `submitted_chand7_deck25` in the combined focused Ogerpon-family check.
- Created archives:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive.tar.gz`
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect.tar.gz`
- Extracted package smoke check for `ogerexactive_cornerdetect` completed with `action_errors: 0`:
  - `analysis_outputs/package_smoke_ogerexactive_cornerdetect_summary.csv`

## 2026-07-04 Archaludon Next Candidate vs Great Tusk Branch Check

Goal:

- After the submitted Archaludon candidate reached the bronze range, check whether switching decks to an existing Great Tusk branch is locally justified.
- Compare the new Archaludon next candidate against the two retained Great Tusk public-like branches.

Output:

- `analysis_outputs/meta_suite_archnext_vs_gt_g10_seed118000_summary.csv`

| Candidate | Public sample | Starmie-heavy | Ogerpon toolbox | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `arch_next` | `0.8039` | `0.7550` | `0.8192` | `0.8550` |
| `gt_nogiant` | `0.8092` | `0.4800` | `0.7154` | `0.7600` |
| `gt_cutterr` | `0.8434` | `0.5650` | `0.7192` | `0.7550` |

Bucket details:

| Candidate | Archaludon | Starmie | Ogerpon Cornerstone |
| --- | ---: | ---: | ---: |
| `arch_next` | `10 / 20` | `17 / 20` | `16 / 20` |
| `gt_nogiant` | `11 / 20` | `5 / 20` | `10 / 20` |
| `gt_cutterr` | `15 / 20` | `6 / 20` | `10 / 20` |

Decision:

- Do not switch broadly from Archaludon to Great Tusk yet.
- `gt_cutterr` is attractive only if the real queue is very close to the public-sample weighting and low on Starmie / Cornerstone Ogerpon.
- For a broad or uncertain queue, keep `arch_next` as the safer next candidate because it preserves Starmie and Ogerpon-toolbox coverage.

## 2026-07-04 Kaggle Submitted `archbossrelic_safe` History Check

Live submission page:

- Submission: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`
- Kaggle public score shown: `923.2`
- Visible replay preview: `episode-83627960-replay.json`
- Replay header showed `TeamNames: ["rurumi", "rurumi"]` and `rewards: [1, -1]`, so the visible replay is a same-team / self-style game and by itself is not enough to classify public-field losses.
- The in-browser replay preview was truncated, and browser-side download continued no further due browser policy. If full `Replay` and `Agent 0/1 Logs` files are downloaded manually, parse those before making a live-log-specific rule change.

Local proxy diagnosis for the same submitted branch:

- Main output: `analysis_outputs/meta_suite_arch_safe_vs_alakline3_recheck_g40_summary.csv`
- Game rows: `analysis_outputs/meta_suite_arch_safe_vs_alakline3_recheck_g40_games.csv`

Loss-only proxy summary for `arch_safe`:

| Opponent bucket | Losses | Empty own Active | Opponent prize 0 | Notes |
| --- | ---: | ---: | ---: | --- |
| Archaludon | `44 / 80` | `44` | `28` | Primary failure. Usually ends with opposing `Archaludon ex (190)` active and our board wiped. |
| Ogerpon | `30 / 80` | `22` | `4` | Mostly `Cornerstone Mask Ogerpon ex (117)` or Ogerpon toolbox board states; not simply prize race. |
| Alakazam | `15 / 80` | `14` | `7` | Ends to `Alakazam (743)` after our Archaludon chain collapses or hand-size damage catches up. |
| Starmie | `14 / 80` | `14` | `4` | Fast board-wipe losses to `Starmie ex (1031)`. |
| Marnie | `9 / 80` | `9` | `1` | Lower priority than Archaludon / Ogerpon; many losses are early board wipe. |

Decision:

- Yes, submitted battle history is the right next signal, but the visible Kaggle replay is only a same-team sample and the full replay/log download was not available through browser automation.
- Based on local proxy losses, do not chase generic draw or benching rules; many such probes already hurt tempo.
- The highest-value next live-log checks are:
  - If real losses are mostly `Archaludon ex (190)`: use the Archaludon-mirror branches such as `mirrorrelicboss19` only when the live field is mirror-heavy.
  - If real losses show `Cornerstone Mask Ogerpon ex (117)` / Shedinja / Sylveon: prefer the later Ogerpon-detection and active-Cornerstone evolution rules (`ogerexactive_cornerdetect` line).
  - If the visible loss is self-play only, treat it as weak evidence and keep using local proxy buckets until more full replay/log files are available.

Follow-up direct comparison:

- `analysis_outputs/meta_suite_live_safe_vs_archnext_key_g20_seed119000_summary.csv`
- Compared the live submitted `arch_safe` branch with the current `arch_next` branch on the buckets most relevant to the proxy loss diagnosis: Archaludon, Ogerpon, Cornerstone Ogerpon, Alakazam, and Starmie.

| Candidate | Alakazam | Archaludon | Ogerpon | Starmie | Cornerstone Ogerpon |
| --- | ---: | ---: | ---: | ---: | ---: |
| `live_arch_safe` | `34 / 40` | `17 / 40` | `25 / 40` | `33 / 40` | `32 / 40` |
| `arch_next` | `36 / 40` | `20 / 40` | `26 / 40` | `35 / 40` | `35 / 40` |

Scenario rollups from the same restricted key-bucket comparison:

| Candidate | Starmie-heavy | Ogerpon toolbox | Equal key buckets |
| --- | ---: | ---: | ---: |
| `live_arch_safe` | `0.7100` | `0.6861` | `0.7050` |
| `arch_next` | `0.7675` | `0.7444` | `0.7600` |

Decision:

- The current `arch_next` candidate is a coherent replacement direction for the submitted `arch_safe` branch if the live history continues to show the same weak buckets.
- It improves every bucket checked in this focused comparison, so no new rule should be added on top before we see a stronger live-log contradiction.

## 2026-07-04 `arch_next` Diagnostic and Ogerpon Retreat Probe

Goal:

- Continue improving the current best `arch_next` branch rather than the already-submitted `arch_safe` branch.
- Recheck remaining weak buckets, then test whether blocked `Archaludon ex` should retreat to an already-powered non-ex `Archaludon` against `Cornerstone Mask Ogerpon ex`.

Current `arch_next` diagnostic:

- Output: `analysis_outputs/meta_suite_archnext_diagnostic_g30_seed120000_summary.csv`

| Bucket | Wins |
| --- | ---: |
| Marnie | `52 / 60` |
| Alakazam | `48 / 60` |
| Archaludon | `34 / 60` |
| Ogerpon | `45 / 60` |
| Lucario | `55 / 60` |
| Hop | `60 / 60` |
| Starmie | `51 / 60` |
| Chandelure | `57 / 60` |
| Raging Bolt Ogerpon | `58 / 60` |
| Cornerstone Ogerpon | `45 / 60` |

Loss-only read:

- Archaludon remains the largest loss bucket, but many mirror-targeted rules have already been rejected.
- Ogerpon / Cornerstone losses often show `Cornerstone Mask Ogerpon ex (117)` Active. Some games have our `Archaludon ex` stuck Active while a powered non-ex `Archaludon` is on Bench.

Rejected Ogerpon retreat probes:

- `ogernonexretreat`: when opposing Active is `117`, our Active is `Archaludon ex`, and a benched non-ex `Archaludon` has at least 3 energy, raise Retreat priority.
- `ogertoolboxretreat`: same retreat rule, but only when Ogerpon-toolbox markers such as `Okidogi` / `Solrock` / `Lunatone` / non-Cornerstone Ogerpon are visible.

Focused Ogerpon-family outputs:

- `analysis_outputs/meta_suite_ogernonexretreat_oger3_g60_seed121000_summary.csv`
- `analysis_outputs/meta_suite_ogertoolboxretreat_oger3_g60_seed122000_summary.csv`

First check:

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Ogerpon toolbox scenario |
| --- | ---: | ---: | ---: | ---: |
| `arch_next` | `81 / 120` | `117 / 120` | `86 / 120` | `0.8222` |
| `ogernonexretreat` | `87 / 120` | `118 / 120` | `77 / 120` | `0.8120` |

Second check:

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Ogerpon toolbox scenario |
| --- | ---: | ---: | ---: | ---: |
| `arch_next` | `89 / 120` | `116 / 120` | `91 / 120` | `0.8472` |
| `ogernonexretreat` | `84 / 120` | `118 / 120` | `90 / 120` | `0.8426` |
| `ogertoolboxretreat` | `88 / 120` | `117 / 120` | `81 / 120` | `0.8213` |

Decision:

- Reject both retreat probes.
- The trace symptom is real, but the retreat rule is still too costly and especially bad for pure Cornerstone.
- Keep `arch_next` as the current best local candidate.

## 2026-07-04 Submitted `arch_safe` Live History Check

Submitted archive checked:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`

Visible Kaggle submission state:

- Status: complete.
- Public score shown on the Submissions page: `909.8`.
- Game History rating panel showed current rating around `905`, with a visible trajectory range of `600 - 986`.

Visible recent results from the Game History panel:

- Wins visible against: `Daniel Casellas`, `kokomi`, `knomura03`, `Fuzoku`, `20070521 assassin`, `OzanM.`, `TakamaruEX`, `Bocchieri Alberto`, `nakayashiki697`, `MooDerEchte`.
- Losses visible against: `noikaret`, `Shunji Minode`, `Rin'z Uznir`, `sam_the_rice_cake`, `rotto`, `Dick Jessen William`, `shg195`, `romthpt`, `anngle`, `wao zhang`, `datnt114`, `Rahul Rathnavel K`.

Concrete replay handle recovered:

- `noikaret` over `rurumi`: `submissionId=54304032`, `episodeId=83661278`.
- Visible result line: `[Win] noikaret 821 (+50)` / `[Loss] rurumi 906 (-6)`.
- Earlier embedded preview showed seed `970205040` and about `150` steps.

Interpretation:

- The visible live losses are not just one isolated mirror loss. They span many opponent accounts in a short window, so live history should be used as a higher-priority signal than the old 2026-07-02 public sample.
- `Dick Jessen William` appears in the existing public sample with a Chandelure / Comfey / Battle Cage style list, so the live queue may include stronger Chandelure-control variants than our local Chandelure mimic.
- Current local diagnostics still show the submitted `arch_safe` branch weak against Archaludon, Ogerpon-family, and Alakazam compared with `arch_next`; live history does not yet contradict promoting `arch_next`.

Limitation:

- The in-app browser could open the embedded Game History and episode IDs, but direct full replay JSON retrieval was blocked by the browser's read-only page scope and Kaggle's XSRF-protected internal API.
- Full card-state analysis should be retried if the episode appears in the public daily episode dataset, or if the external `ptcgvis` POST view can be opened manually and the replay JSON is saved.

### Chandelure Follow-up From Live Losses

Added a second local Chandelure-control bucket:

- `meta_agents/chandelure_psychic_control_dick`
- Source deck shape: public sample linked to `Dick Jessen William`, with heavier `Battle Cage` count than the earlier simple Chandelure mimic.

Focused local outputs:

- `analysis_outputs/meta_suite_chandelure_dick_archsafe_g80_seed123500_summary.csv`
- `analysis_outputs/meta_suite_chandelure_dick_archsafe_g80_seed123500_games.csv`
- `analysis_outputs/meta_suite_chandelure_dick_probe_g80_seed123500_summary.csv`
- `analysis_outputs/meta_suite_chandelure_dick_probe_g80_seed123500_games.csv`

Results:

| Candidate | Chandelure simple | Chandelure Dick-style | Combined |
| --- | ---: | ---: | ---: |
| Submitted `arch_safe` | `134 / 160` | `146 / 160` | `280 / 320` |
| Current `arch_next` | `146 / 160` | `154 / 160` | `300 / 320` |

Loss pattern from trace summaries:

- Submitted `arch_safe`: `25 / 40` local Chandelure-family losses ended with our deck at `0`.
- Current `arch_next`: `15 / 20` local Chandelure-family losses ended with our deck at `0`.
- Most losses had our Active as `Archaludon ex (190)`, with the opponent often hiding behind `Comfey (164)` or a low-prize Chandelure-line Pokemon.

Interpretation:

- The Chandelure-family loss mode is mostly deck-out / failure to close after drawing too aggressively, not a clean prize race loss.
- The current `arch_next` branch already cuts this loss mode substantially through the Chandelure-specific Explorer and Lillie rules.
- A further Chandelure-only anti-deckout rule may help, but this bucket is no longer the biggest local weakness compared with Archaludon mirror, Alakazam, and Ogerpon-family buckets.

## 2026-07-04 Mirror Lethal Boss Search Probe

Goal:

- Test whether Archaludon mirror losses could be reduced by taking `Boss's Orders` from search effects when Boss would immediately pull a benched KO for the final prize.

Candidate:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_mirrorlethalboss`

Change:

- Added `lethal_boss_search_score`.
- Scoped to detected Archaludon mirror.
- Applies only when a planned attack can KO a benched target worth enough prizes to win and the Active KO does not already win.
- Raises `Boss's Orders` priority when selected from `Explorer's Guidance` or generic to-hand search effects.

Focused output:

- `analysis_outputs/meta_suite_mirrorlethalboss_arch_g80_seed124000_summary.csv`

Result:

| Candidate | Archaludon |
| --- | ---: |
| `arch_next` | `78 / 160` |
| `mirrorlethalboss` | `69 / 160` |

Decision:

- Reject.
- The intended endgame Boss pickup likely happens too rarely, or the higher Boss selection disrupts setup/draw sequencing more than it helps.
- Keep `arch_next` as the current best local candidate.

## 2026-07-04 Chandelure Low-Deck Lillie Probe

Goal:

- Reduce the remaining Chandelure-family deck-out losses without touching non-Chandelure matchups.

Candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`

Change:

- In detected Chandelure matchups only, if deck count is `<= 8` and hand count is at least `deck + 6`, raise `Lillie's Determination` to `26000`.
- Intended effect: shuffle a large hand back before deck-out while also lowering `Mind Ruler` damage.

Focused outputs:

- `analysis_outputs/meta_suite_chandlowdecklillie_g80_seed125000_summary.csv`
- `analysis_outputs/meta_suite_chandlowdecklillie_g80_seed126000_summary.csv`

Two-seed combined result:

| Candidate | Chandelure simple | Chandelure Dick-style | Combined |
| --- | ---: | ---: | ---: |
| `arch_next` | `301 / 320` | `307 / 320` | `608 / 640` |
| `chandlowdecklillie` | `306 / 320` | `306 / 320` | `612 / 640` |

Decision:

- Tentatively adopt `chandlowdecklillie` as the local next candidate because the rule is Chandelure-gated and improves the two Chandelure-control buckets in aggregate.
- The gain is small, so do not submit only for this change unless live history continues to show Chandelure-control losses or submission limits are otherwise available.

## 2026-07-04 Alakazam Emergency Backup Probe After Chandlowdecklillie

Goal:

- Reduce Alakazam losses where our Active is KO'd by `Alakazam ex (743)` and the board collapses with no backup Pokemon.

Candidate:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_alakbackup`

Change:

- Add `need_alakazam_backup_bench()`.
- In detected Alakazam matchups only, if our bench is empty and Active HP is inside the estimated Alakazam damage ceiling:
  - Raise hand-played `Duraludon` to `26000`.
  - Allow `Ultra Ball` despite the normal empty-bench suppression when there are at least two safe discards.

Focused output:

- `analysis_outputs/meta_suite_alakbackup_chandlow_alak_g80_seed127000_summary.csv`

Result:

| Candidate | Alakazam |
| --- | ---: |
| `chandlowdecklillie` | `135 / 160` |
| `alakbackup` | `134 / 160` |

Decision:

- Reject.
- The final no-bench loss count did not improve, so the targeted backup rule either triggers too late or disrupts tempo when it does trigger.
- Keep `chandlowdecklillie` as the current local next candidate.

## 2026-07-04 Ogerpon Non-Ex Energy Priority Probe After Chandlowdecklillie

Goal:

- Improve Ogerpon / Cornerstone games by charging the non-ex `Archaludon (840)` route more deliberately after `Cornerstone Mask Ogerpon ex (117)` is visible.

Candidate:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_ogerenergy840`

Change:

- In detected Ogerpon matchups, if `117` is visible:
  - Add `+5000` to Metal attach score for non-ex `Archaludon`.
  - Add `+4000` to Metal attach score for `Duraludon` when no non-ex `Archaludon` is in play.

Focused outputs:

- `analysis_outputs/meta_suite_ogerenergy840_oger3_g60_seed128000_summary.csv`
- `analysis_outputs/meta_suite_ogerenergy840_oger3_g60_seed129000_summary.csv`

Two-seed combined result:

| Candidate | Ogerpon | Raging Bolt Ogerpon | Cornerstone Ogerpon | Combined |
| --- | ---: | ---: | ---: | ---: |
| `chandlowdecklillie` | `163 / 240` | `235 / 240` | `192 / 240` | `590 / 720` |
| `ogerenergy840` | `170 / 240` | `228 / 240` | `191 / 240` | `589 / 720` |

Decision:

- Reject.
- Normal Ogerpon improved, but the total Ogerpon-family result did not improve after the second seed.
- Keep `chandlowdecklillie` as the current local next candidate.

## 2026-07-04 Chandlowdecklillie Full Diagnostic

Current local next candidate:

- Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`
- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`

Diagnostic output:

- `analysis_outputs/meta_suite_chandlowdecklillie_diagnostic_g30_seed130000_summary.csv`
- `analysis_outputs/meta_suite_chandlowdecklillie_diagnostic_g30_seed130000_games.csv`

Bucket results:

| Bucket | Result |
| --- | ---: |
| Marnie | `51 / 60` |
| Alakazam | `44 / 60` |
| Archaludon | `29 / 60` |
| Ogerpon | `40 / 60` |
| Lucario | `56 / 60` |
| Hop | `59 / 60` |
| Starmie | `56 / 60` |
| Chandelure | `55 / 60` |
| Chandelure Dick-style | `58 / 60` |
| Raging Bolt Ogerpon | `58 / 60` |
| Cornerstone Ogerpon | `48 / 60` |

Scenario results:

| Scenario | Win rate |
| --- | ---: |
| Public sample | `0.7592` |
| Public sample top20 | `0.7608` |
| Starmie-heavy discussion | `0.7583` |
| Ogerpon-toolbox scenario | `0.7872` |
| Live Chandelure-control | `0.9417` |
| Equal public buckets | `0.8394` |

Next focus:

- Archaludon mirror is still the largest local weakness, but many direct mirror micro-rules have already been rejected.
- Normal Ogerpon remains the next meaningful weakness; however the latest non-ex energy-priority probe did not reproduce.
- Prefer new evidence from live logs or a more faithful Archaludon/Ogerpon proxy before adding another narrow rule.

## 2026-07-04 Archaludon Mirror Promotion Tank Probe

Goal:

- Test whether Archaludon mirror losses are worsened by promoting `Cinderace (666)` over a healthy `Archaludon ex (190)` after a KO.

Candidate:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_archpromotetank`

Change:

- In detected Archaludon mirrors only:
  - If a promotable `Archaludon ex` has HP above the estimated opponent max damage, score it at `17000`.
  - If such a tank is available, lower `Cinderace` promotion from `16000` to `7000`.

Focused output:

- `analysis_outputs/meta_suite_archpromotetank_arch_g80_seed131000_summary.csv`

Result:

| Candidate | Archaludon |
| --- | ---: |
| `chandlowdecklillie` | `77 / 160` |
| `archpromotetank` | `72 / 160` |

Decision:

- Reject.
- The visible Cinderace-promotion symptom was real, but preserving the existing retreat-0 pivot line is better in aggregate.
- Keep `chandlowdecklillie` as the current local next candidate.

## 2026-07-04 Live Submission Loss Review: Safe Archive

Submitted archive:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`
- Kaggle visible score during review: `927.6`
- Submission id observed in URL: `54304032`

Reviewed live losses:

| Opponent | Episode | Seed | Observed loss pattern |
| --- | ---: | ---: | --- |
| `ysakuragi` | `83669966` | `1498953648` | Starmie rush. Mega Starmie ex KO line left us with no bench. |
| `noikaret` | `83661278` | `970205040` | Solrock/Lunatone + Cornerstone Ogerpon + Okidogi/Neutralization. We reached deck `0` with prizes remaining and lost to deckout pressure. |
| `Shunji Minode` | `83660805` | `1641327451` | Marnie's Grimmsnarl ex board with multiple Grimmsnarl/Munkidori. We were pushed out before finishing the prize race. |

Immediate probe 1:

- Candidate: `submission_archaludon_chandlow_ogerlillie`
- Change: extend low-deck Lillie refill priority to Ogerpon/Chandelure/Crustle at deck count `<= 8`, with a generic critical low-deck fallback.
- Output: `analysis_outputs/meta_suite_ogerlillie_key_g80_seed142000_summary.csv`

Result:

| Candidate | Marnie | Ogerpon | Starmie | Chandelure Dick | Cornerstone |
| --- | ---: | ---: | ---: | ---: | ---: |
| `current` | `139 / 160` | `121 / 160` | `143 / 160` | `155 / 160` | `130 / 160` |
| `ogerlillie` | `138 / 160` | `114 / 160` | `147 / 160` | `154 / 160` | `125 / 160` |

Decision:

- Reject.
- It improves Starmie slightly but hurts the live-relevant Ogerpon family too much.

Immediate probe 2:

- Candidate: `submission_archaludon_chandlow_ogercritical_lillie`
- Change: Ogerpon-only Lillie refill priority at deck count `<= 3`, scored below Boss bypass.
- Output: `analysis_outputs/meta_suite_ogercritical_oger_g100_seed143000_summary.csv`

Result:

| Candidate | Ogerpon | Cornerstone |
| --- | ---: | ---: |
| `current` | `143 / 200` | `151 / 200` |
| `critical` | `134 / 200` | `147 / 200` |

Decision:

- Reject.
- Lillie-based deckout prevention still costs too much tempo, especially on the second-player Ogerpon side.
- Keep `chandlowdecklillie` as the current local next candidate.
- Next live-log-driven work should inspect Boss/non-ex Archaludon targeting into Neutralization or Starmie no-bench failures, not broader draw-supporter priority.

## 2026-07-04 Starmie Bench-Out Probes

Context:

- Live loss `ysakuragi` / episode `83669966` showed a Starmie rush line where the board collapsed.
- Local diagnostic Starmie losses included bench-out patterns with only a damaged Duraludon/Archaludon line in play.

Probe 1:

- Candidate: `submission_archaludon_chandlow_starmie_cinderbench`
- Change: vs Starmie only, if our bench is empty, play `Cinderace (666)` as a backup basic.
- Output: `analysis_outputs/meta_suite_starmie_cinderbench_g160_seed145000_summary.csv`

Result:

| Candidate | Starmie |
| --- | ---: |
| `current` | `285 / 320` |
| `cinderbench` | `277 / 320` |

Decision:

- Reject.
- It improved the candidate-first seat slightly (`139 -> 142`) but damaged the candidate-second seat heavily (`146 -> 135`).

Probe 2:

- Candidate: `submission_archaludon_chandlow_starmie_cinderdanger`
- Change: vs Starmie only, bench `Cinderace` only when bench is empty and active HP is `<= 210`.
- Output: `analysis_outputs/meta_suite_starmie_cinderdanger_g160_seed145000_summary.csv`

Result:

| Candidate | Starmie |
| --- | ---: |
| `current` | `279 / 320` |
| `danger` | `277 / 320` |

Decision:

- Reject.
- Narrowing to lethal-range active HP removed the worst second-seat damage but still did not improve the bucket.
- Do not solve Starmie losses by simply benching Cinderace; it creates too many extra liabilities.

## 2026-07-04 Marnie Cinderace Backup Probes

Context:

- Live loss `Shunji Minode` / episode `83660805` showed a Marnie's Grimmsnarl ex board with multiple Grimmsnarl/Munkidori.
- Local Marnie losses often had our Archaludon line knocked out while our bench was empty or nearly empty.
- Existing Archaludon code had no explicit Marnie matchup detection.

Probe 1:

- Candidate: `submission_archaludon_chandlow_marnie_cinderdanger`
- Change:
  - Detect Marnie line ids `646/647/648/649`.
  - In Marnie games only, if our bench is empty and active HP is `<= 180`, play `Cinderace (666)` as a backup basic.
- Focused outputs:
  - `analysis_outputs/meta_suite_marnie_cinderdanger_g160_seed147000_summary.csv`
  - `analysis_outputs/meta_suite_marnie_cinderdanger_g240_seed150000_summary.csv`
- Broad spot checks:
  - `analysis_outputs/meta_suite_marnie_cinderdanger_broad_g60_seed148000_summary.csv`
  - `analysis_outputs/meta_suite_marnie_cinderdanger_broad_g60_seed149000_summary.csv`

Marnie focused / spot-check totals:

| Output | Current | Candidate |
| --- | ---: | ---: |
| `g160_seed147000` | `269 / 320` | `286 / 320` |
| `broad_g60_seed148000` Marnie bucket | `103 / 120` | `106 / 120` |
| `broad_g60_seed149000` Marnie bucket | `100 / 120` | `97 / 120` |
| `g240_seed150000` | `412 / 480` | `415 / 480` |

Decision:

- Initial combined Marnie evidence was positive (`+20 / 1040`), and the rule is Marnie-gated, but the edge was not stable on every seed.
- After the follow-up full-bucket check, reject as a submission candidate.
- The local evaluator has visible run-to-run noise, but the final check moved the target bucket itself in the wrong direction.

Follow-up full-bucket check:

- Output: `analysis_outputs/meta_suite_marnie_cinderdanger_full_g30_seed151000_summary.csv`

| Candidate | Marnie | Public sample | Top20 sample | Equal buckets |
| --- | ---: | ---: | ---: | ---: |
| `current` | `57 / 60` | `0.8154` | `0.8187` | `0.8667` |
| `marniedanger` | `48 / 60` | `0.8044` | `0.8071` | `0.8561` |

Probe 2:

- Candidate: `submission_archaludon_chandlow_marnie_cinderdanger_p0`
- Change: same rule, but only when our player index is `0`.
- Output: `analysis_outputs/meta_suite_marnie_cinderdanger_p0_g240_seed150000_summary.csv`

Result:

| Candidate | Marnie |
| --- | ---: |
| `current` | `423 / 480` |
| `p0` | `418 / 480` |

Decision:

- Reject.
- The p0-only restriction removed too many useful backup cases.

Probe 3:

- Candidate: `submission_archaludon_chandlow_marnie_duracinder`
- Change: same Marnie detection, but only bench `Cinderace` when our bench is empty, active is `Duraludon`, and active HP is `<= 180`.
- Output: `analysis_outputs/repeated_marnie_duracinder_g80r3_summary.csv`
- Evaluated with `tools/run_repeated_meta_suite.py` to reduce native-engine RNG noise.

Result:

| Candidate | Marnie |
| --- | ---: |
| `current` | `414 / 480` |
| `duracinder` | `414 / 480` |

Decision:

- Reject / no effect.
- The short-loss symptom exists, but this narrower Cinderace backup rule does not move the matchup.

## 2026-07-04 Local Evaluator Noise Check

Reason:

- Several probes showed surprising movement in unrelated buckets.
- `run_meta_suite.py --fair-seeds` reuses Python-side `game_id`, but the engine binary itself appears to use native randomness.

Finding:

- `submission_archaludon/cg/libcg.so` contains `std::random_device`, `mt19937`, and `shuffle` symbols/strings.
- The Python wrapper exposes `BattleStart` and `GameInitialize`, but no seed setter.
- Therefore `--seed-base` only controls Python agent tie-break randomness; it does not fully fix engine shuffles.

Identical-candidate check:

- Output: `analysis_outputs/meta_suite_identical_noise_g80_seed160000_summary.csv`
- Compared the same directory under aliases `a` and `b`:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`

| Bucket | Alias `a` | Alias `b` |
| --- | ---: | ---: |
| Marnie | `144 / 160` | `137 / 160` |
| Archaludon | `86 / 160` | `66 / 160` |
| Ogerpon | `114 / 160` | `113 / 160` |
| Starmie | `137 / 160` | `138 / 160` |
| Public sample | `0.7651` | `0.7082` |
| Equal selected buckets | `0.7516` | `0.7094` |

Implication:

- Small local differences are not actionable.
- Do not promote a rule from one batch unless the gain is large, repeats across independent batches, and ideally matches a live-log symptom.
- For Archaludon mirror in particular, even `20 / 160` swings can occur between identical aliases, so mirror probes need much larger samples or live evidence.

Follow-up repeated mirror recheck:

- Candidate: `submission_archaludon_chandlow_mirrorpromotedura`
- Output: `analysis_outputs/repeated_arch_mirrorpromotedura_g80r3_summary.csv`
- Diff output: `analysis_outputs/repeated_arch_mirrorpromotedura_g80r3_diff.csv`

| Candidate | Archaludon |
| --- | ---: |
| `current` | `238 / 480` |
| `mirrorpromotedura` | `248 / 480` |

Decision:

- Do not promote.
- The direction is positive, but the difference is only `+2.09%` with approximate `z = 0.648`, well inside local evaluator noise.

## 2026-07-04 Submitted Safe Archive Live History

Submitted archive:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`
- Kaggle submission id: `54304032`
- Observed public score after more games: `935.3`

Visible live-history note:

- The score is materially above the earlier local / first-live expectation, so this archive is viable.
- The Games list shows many wins, but losses still appear against several strong archetypes / users.
- In the currently loaded visible Games list, the rough parsed count was `36` external wins, `24` external losses, and one `rurumi` vs `rurumi` self-match row.
- Visible loss opponents included: `ysakuragi`, `noikaret`, `Shunji Minode`, `Rin'z Uznir`, `sam_the_rice_cake`, `rotto`, `Dick Jessen William`, `shg195`, `romthpt`, `anngle`, `wao zhang`, `datnt114`, `Rahul Rathnavel K`, `Biel Escola Rodrigo`, `如月メノウ`, `cimyzzz`, `tototo`, `yq line`, `tsukammo`, `Joe Chapa`, `Hamachi`, `kemurayama`, `PokeBotty`, `RyuMizu`.
- Representative losses already inspected:
  - `ysakuragi`, episode `83669966`, seed `1498953648`: Starmie rush. Final board showed Mega Starmie ex pressure with Cinderace support; our side was losing tempo / board presence.
  - `noikaret`, episode `83661278`, seed `970205040`: Solrock/Lunatone + Cornerstone Ogerpon + Okidogi / Neutralization style pressure. Loss pattern looked like control and deck-out pressure.
  - `Shunji Minode`, episode `83660805`, seed `1641327451`: Marnie's Grimmsnarl ex + Munkidori board. Loss pattern looked like pressure from an established multi-attacker board.

Interpretation:

- Live losses are not one single bug. They currently cluster into:
  - fast Starmie setup / bench pressure,
  - Ogerpon or non-ex control / wall pressure,
  - Marnie Grimmsnarl style midrange pressure.
- This supports using live replay symptoms as the source of candidate rules, because the local engine RNG is too noisy for small blind tweaks.

Submitted safe vs current chandlow local repeated sanity check:

- Output: `analysis_outputs/repeated_safe_vs_chandlow_key_g20r2_summary.csv`
- Diff output: `analysis_outputs/repeated_safe_vs_chandlow_key_g20r2_diff.csv`
- Setup: `20` games per seat, `2` independent repeats, key buckets only.

| Scenario | Submitted safe | Current chandlow | Diff |
| --- | ---: | ---: | ---: |
| Marnie bucket | `66 / 80` | `66 / 80` | `+0.0%` |
| Archaludon bucket | `34 / 80` | `43 / 80` | `+11.25%` |
| Ogerpon bucket | `51 / 80` | `64 / 80` | `+16.25%` |
| Starmie bucket | `72 / 80` | `71 / 80` | `-1.25%` |
| Public sample | `0.6852` | `0.7449` | `+5.97%` |
| Equal public buckets | `0.6969` | `0.7625` | `+6.56%` |

Decision:

- The current `chandlowdecklillie` line is still the best local baseline versus the submitted safe archive.
- It appears to improve Ogerpon / Archaludon style buckets without clearly worsening Starmie.
- Next useful live-log-driven work should target Starmie tempo losses and Marnie Grimmsnarl losses, because the current chandlow changes mostly address Ogerpon/control symptoms.

## 2026-07-04 Live-Loss Follow-Up: Boss Setup And Backup Probes

Baseline:

- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`

Local trace context:

- Fresh Starmie trace output: `analysis_outputs/meta_suite_current_starmie_trace_g20_games.csv`
- Fresh Marnie trace output: `analysis_outputs/meta_suite_current_marnie_trace_g30_games.csv`
- Starmie losses still often end as bench-out against `Mega Starmie ex (1031)`.
- Marnie losses also often end as bench-out after repeated `Shadow Bullet (937)` from `Marnie's Grimmsnarl ex (648)`.

Rejected probe 1:

- Candidate: `submission_archaludon_chandlow_bosssetup_targets`
- Change:
  - Add Marnie detection.
  - Boss killable Starmie setup targets (`Staryu`, `Cinderace`) and Marnie setup targets (`Impidimp`, `Morgrem`, `Munkidori`, etc.).
- Output: `analysis_outputs/repeated_bosssetup_key_g20r3_summary.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `103 / 120` | `97 / 120` |
| Archaludon | `71 / 120` | `50 / 120` |
| Ogerpon | `88 / 120` | `89 / 120` |
| Starmie | `103 / 120` | `112 / 120` |

Decision:

- Reject.
- Starmie improved, but the Marnie setup-target part worsened the intended Marnie bucket and the public proxy fell.

Rejected probe 2:

- Candidate: `submission_archaludon_chandlow_starmie_bosssetup`
- Change: only Boss killable `Staryu (1030)` / `Cinderace (666)` in detected Starmie games.
- Output: `analysis_outputs/repeated_starmieboss_key_g20r3_summary.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `109 / 120` | `104 / 120` |
| Archaludon | `59 / 120` | `46 / 120` |
| Ogerpon | `71 / 120` | `91 / 120` |
| Starmie | `103 / 120` | `107 / 120` |

Decision:

- Reject.
- The Starmie gain was small (`+4 / 120`, approximate `z = 0.782`) and public-sample proxy was lower.

Rejected probe 3:

- Candidate: `submission_archaludon_chandlow_starmie_ubbackup`
- Change:
  - In detected Starmie games only, when our bench is empty, Active HP is within `210`, and there are at least two safe discards, allow `Ultra Ball`.
  - During that Ultra Ball search, prefer active evolution into `Archaludon ex` or backup `Duraludon`.
- Output: `analysis_outputs/repeated_starmie_ubbackup_g60r3_summary.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Starmie | `315 / 360` | `317 / 360` |

Decision:

- Reject / no material effect.
- The trace symptom is real, but this specific Ultra Ball backup rule only moved `+2 / 360` (`z = 0.229`).

Watchlist probe:

- Candidate: `submission_archaludon_chandlow_marnie_durabackup`
- Change:
  - Detect Marnie line ids `646/647/648/649`.
  - In detected Marnie games only, when our bench is empty and Active HP is `<= 180`, prioritize hand-played `Duraludon`.
  - Under the same condition, allow `Ultra Ball` with safe discards and prefer active evolution into `Archaludon ex` or backup `Duraludon`.
- Focused output: `analysis_outputs/repeated_marnie_durabackup_g60r3_summary.csv`
- Key-bucket output: `analysis_outputs/repeated_marnie_durabackup_key_g20r3_summary.csv`

Focused Marnie:

| Candidate | Marnie |
| --- | ---: |
| `current` | `303 / 360` |
| `marniedura` | `318 / 360` |

Key-bucket check:

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `105 / 120` | `103 / 120` |
| Archaludon | `51 / 120` | `64 / 120` |
| Ogerpon | `81 / 120` | `78 / 120` |
| Starmie | `107 / 120` | `105 / 120` |

Decision:

- Do not package yet.
- Keep as a watchlist candidate if live history continues to show Marnie / Grimmsnarl bench-out losses.
- Evidence is directionally useful (`+15 / 360` focused, public proxy slightly up in the key check), but the intended Marnie bucket did not reproduce in the smaller key-bucket confirmation.

## 2026-07-04 Live Submission History Check: safe archive

Target submission:

- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe.tar.gz`
- Kaggle submission id: `54304032`
- Observed public score moved from about `935.3` to `931.8` while games continued.

Visible Games panel snapshot:

- Visible total: `63`
- Visible wins: `37`
- Visible losses: `26`
- Losses are not concentrated on one opponent; they are spread across many teams, with repeated or representative losses including `UBI=ISHI`, `ysakuragi`, `noikaret`, `Shunji Minode`, `wao zhang`, and others.

Representative live losses:

| Opponent | Episode | Seed | Observed symptom |
| --- | ---: | ---: | --- |
| `UBI=ISHI` | `83689119` | `227111633` | Long game (`164` steps), Cinderace active with Archaludon pieces in hand and little board progress. Looks like an opening/progression stall rather than a normal prize race. |
| `ysakuragi` | `83669966` | `1498953648` | Starmie/Cinderace pressure was visible in prior inspection; likely rush/bench-pressure bucket. |
| `noikaret` | `83661278` | `970205040` | Solrock/Lunatone + Ogerpon/control style was visible in prior inspection; long game/control or deck-pressure bucket. |
| `Shunji Minode` | `83660805` | `1641327451` | Marnie's Grimmsnarl ex + Munkidori style was visible in prior inspection; bench-out / Shadow Bullet pressure bucket. |

Interpretation:

- The live record says the deck is strong enough for bronze range, but the remaining losses are a mix of:
  - setup/progression stalls where Cinderace is active but Duraludon/energy development does not convert,
  - Starmie/Cinderace fast pressure,
  - Ogerpon/control or resource-pressure games,
  - Marnie/Grimmsnarl bench-pressure games,
  - likely Archaludon mirror variance.
- This supports using live history as the next selector for local work: do not keep random local micro-tuning; target the specific live-loss symptoms and only promote rules that reproduce across repeated local batches.

Next local targets:

1. Reproduce the `UBI=ISHI`-like opening/progression stall locally: Cinderace active, no durable Duraludon line established, draw/search cards not converting.
2. Revisit the watchlist Marnie backup rule only if more live Marnie/Grimmsnarl losses appear.
3. Keep Starmie Boss/setup probes rejected unless a new Starmie trace shows a different failure mode than the prior low-impact `starmie_bosssetup` and `starmie_ubbackup` probes.

## 2026-07-04 Follow-Up: Cinderace Rescue And Marnie Backup Recheck

Hypothesis from live history:

- The latest live `UBI=ISHI` loss showed a Cinderace-active board with Archaludon pieces in hand but no stable Duraludon line.
- Current rule suppresses Ultra Ball when our bench is empty (`"Ultra Ball: bench empty (donk risk)"`), so a possible failure mode is not using Ultra Ball to find Duraludon from a Cinderace-only setup.

Rejected probe 1:

- Candidate: `submission_archaludon_chandlow_cinderrescue_ub`
- Change: if Active is `Cinderace`, our bench is empty, no Duraludon/Archaludon ex is in play, and no Duraludon is in hand, strongly play Ultra Ball to find Duraludon.
- Output:
  - `analysis_outputs/repeated_cinderrescue_key_g15r2_summary.csv`
  - `analysis_outputs/repeated_cinderrescue_key_g15r2_diff.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `51 / 60` | `48 / 60` |
| Archaludon | `28 / 60` | `31 / 60` |
| Ogerpon | `45 / 60` | `31 / 60` |
| Starmie | `49 / 60` | `54 / 60` |

Decision:

- Reject.
- The Starmie and mirror gains do not justify the large Ogerpon collapse. Early Ultra Ball rescue spends resources that Ogerpon games need for the non-ex / Cornerstone plan.

Rejected probe 2:

- Candidate: `submission_archaludon_chandlow_cinderrescue_visible`
- Change: same Cinderace rescue idea, but only after visible opponent Starmie / Archaludon / Alakazam-Dunsparce line cards.
- Output:
  - `analysis_outputs/repeated_cinderrescuevis_key_g15r2_summary.csv`
  - `analysis_outputs/repeated_cinderrescuevis_key_g15r2_diff.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `49 / 60` | `51 / 60` |
| Archaludon | `33 / 60` | `25 / 60` |
| Ogerpon | `37 / 60` | `44 / 60` |
| Starmie | `53 / 60` | `50 / 60` |

Decision:

- Reject.
- The narrowed trigger removed the Ogerpon collapse but reversed the intended Starmie / Archaludon signal.

Marnie backup recheck:

- Candidate: `submission_archaludon_chandlow_marnie_durabackup`
- Larger key-bucket output:
  - `analysis_outputs/repeated_marnie_durabackup_key_g30r3_summary.csv`
  - `analysis_outputs/repeated_marnie_durabackup_key_g30r3_diff.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `159 / 180` | `156 / 180` |
| Archaludon | `89 / 180` | `85 / 180` |
| Ogerpon | `129 / 180` | `134 / 180` |
| Starmie | `155 / 180` | `161 / 180` |

Proxy outcome:

- Public sample: `0.7460 -> 0.7381`
- Top20 sample: `0.7519 -> 0.7437`
- Equal buckets: `0.7389 -> 0.7444`

Decision:

- Do not promote.
- It is a plausible conditional branch if future live history is Ogerpon/Starmie-heavy, but it does not improve the intended Marnie bucket and it gives up enough public-sample / top20 proxy that it should not replace the current best branch.

## 2026-07-04 Opponent Counting / Inference Probes After Live-Loss Review

Goal:

- Test whether lightweight opponent-deck inference and visible-card counting can improve the current Archaludon branch before building a larger tracker.
- Focus on changes that are explainable from visible cards: early Alakazam pressure, Marnie bench-pressure targeting, and Archaludon mirror Relicanth handling.

Rejected early Alakazam counting probe:

- Candidate: `submission_archaludon_chandlow_oppcount_lite`
- Change:
  - Add `opp_visible_counts()`.
  - Treat `Dunsparce` / `Dudunsparce` plus Psychic/Enriching Energy, with no Marnie evidence, as early Alakazam pressure.
  - Use that only to allow a third Duraludon / Archaludon ex line before Alakazam itself is visible.
- Outputs:
  - `analysis_outputs/repeated_oppcount_lite_key_g20r2_summary.csv`
  - `analysis_outputs/meta_suite_oppcount_lite_fair_g30_summary.csv`

Fair-seed check:

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `49 / 60` | `49 / 60` |
| Alakazam | `49 / 60` | `51 / 60` |
| Archaludon | `33 / 60` | `30 / 60` |
| Ogerpon | `41 / 60` | `41 / 60` |
| Starmie | `52 / 60` | `51 / 60` |

Decision:

- Reject.
- The first repeated batch looked positive, but most of that improvement appeared in buckets where the rule should not causally trigger.
- The fair-seed check showed only a small Alakazam gain and a mirror/Starmie give-up. This is not enough to promote.

Rejected Marnie Boss-target probe:

- Candidate: `submission_archaludon_chandlow_marnieboss_count`
- Change:
  - Add Marnie-line detection.
  - Raise Boss target priority for `Munkidori (112)` and Marnie evolution-line Pokemon after Marnie cards are visible.
- Output:
  - `analysis_outputs/meta_suite_marnieboss_fair_g40_summary.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `73 / 80` | `68 / 80` |
| Archaludon | `36 / 80` | `40 / 80` |
| Ogerpon | `61 / 80` | `53 / 80` |
| Starmie | `62 / 80` | `70 / 80` |

Decision:

- Reject.
- The intended Marnie bucket worsened. Spending Boss to remove bench engines appears worse than keeping prize tempo in this local mimic.

Rejected mirror deck-construction recheck:

- Candidate: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_relic1_cutice`
- Change:
  - Restore one `Relicanth`, cutting one `Jumbo Ice Cream`.
- Output:
  - `analysis_outputs/meta_suite_relic1_vs_chandlow_fair_g30_summary.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `54 / 60` | `51 / 60` |
| Alakazam | `52 / 60` | `50 / 60` |
| Archaludon | `33 / 60` | `25 / 60` |
| Ogerpon | `42 / 60` | `43 / 60` |
| Starmie | `51 / 60` | `52 / 60` |

Decision:

- Reject.
- Restoring Relicanth did not fix the mirror; it worsened it in this fair-seed check and lowered the public proxy.

Rejected mirror Relicanth Boss priority sweep:

- Candidates:
  - `submission_archaludon_chandlow_mirrorrelicboss17`: raise mirror Relicanth Boss priority from `15500` to `17000`.
  - `submission_archaludon_chandlow_mirrorrelicbosslow`: lower mirror Relicanth Boss priority to `3500`.
- Outputs:
  - `analysis_outputs/meta_suite_chandlow_relicboss17_fair_g40_summary.csv`
  - `analysis_outputs/meta_suite_chandlow_relicbosslow_fair_g30_summary.csv`

Aggressive priority result:

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `71 / 80` | `68 / 80` |
| Alakazam | `73 / 80` | `73 / 80` |
| Archaludon | `35 / 80` | `24 / 80` |
| Ogerpon | `58 / 80` | `52 / 80` |
| Starmie | `72 / 80` | `71 / 80` |

Low-priority result:

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Marnie | `53 / 60` | `54 / 60` |
| Archaludon | `31 / 60` | `30 / 60` |
| Ogerpon | `37 / 60` | `41 / 60` |
| Starmie | `52 / 60` | `57 / 60` |

Decision:

- Reject both.
- Raising the priority clearly worsened the mirror.
- Lowering the priority did not improve the mirror; non-mirror gains are not causally attributable because the rule is mirror-gated and native engine variance remains high.

Current conclusion:

- Do not replace `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`.
- Lightweight visible-card counting is useful as infrastructure, but the tested triggers are not yet strong enough.
- The remaining mirror weakness likely needs a broader plan than one-card Relicanth Boss tuning: either a different deck slot package or a turn-level policy that improves body preservation without sacrificing Ogerpon / Alakazam / Starmie equity.

## 2026-07-04 Submission After Kaggle API Token Setup

Submitted:

- Archive: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`
- Message: `Archaludon chandlowdecklillie local next candidate`
- CLI status check: `SubmissionStatus.COMPLETE`
- Initial public score: `600.0`

Notes:

- The first submit command uploaded successfully but crashed while printing the Kaggle response because the Windows CP932 console could not encode the Pokemon competition title. Rechecking with `PYTHONIOENCODING=utf-8` showed the submission was created and completed.
- Additional local probes after this candidate were rejected:
  - `submission_archaludon_chandlowdecklillie_mirrorpromotedura2`: mirror promotion tweak worsened Archaludon mirror (`49.2% -> 45.0%` in the checked fair-seed batch).
  - `submission_archaludon_chandlowdecklillie_relic1_cutnonex`: first key-bucket batch looked positive, but all-bucket fair-seed check worsened public proxy (`0.8553 -> 0.7705`) and Ogerpon/Alakazam/Chandelure buckets.
  - `submission_archaludon_chandlowdecklillie_archubbackup`: narrow mirror Ultra Ball backup rule still worsened the mirror (`42.5% -> 40.8%` in the checked fair-seed batch).
- Next useful loop should use live game history from this new submission once enough games have accumulated. The local engine repeatedly flags Archaludon mirror and bench depletion as weak points, but the simple fixes tested so far trade off too much elsewhere.

## 2026-07-04 Kaggle API and Live Replay Follow-up

Kaggle API setup:

- `C:\Users\amuam\.kaggle\kaggle.json` was detected.
- `kaggle competitions submissions -c pokemon-tcg-ai-battle` works when `PYTHONIOENCODING=utf-8` is set.
- Latest submission ref recovered through the Python 3.9 Kaggle API: `54310897`.
- The latest submission public score was still moving during checks: observed `959.7`, then `942.9`, then `931.5`. Treat this as live leaderboard calibration, not a stable final estimate.

Replay/API access:

- `GetEpisode` can be called through Kaggle's internal web API with an anonymous XSRF session when the episode ID is already known.
- `ListEpisodesFromCompetition`, `ListEpisodes`, and `GetEpisodeSummary` were not usable from the anonymous/API-token path for discovering all episode IDs.
- Direct replay JSON remains usable for known episode IDs, e.g. `https://www.kaggle.com/competitions/episodes/83699935/replay.json`.

Scans:

- `analysis_outputs/kaggle_live/scan_54310897_83699935_83700935.csv`
- `analysis_outputs/kaggle_live/scan_54310897_83700936_83705935.csv`
- The only exact hit for latest submission `54310897` was validation/self episode `83699935`.
- Episode `83700054` was a public `rurumi` loss, but it used old submission `54304032`, not latest `54310897`.
- A coarse future block scan from `83705000` to `83750000` found no existing episode block.

Live replay observations:

- `83699935` was same-team validation/self-play with rewards `[-1, 1]`.
- The losing side opened `Cinderace` with no bench, failed to find `Duraludon`, attacked without Turbo Flare targets, then lost on board wipe.
- This suggested testing a deck-construction probe to reduce `Cinderace`-only starts.

Rejected deck probe:

- Candidate: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_cinder3relic1`
- Change: `Cinderace (666) 4 -> 3`, add `Relicanth (57) 1`.
- Output: `analysis_outputs/meta_suite_cinder3relic1_key_g30_seed224000_summary.csv`

| Bucket | Current | Candidate |
| --- | ---: | ---: |
| Archaludon | `30 / 60` | `23 / 60` |
| Marnie | `55 / 60` | `50 / 60` |
| Starmie | `58 / 60` | `53 / 60` |
| Ogerpon | `47 / 60` | `45 / 60` |
| Ogerpon Cornerstone | `50 / 60` | `46 / 60` |
| Chandelure | `55 / 60` | `50 / 60` |

Decision:

- Reject.
- The single validation loss exposed a real failure mode, but cutting `Cinderace` damages setup consistency and worsens all checked key buckets.

Alakazam/Ketchum Alt follow-up:

- Episode `83700054` looked like an `Alakazam ex (743)` line, consistent with already-known Alakazam pressure losses.
- Local recheck output: `analysis_outputs/meta_suite_alakazam_submitted_vs_old_g80_seed225000_summary.csv`

| Candidate | Alakazam bucket |
| --- | ---: |
| Current submitted candidate | `133 / 160` |
| Old safe submission | `134 / 160` |

Decision:

- Do not tune current candidate from episode `83700054`; it was an old-submission loss and local Alakazam equity is already high.
- Wait for actual latest-submission public episode IDs before making live-log-specific changes.

## 2026-07-04 After Auth: 2026-07-03 Public Episodes And New Buckets

Kaggle auth recheck:

- `C:\Users\amuam\.kaggle\kaggle.json` exists and the installed Python 3.9 `kaggle.exe` works.
- Latest submission `54310897` prints as `COMPLETE` with public score `948.2` in `kaggle competitions submissions -c pokemon-tcg-ai-battle`.
- The Python object stores fields as private attributes such as `_public_score`; `str(submission)` also includes `publicScore`.

Fresh public daily episode data:

- Forced a fresh manifest download to `data/episodes_index_refresh_2026_07_04_after_auth/manifest.csv`.
- The public daily episode index now includes `2026-07-03`.
- Downloaded 20 small top episode JSON files into `data/episodes_after_auth_2026_07_04/2026-07-03-sample`.
- Extracted decks to `analysis_outputs/episode_decks_after_auth_2026_07_04_2026_07_03_sample20`.
- Summarized visible replay mentions to `analysis_outputs/episode_meta_after_auth_2026_07_04_2026_07_03_sample20`.

2026-07-03 sample20 archetype distribution:

| Archetype | All decks | Winners |
| --- | ---: | ---: |
| `marnie_grimmsnarl` | 12 | 8 |
| `ogerpon_toolbox` | 7 | 1 |
| `mega_lucario` | 4 | 4 |
| `alakazam_psychic` | 3 | 0 |
| `archaludon_metal` | 3 | 2 |
| `starmie_froslass` | 3 | 2 |
| `great_tusk_crustle` | 2 | 0 |
| `rocket_mewtwo_spidops` | 2 | 2 |
| `unknown` | 2 | 1 |
| `hop_trevenant` | 1 | 0 |
| `chandelure_psychic_control` | 1 | 0 |

Evaluation-suite updates:

- Added `great_tusk` and `alakazam_ketchum_alt` buckets to `tools/run_meta_suite.py`.
- Added scenario `public_sample_2026_07_03_top20` using the covered 7/3 buckets.
- Added scenario `live_alakazam_ketchum_alt_2026_07_04`.
- Updated `tools/aggregate_meta_summaries.py` scenario coverage metadata.

Current candidate on the new 7/3 proxy:

- Output: `analysis_outputs/meta_suite_submitted929_public0703_plus_ketchum_g20_seed227000_summary.csv`

| Scenario / bucket | Win rate |
| --- | ---: |
| `public_sample_2026_07_03_top20` | `0.7750` |
| `equal_public_buckets` | `0.7575` |
| `bucket:marnie` | `0.9000` |
| `bucket:lucario` | `0.9750` |
| `bucket:starmie` | `0.9000` |
| `bucket:alakazam` | `0.8000` |
| `bucket:alakazam_ketchum_alt` | `0.7250` |
| `bucket:ogerpon` | `0.6250` |
| `bucket:archaludon` | `0.3750` |
| `bucket:great_tusk` | `0.3250` |

Rejected public Archaludon deck-copy probe:

- Candidate: `submission_archaludon_shumpei0703_highenergy`
- Deck copied from 7/3 winner `ShumpeiNomura`: no `Cinderace`, `Metal Energy` 14, `Relicanth` 2, `Team Rocket's Articuno` 1, `Carmine` 4, `Judge` 2.
- Added minimal `Carmine`, `Judge`, and `Team Rocket's Articuno` scoring and changed setup to choose first.
- Smoke ran without errors, but Archaludon-only fair-seed check was poor:
  - Output: `analysis_outputs/meta_suite_shumpei0703_arch_g20_seed228100_summary.csv`
  - Result: `10 / 40`, win rate `0.25`.
- Decision: reject. The deck list needs a dedicated policy; copying it into the current Cinderace-oriented policy makes it worse.

Mirror Boss 2Prize-only probe:

- Candidate: `submission_archaludon_chandlow_mirrorboss2p`
- Change: in detected Archaludon mirrors, suppress non-lethal Boss's Orders into 1-prize bench targets; still allow lethal targets and 2-prize-or-better KOs.
- First mirror-only fair-seed check looked promising:
  - Output: `analysis_outputs/meta_suite_mirrorboss2p_arch_g40_seed229000_summary.csv`
  - Current: `28 / 80`, candidate: `38 / 80`.
- Broader 7/3 proxy check was only slightly positive:
  - Output: `analysis_outputs/meta_suite_mirrorboss2p_public0703_plus_ketchum_g20_seed229500_summary.csv`
  - `public_sample_2026_07_03_top20`: current `0.7681`, candidate `0.7792`.
- Repeated mirror check showed only a small gain:
  - Output: `analysis_outputs/repeated_mirrorboss2p_arch_g40r3_seed230000_summary.csv`
  - Current: `108 / 240` (`0.45`), candidate: `113 / 240` (`0.4708`).
- Decision: keep as a possible idea, but do not promote yet. The effect is positive but small relative to local mirror variance.

Rocket Mewtwo / Spidops local opponent:

- Added rough local mimic: `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple`.
- Deck copied from `kashiwashira` episodes `83448542` and `83448553`.
- Smoke and 80-game check ran without errors.
- Current submitted candidate result:
  - `analysis_outputs/local_submitted929_vs_rocket_mewtwo_g40_seed231100_summary.json`
  - `analysis_outputs/local_rocket_mewtwo_vs_submitted929_g40_seed231140_summary.json`
  - Combined result: `76 / 80`, win rate `0.95`.
- Decision: this rough mimic is not a current weakness signal. Do not over-weight it until its play policy is improved or a live loss confirms the archetype is problematic.

Great Tusk early-detection probe:

- Candidate: `submission_archaludon_chandlow_greattuskdetect58`
- Change: added card `58` to `CRUSTLE_LINE` so Great Tusk / Crustle can be detected earlier from the opponent's visible cards.
- Output: `analysis_outputs/meta_suite_greattuskdetect58_key_g30_seed232000_summary.csv`
- Result: the change worsened the key check:
  - `bucket:great_tusk`: current `27 / 60` (`0.45`), candidate `24 / 60` (`0.40`).
  - `bucket:marnie`: current `0.90`, candidate `0.75`.
  - `bucket:starmie`: current `0.95`, candidate `0.8667`.
  - `bucket:archaludon`: current `0.5333`, candidate `0.45`.
  - `public_sample_2026_07_03_top20`: current `0.7489`, candidate `0.6872`.
- Decision: reject. Earlier archetype detection alone appears to trigger the anti-Crustle branch too broadly and hurts more common buckets.

Kaggle auth and live episode scanner follow-up:

- `C:\Users\amuam\.kaggle\kaggle.json` was placed and Kaggle CLI authentication works.
- Confirmed command:
  - `kaggle competitions submissions -c pokemon-tcg-ai-battle`
  - Use `PYTHONIOENCODING=utf-8` on Windows to avoid console encoding issues.
- Latest CLI check showed the current submitted archive as `COMPLETE` with public score `937.6` at that moment. Treat this as volatile while leaderboard episodes are still calibrating.
- Added `tools/scan_kaggle_episodes.py`.
  - Purpose: scan known Kaggle episode ID ranges through `competitions.EpisodeService/GetEpisode`, match an exact `submissionId`, and optionally save matching `replay.json` files.
  - Important fix: Kaggle has both `CSRF-TOKEN` and `XSRF-TOKEN`; the internal API requires the `XSRF-TOKEN` cookie value in `X-XSRF-TOKEN`.
  - Small known-range probe worked:
    - `analysis_outputs/kaggle_live/scan_54310897_known_probe.csv`
    - `analysis_outputs/kaggle_live/scan_54310897_known_probe_workers.csv`
    - Both found one exact `54310897` hit: validation/self episode `83699935`.
- Newer range probe:
  - `analysis_outputs/kaggle_live/scan_54310897_83705936_83712000.csv`
  - Checked `6065` IDs; `196` existing episode metadata responses before the route stopped being usable; exact latest-submission hits: `0`.
- Caution: after the broader scan, Kaggle's internal episode API started returning `404`/`403` from local anonymous/API-token HTTP, likely temporary route protection or rate limiting. Direct replay JSON still works for known episode IDs, e.g. `https://www.kaggle.com/competitions/episodes/83699935/replay.json`.
- Practical next step: avoid broad high-worker scans for now. Use the scanner with narrow ranges and low workers, or rely on direct replay URLs / Kaggle UI episode links when specific episode IDs are known.

## 2026-07-04 Local Rule Refinement: Great Tusk Deckout Guard

Starting point:

- Submitted/current local candidate:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`
- Debug run:
  - `analysis_outputs/debug_current_weak_seed233000_summary.csv`
  - `analysis_outputs/debug_current_weak_seed233000_games.csv`
  - `analysis_outputs/debug_current_weak_seed233000_trace_summary.csv`
  - `analysis_outputs/debug_current_weak_seed233000_score_reasons.csv`
- In that run, current was weak into:
  - `bucket:archaludon`: `14 / 32` (`0.4375`)
  - `bucket:great_tusk`: `7 / 32` (`0.2188`)

Great Tusk loss diagnosis:

- Most Great Tusk losses were not prize losses; they were deckout-style long games.
- In `analysis_outputs/debug_current_weak_seed233000_games.csv`, current lost `25 / 32` Great Tusk games.
- Final deck counts in those Great Tusk losses were mostly `0` or `1`.
- Typical final board: current still had `Duraludon` or `Archaludon ex` active while the opponent still had all prizes; the opponent was winning by milling/stalling, not by taking prizes.
- Selected reasons in losses showed repeated late deck-thinning:
  - `play Explorer`
  - `play item`
  - `Ultra Ball: search line`
  - `Crustle: Lillie OK (no energy in hand)`

Accepted candidate:

- Candidate directory: `submission_archaludon_chandlow_crustledeckguard58_strict`
- Submission archive: `submission_archaludon_chandlow_crustledeckguard58_strict.tar.gz`
- Changes:
  - Add `58` to the Crustle/Great Tusk detection set so Great Tusk is identified before Dwebble/Crustle appears.
  - In the detected Great Tusk/Crustle branch, preserve deck more aggressively:
    - skip `Poke Pad` / `Pokegear` at `deck <= 30` or once a stable attacker exists.
    - skip `Explorer` at `deck <= 24`, or at `deck <= 30` once the line is established.
    - skip `Ultra Ball` at `deck <= 24` when the board already has enough line pieces.
    - use `Lillie's Determination` as a deck-refill line at `deck <= 25` only when hand count is above `6`; otherwise skip it.

Key Great Tusk checks:

| Output | Baseline | Candidate | Result |
| --- | ---: | ---: | --- |
| `analysis_outputs/meta_suite_deckguard58_greattusk_g40_seed235000_summary.csv` | current `32 / 80` (`0.4000`) | deckguard58 `58 / 80` (`0.7250`) | accepted direction |
| `analysis_outputs/repeated_deckguard58_greattusk_g28r3_seed235500_summary.csv` | current `60 / 168` (`0.3571`) | deckguard58 `121 / 168` (`0.7202`) | robust |
| `analysis_outputs/meta_suite_deckguard58_strict_greattusk_g48_seed239000_summary.csv` | deckguard58 `59 / 96` (`0.6146`) | strict `72 / 96` (`0.7500`) | strict better |
| `analysis_outputs/repeated_deckguard58_strict_greattusk_g28r3_seed239500_summary.csv` | deckguard58 `111 / 168` (`0.6607`) | strict `121 / 168` (`0.7202`) | strict remains better |

Full public-proxy check for strict:

- Output:
  - `analysis_outputs/meta_suite_strict_public0703_g16_seed240000_summary.csv`
  - `analysis_outputs/meta_suite_strict_public0703_g16_seed240000_results.csv`
- Summary:

| Scenario | Current | Strict |
| --- | ---: | ---: |
| `public_sample_2026_07_03_top20` | `0.7031` | `0.8125` |
| `equal_public_buckets` | `0.7219` | `0.7937` |
| `bucket:great_tusk` | `0.3438` | `0.8750` |

Rejected candidates from this loop:

- `submission_archaludon_chandlow_crustledeckguard58_mirrorboss2p`
  - Rationale: the mirror Boss suppression looked good in one key run, but repeated Archaludon-only check worsened:
    - `analysis_outputs/repeated_dg58mirrorboss2p_arch_g32r3_seed238000_summary.csv`
    - deckguard58 `100 / 192` (`0.5208`)
    - mirrorboss2p `95 / 192` (`0.4948`)
  - Decision: reject for now.
- `submission_archaludon_chandlow_greattuskseparate`
  - Rationale: separating `Great Tusk` from `Crustle` did not improve Great Tusk and hurt the key check:
    - `analysis_outputs/meta_suite_gtseparate_key_g32_seed238500_summary.csv`
    - deckguard58 `bucket:great_tusk` `0.6094`, gtseparate `0.6094`
    - deckguard58 `bucket:archaludon` `0.4375`, gtseparate `0.3906`
  - Decision: reject.

Current best local submission candidate:

- `submission_archaludon_chandlow_crustledeckguard58_strict.tar.gz`
- Main expected gain: much less deckout loss into Great Tusk / Crustle variants.
- Caution: public proxy results are still noisy outside the directly touched matchup. The code change is localized to the detected Great Tusk/Crustle branch, so non-Great-Tusk bucket swings in small runs should be treated as native-engine shuffle variance unless repeated evidence says otherwise.

## 2026-07-04 Local Rule Refinement: Post-Strict Probes

Baseline:

- Current best local candidate remains `submission_archaludon_chandlow_crustledeckguard58_strict`.
- Rechecked weak areas with trace-scores:
  - `analysis_outputs/debug_strict_arch_seed241000_summary.csv`
  - `analysis_outputs/debug_strict_key_seed243000_summary.csv`
  - `analysis_outputs/debug_strict_key_seed243000_trace_summary.csv`
  - `analysis_outputs/debug_strict_key_seed243000_score_reason_games.csv`

Rejected Archaludon mirror line-depth probes:

- `submission_archaludon_chandlow_crustledeckguard58_mirrorline3`
  - Change: in Archaludon mirrors, require up to three Duraludon/Archaludon ex line pieces and loosen mirror Night Stretcher thresholds.
  - Output: `analysis_outputs/compare_mirrorline3_arch_g32_seed242000_summary.csv`
  - Result: strict `38 / 64` (`0.5938`), mirrorline3 `31 / 64` (`0.4844`).
  - Decision: reject. Searching/evolving the third ex line costs too much tempo and prize equity.
- `submission_archaludon_chandlow_crustledeckguard58_mirrordura3`
  - Change: only require the third backup as Duraludon, keeping Archaludon ex target count at strict's default.
  - Output: `analysis_outputs/compare_mirrordura3_arch_g32_seed242500_summary.csv`
  - Result: strict `34 / 64` (`0.5312`), mirrordura3 `29 / 64` (`0.4531`).
  - Decision: reject. Even the narrower backup-body rule worsened the mirror.

Rejected Alakazam low-deck refill probe:

- `submission_archaludon_chandlow_crustledeckguard58_alaklowdecklillie`
  - Change: in detected Alakazam games, prioritize Lillie at deck `<= 8` when hand count can refill the deck.
  - Output: `analysis_outputs/compare_alaklillie_key_g40_seed244000_summary.csv`
  - Result:
    - Alakazam: strict `66 / 80`, alaklillie `64 / 80`
    - Alakazam Ketchum Alt: strict `53 / 80`, alaklillie `51 / 80`
    - Equal selected buckets: strict `0.7125`, alaklillie `0.6917`
  - Decision: reject. Late refill loses more tempo than it saves.

Rejected Ogerpon late deck-guard probe:

- `submission_archaludon_chandlow_crustledeckguard58_ogerdeckguard`
  - Change: after Cornerstone is visible and a charged non-ex Archaludon route exists, skip low-deck search items/Explorer/Ultra Ball more aggressively.
  - Output: `analysis_outputs/compare_ogerdeckguard_key_g36_seed245000_summary.csv`
  - Result:
    - Normal Ogerpon: strict `50 / 72`, ogerdeckguard `52 / 72`
    - Ogerpon-family combined: strict `176 / 216`, ogerdeckguard `175 / 216`
    - Alakazam Ketchum Alt: strict `44 / 72`, ogerdeckguard `42 / 72`
  - Decision: reject. The normal Ogerpon bump did not hold across the Ogerpon family and gave up Alakazam Alt equity.

Current decision:

- Keep `submission_archaludon_chandlow_crustledeckguard58_strict.tar.gz` as the best local candidate.
- The most common remaining local symptoms are still Archaludon mirror board collapse, Alakazam Alt pressure, and Ogerpon/Cornerstone long-game pressure, but the tested low-deck and extra-backup micro-rules are not reliable improvements.

## Iteration 2026-07-04: strict4 post-submit rule probes

Baseline for this pass:

- `submission_archaludon_safe_gt58guard_strict4`
- Current strongest archive remains `submission_archaludon_safe_gt58guard_strict4.tar.gz` unless a later probe has stronger repeated evidence.

Evaluation tooling update:

- Added `--no-traces` to `tools/run_repeated_meta_suite.py`.
- `run_meta_suite.py --fair-seeds` and `--seed-base` still do not seed the native engine shuffle. A strict4 copycheck showed large differences even for identical code, so candidate comparisons must use repeated batches and should not be treated as deterministic paired tests.
- `--no-traces` makes larger repeated batches practical by skipping per-game JSONL trace output.

Archaludon mirror probe:

- Candidate: `submission_archaludon_safe_gt58guard_strict4_mirrorline3_relic235`
- Change:
  - In Archaludon mirrors, search toward three Duraludon/Archaludon ex line pieces.
  - Raise killable opposing Relicanth Boss target priority from `22500` to `23500`.
- Archive built and smoke-tested:
  - `submission_archaludon_safe_gt58guard_strict4_mirrorline3_relic235.tar.gz`
  - Extract/compile/smoke errors: `0`
- Focused repeated result:
  - Output: `analysis_outputs/repeat_strict4_mirrorline3_relic235_arch_g100r5_seed362000_summary.csv`
  - strict4: `459 / 1000` (`0.4590`)
  - mirrorline3_relic235: `484 / 1000` (`0.4840`)
- Decision:
  - Keep as a mirror-heavy environment candidate, but do not replace strict4 as the broad best. The repeated edge is only `+2.5pt`.

Tool Scrapper probes:

- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_toolscrap1_cutgear`
  - `submission_archaludon_safe_gt58guard_strict4_toolscrap1_cutice`
  - dead-discard/pad variants
- Change:
  - Add one Tool Scrapper and target opposing Tools, especially Hero's Cape.
  - Add `OptionType.TOOL_CARD` target scoring to avoid discarding own Hero's Cape.
- Result:
  - Initial small screen looked positive, but repeated/follow-up checks swung negative and exposed broad side effects.
- Decision:
  - Reject for current broad candidate. Keep the code as a reference if the leaderboard becomes Hero's Cape mirror-heavy.

Alakazam non-ex Archaludon probes:

- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_ketchum_nonex`
  - `submission_archaludon_safe_gt58guard_strict4_alak_nonex_noketchum`
- Hypothesis:
  - Use non-ex Archaludon into Alakazam / Neutralization Zone pressure to improve prize trade and avoid ex-damage prevention.
- Results:
  - First Ketchum/Alakazam screen was noisy and partly positive.
  - Follow-up repeated result rejected both variants:
    - Output: `analysis_outputs/repeat_strict4_alak_nonex_variants_g50r4_seed365000_summary.csv`
    - strict4 Alakazam: `349 / 400` (`0.8725`)
    - `ketchum_nonex` Alakazam: `340 / 400` (`0.8500`)
    - `alak_nonex_noketchum` Alakazam: `279 / 400` (`0.6975`)
    - strict4 Ketchum: `268 / 400` (`0.6700`)
    - `ketchum_nonex` Ketchum: `219 / 400` (`0.5475`)
    - `alak_nonex_noketchum` Ketchum: `258 / 400` (`0.6450`)
- Decision:
  - Reject. The non-ex route loses too much tempo against these local Alakazam agents.

Current decision after this pass:

- Keep `submission_archaludon_safe_gt58guard_strict4.tar.gz` as broad best.
- Keep `submission_archaludon_safe_gt58guard_strict4_mirrorline3_relic235.tar.gz` only as a mirror-heavy optional candidate.
- Reject Tool Scrapper and Alakazam non-ex variants for broad submission.

Ogerpon low-deck preservation probe:

- Candidate: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex`
- Archive built and smoke-tested:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex.tar.gz`
  - Extract/compile/smoke errors: `0`
- Change:
  - When Ogerpon is detected, Cornerstone Mask Ogerpon ex (`117`) is visible, and non-ex Archaludon is already in play, avoid extra deck-thinning plays in the late game.
  - Skip Explorer, Pokegear, Poke Pad, and Ultra Ball at deck `<= 12`.
  - Skip Lillie at deck `<= 6`.
- Motivation:
  - Loss traces against normal Ogerpon showed games where the non-ex Archaludon answer was established, but the agent kept using Explorer/Pokegear/Lillie at very low deck counts and lost the long game.
- Focused repeated results:
  - `analysis_outputs/repeat_strict4_oger_lowdeck_family_g60r4_seed368000_summary.csv`
  - `analysis_outputs/repeat_strict4_oger_lowdeck_variants_g40r3_seed371000_summary.csv`
  - Combined with the light all-meta screen, strict4 vs `hasnonex` over Ogerpon-family buckets:
    - Normal Ogerpon: strict4 `547 / 784` (`0.6977`), `hasnonex` `557 / 784` (`0.7105`)
    - Ogerpon Cornerstone: strict4 `618 / 784` (`0.7883`), `hasnonex` `629 / 784` (`0.8023`)
    - Ogerpon Raging Bolt: strict4 `756 / 784` (`0.9643`), `hasnonex` `758 / 784` (`0.9668`)
- Broad screen:
  - Output: `analysis_outputs/repeat_strict4_oger_lowdeck_all_g16r2_seed370000_summary.csv`
  - Equal public buckets: strict4 `0.8329`, `hasnonex` `0.8401`
  - Public-sample scenarios were mixed within noise (`-0.7pt` to `+0.3pt`), with no errors.
  - Alakazam short-screen underperformance appears to be native shuffle noise rather than Ogerpon misdetection; the local Alakazam decks do not contain Ogerpon-line IDs.
- Rejected follow-up variants:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_activeonly`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_activeonly_soft`
  - Restricting the rule to active non-ex Archaludon reduced the normal Ogerpon win rate and did not improve the aggregate.
- Decision:
  - Promote `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex.tar.gz` as the next local submit candidate over strict4.
  - Expected gain is modest and Ogerpon-meta dependent; keep `submission_archaludon_safe_gt58guard_strict4.tar.gz` as the fallback if live results underperform.

Combined Ogerpon + mirror probe:

- Candidate: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235`
- Archive built and smoke-tested:
  - `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235.tar.gz`
  - Extract/compile/smoke errors: `0`
- Change:
  - Starts from `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex`.
  - Adds the prior Archaludon mirror line-depth probe:
    - Treat Archaludon mirrors like Alakazam for the third Duraludon/Archaludon ex line target.
    - Raise killable opposing Relicanth Boss priority from `22500` to `23500`.
- Focused screen:
  - Output: `analysis_outputs/repeat_strict4_oger_combo_focus_g32r2_seed373000_summary.csv`
  - Archaludon: strict4 `51 / 128` (`0.3984`), combo `47 / 128` (`0.3672`)
  - Normal Ogerpon: strict4 `93 / 128` (`0.7266`), combo `100 / 128` (`0.7812`)
  - Ogerpon Cornerstone: strict4 `99 / 128` (`0.7734`), combo `105 / 128` (`0.8203`)
  - Ogerpon Raging Bolt: strict4 `124 / 128` (`0.9688`), combo `126 / 128` (`0.9844`)
- Light all-meta screen:
  - Output: `analysis_outputs/repeat_strict4_oger_combo_all_g8r2_seed374000_summary.csv`
  - Equal public buckets: strict4 `0.8149`, Oger lowdeck `0.8462`, combo `0.8654`
  - Public-sample scenarios all improved for combo in this short screen, but the per-bucket sample is only `32` games and should be treated as noisy.
- Decision:
  - Keep the combo archive as the higher-upside candidate if the live field appears Archaludon/Ogerpon-heavy.
  - Keep `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex.tar.gz` as the more conservative next submit candidate because the mirror component is still noisy across local batches.

Archaludon mirror trace follow-up:

- Trace run:
  - `analysis_outputs/trace_combo_arch_g8_seed376000_summary.csv`
  - `analysis_outputs/trace_combo_arch_g8_seed376000_games.csv`
  - `analysis_outputs/trace_combo_arch_g8_seed376000_trace_summary.csv`
  - `analysis_outputs/trace_combo_arch_g8_seed376000_score_reason_games.csv`
- Result:
  - Combo candidate vs public Archaludon mimic: `7 / 16` (`0.4375`), errors `0`.
- Observations:
  - Several losses reached the normal late mirror state with both sides trading Archaludon ex attackers and prizes at `1` to `2`.
  - Some loss traces showed non-ex Archaludon `840` available but held outside Ogerpon.
  - This is not a fresh patch target by itself: prior `mirrornonex` and backup-non-ex probes already fell in focused mirror checks because the lower-damage attacker loses tempo.
  - Prior `choose first` mirror probe was also rejected; going second for Cinderace acceleration remains better locally.
- Decision:
  - Do not add a new mirror rule from this trace pass.
  - Current actionable candidates remain:
    - Conservative: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex.tar.gz`
    - Higher-upside / mirror+Ogerpon field: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235.tar.gz`

Rejected Alakazam Ketchum Boss probes:

- Starting point: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235`
- Trace run:
  - `analysis_outputs/trace_combo_ketchum_g10_seed377000_summary.csv`
  - `analysis_outputs/trace_combo_ketchum_g10_seed377000_games.csv`
  - `analysis_outputs/trace_combo_ketchum_g10_seed377000_score_reason_games.csv`
- Observation:
  - Ketchum Alt losses mixed early setup failures with late one-to-two-prize races.
  - The opponent often used Dunsparce / Dudunsparce pivots while keeping Alakazam lines on the bench.
- Candidate: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235_alakbosscore`
  - Rule: if Active is not Alakazam and a benched Alakazam/Kadabra is KO-able, spend Boss to remove the Alakazam line.
  - Output: `analysis_outputs/repeat_combo_alakboss_variants_g40r3_seed379000_summary.csv`
  - Result:
    - Normal Alakazam: combo `210 / 240` (`0.8750`), `alakbosscore` `202 / 240` (`0.8417`)
    - Ketchum Alt: combo `146 / 240` (`0.6083`), `alakbosscore` `162 / 240` (`0.6750`)
  - Decision: reject for broad use. The Ketchum gain costs too much normal Alakazam equity.
- Candidate: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235_ketchumbossalak`
  - Rule: only use the Boss-Alakazam line when the opponent Active is Dunsparce/Dudunsparce.
  - Same output as above.
  - Result:
    - Normal Alakazam: combo `210 / 240` (`0.8750`), `ketchumbossalak` `206 / 240` (`0.8583`)
    - Ketchum Alt: combo `146 / 240` (`0.6083`), `ketchumbossalak` `157 / 240` (`0.6542`)
  - Decision: reject for broad use. The narrower rule still gives up normal Alakazam equity.
- Candidate: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235_ketchumbossalak65`
  - Rule: restrict further to Active Dunsparce `65`, which is specific to the Ketchum Alt proxy.
  - Output: `analysis_outputs/repeat_combo_ketchum65_g50r3_seed380000_summary.csv`
  - Result:
    - Normal Alakazam: combo `250 / 300` (`0.8333`), `ketchum65` `250 / 300` (`0.8333`)
    - Ketchum Alt: combo `179 / 300` (`0.5967`), `ketchum65` `175 / 300` (`0.5833`)
  - Decision: reject. Removing the normal-Alakazam side effect also removed the Ketchum benefit.
- Conclusion:
  - Do not add an Alakazam Boss override to the current submit candidates.
  - If live leaderboard becomes clearly Ketchum-heavy, `alakbosscore` is a possible specialist, but it is not the broad candidate.

Conservative vs combo priority check:

- Candidates:
  - Conservative: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex`
  - Combo: `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235`
- Additional all-bucket comparison:
  - Output: `analysis_outputs/repeat_ogerlow_combo_all_g16r2_seed381000_summary.csv`
  - Errors: `0`
- Result:
  - Equal public buckets: conservative `0.8257`, combo `0.8438`
  - Public sample 2026-07-02: conservative `0.8063`, combo `0.7932`
  - Public sample 2026-07-02 top20: conservative `0.8113`, combo `0.7949`
  - Public sample 2026-07-03 top20: conservative `0.8338`, combo `0.8286`
  - Ketchum Alt: conservative `40 / 64`, combo `46 / 64`
  - Archaludon: conservative `23 / 64`, combo `33 / 64`
  - Marnie: conservative `61 / 64`, combo `56 / 64`
  - Normal Alakazam: conservative `55 / 64`, combo `50 / 64`
- Combined with the prior light all-bucket screen:
  - Equal public buckets: conservative `0.8325`, combo `0.8510`
  - Ketchum Alt: conservative `0.6042`, combo `0.7188`
  - Public sample 2026-07-02: conservative `0.8182`, combo `0.8043`
  - Public sample 2026-07-02 top20: conservative `0.8229`, combo `0.8062`
  - Public sample 2026-07-03 top20: conservative `0.8423`, combo `0.8290`
- Decision:
  - Keep the conservative archive as the broad default because it is better under the public-sample meta assumptions and safer against normal Alakazam / Marnie.
  - Use the combo archive only when live evidence suggests a heavier Ketchum Alt / Archaludon / Starmie field than the public-sample assumptions.

Rejected mirror decomposition probes:

- Starting point: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex`
- Reason:
  - The combo candidate mixed two Archaludon-mirror changes:
    - Raise KO-able opposing Relicanth Boss target score from `22500` to `23500`.
    - Search toward three Duraludon/Archaludon ex line pieces in mirrors.
  - This pass separated those two changes to see whether either one was a safer standalone patch.
- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_relic235only`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_line3only`
  - Compared against conservative `oger_lowdeck` and combo.
- Output:
  - `analysis_outputs/repeat_ogerlow_mirror_decomp_arch_g50r3_seed382000_summary.csv`
  - `analysis_outputs/repeat_ogerlow_mirror_decomp_arch_g50r3_seed382000_diff.csv`
- Result:
  - `oger_lowdeck`: `143 / 300` (`0.4767`)
  - `relic235only`: `134 / 300` (`0.4467`)
  - `line3only`: `140 / 300` (`0.4667`)
  - `combo`: `141 / 300` (`0.4700`)
  - Errors: `0`
- Decision:
  - Reject both standalone mirror patches.
  - Treat prior combo mirror gains as noisy and field-dependent, not as a clean broad improvement.
  - Keep `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex.tar.gz` as the broad default.

Ogerpon low-deck threshold sweep:

- Starting point:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex`
  - Original rule: after Cornerstone is visible and non-ex Archaludon is in play, suppress search/thinning at deck `<= 12` and Lillie at deck `<= 6`.
- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t10_l5`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t16_l8`
- First Ogerpon-family screen:
  - Output: `analysis_outputs/repeat_ogerlow_thresholds_g40r3_seed383000_summary.csv`
  - `t10_l5` was worse, mostly from Cornerstone.
  - `t14_l7` improved normal Ogerpon but hurt Cornerstone in this first batch.
  - `t16_l8` was mixed and hurt normal Ogerpon.
- Light all-bucket screen:
  - Output: `analysis_outputs/repeat_ogerlow_thresholds_all_g8r2_seed384000_summary.csv`
  - Treat non-Ogerpon bucket differences as native shuffle noise because the rule only triggers on visible Ogerpon-family IDs.
  - The signal supported checking `t14_l7` again because normal Ogerpon rose strongly.
- Confirmation:
  - Output: `analysis_outputs/repeat_ogerlow_t14_confirm_g80r3_seed385000_summary.csv`
  - Normal Ogerpon: `t12_l6` `334 / 480` (`0.6958`), `t14_l7` `352 / 480` (`0.7333`)
  - Ogerpon Cornerstone: `t12_l6` `368 / 480` (`0.7667`), `t14_l7` `388 / 480` (`0.8083`)
  - Ogerpon Raging Bolt: `t12_l6` `461 / 480` (`0.9604`), `t14_l7` `469 / 480` (`0.9771`)
  - Ogerpon toolbox weighted scenario: `t12_l6` `0.8370`, `t14_l7` `0.8667`
  - Errors: `0`
- Archive built and smoke-tested:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7.tar.gz`
  - Extract/compile/smoke errors: `0`
- Decision:
  - Promote `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7.tar.gz` as the new broad default submit candidate.
  - Keep `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_hasnonex.tar.gz` as the previous fallback.
  - Reject `t10_l5` and `t16_l8` for broad use.

Rejected Ogerpon threshold-neighbor probes:

- Starting point:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7`
- Reason:
  - After `t14_l7` beat `t12_l6`, test nearby thresholds to separate the search/thinning threshold from the Lillie threshold.
- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l6`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l8`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t13_l7`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t15_l7`
- Output:
  - `analysis_outputs/repeat_ogerlow_t14_neighbors_g36r2_seed387000_summary.csv`
  - `analysis_outputs/repeat_ogerlow_t14_neighbors_g36r2_seed387000_diff.csv`
- Result:
  - `t14_l7`: normal Ogerpon `115 / 144` (`0.7986`), Cornerstone `110 / 144` (`0.7639`), Raging Bolt `140 / 144` (`0.9722`)
  - `t14_l6`: normal Ogerpon `96 / 144` (`0.6667`), Cornerstone `118 / 144` (`0.8194`), Raging Bolt `144 / 144` (`1.0000`)
  - `t14_l8`: normal Ogerpon `104 / 144` (`0.7222`), Cornerstone `115 / 144` (`0.7986`), Raging Bolt `138 / 144` (`0.9583`)
  - `t13_l7`: normal Ogerpon `101 / 144` (`0.7014`), Cornerstone `115 / 144` (`0.7986`), Raging Bolt `138 / 144` (`0.9583`)
  - `t15_l7`: normal Ogerpon `108 / 144` (`0.7500`), Cornerstone `115 / 144` (`0.7986`), Raging Bolt `140 / 144` (`0.9722`)
  - Errors: `0`
- Decision:
  - Keep `t14_l7` as the broad default because it preserves the highest normal Ogerpon rate.
  - The neighbor variants shift equity toward Cornerstone/Raging Bolt, but they give up too much normal Ogerpon and do not justify replacing the current archive.

Rejected Ogerpon Cornerstone promotion probe:

- Starting point:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7`
- Trace source:
  - `analysis_outputs/trace_t14_l7_ogerpon_g16_seed388000_games.csv`
  - `analysis_outputs/trace_t14_l7_ogerpon_g16_seed388000_score_reasons.csv`
- Observation:
  - Several Ogerpon losses still involved Cornerstone in the Active slot.
  - One visible mistake was retreating into `Archaludon ex` against active Cornerstone, then passing because `Metal Defender` was blocked.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_cornerpromote`
  - Rule: in active-Cornerstone Ogerpon states, avoid retreating into blocked `Archaludon ex`; prefer a direct-attack-capable non-Ability `Archaludon` / `Duraludon`, and prefer those on forced promotion.
- Output:
  - `analysis_outputs/repeat_cornerpromote_ogerpon_g60r3_seed389000_summary.csv`
  - `analysis_outputs/repeat_cornerpromote_ogerpon_g60r3_seed389000_diff.csv`
- Result:
  - `t14_l7`: normal Ogerpon `256 / 360` (`0.7111`)
  - `cornerpromote`: normal Ogerpon `243 / 360` (`0.6750`)
  - Errors: `0`
- Decision:
  - Reject. The single trace looked strategically wrong, but the broad Ogerpon check says the extra promotion/retreat restriction costs more tempo than it saves.

Rejected Ogerpon Boss-target priority probes:

- Starting point:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7`
- Reason:
  - Boss target counts in the Ogerpon trace showed many wins after pulling `Solrock` / `Lunatone`, while some losses involved `Okidogi` or support targets.
  - The default priority was `Binacle > Munkidori > Lunatone/Solrock > Okidogi > Barbaracle`.
- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_bosssolluna`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_bossokidogi`
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_bossokidogi_solluna`
- First normal-Ogerpon screen:
  - Output: `analysis_outputs/repeat_ogerboss_priority_g50r3_seed390000_summary.csv`
  - `t14_l7`: `203 / 300` (`0.6767`)
  - `bosssolluna`: `220 / 300` (`0.7333`)
  - `bossokidogi`: `223 / 300` (`0.7433`)
- Ogerpon-family side check for `bossokidogi`:
  - Output: `analysis_outputs/repeat_bossokidogi_cornerstone_g50r3_seed391000_summary.csv`
  - Cornerstone: `t14_l7` `230 / 300` (`0.7667`), `bossokidogi` `243 / 300` (`0.8100`)
  - Output: `analysis_outputs/repeat_bossokidogi_raging_g50r3_seed392000_summary.csv`
  - Raging Bolt: both `289 / 300` (`0.9633`)
- Recheck:
  - Output: `analysis_outputs/repeat_ogerboss_combo_g50r3_seed394000_summary.csv`
  - `t14_l7`: normal Ogerpon `228 / 300` (`0.7600`)
  - `bossokidogi`: normal Ogerpon `208 / 300` (`0.6933`)
  - `bossokidogi_solluna`: normal Ogerpon `202 / 300` (`0.6733`)
  - Errors: `0`
- Decision:
  - Reject all Boss-priority changes for the current broad candidate.
  - The initial positive signal did not reproduce; aggregated normal-Ogerpon evidence does not clearly beat `t14_l7`.
  - Keep the default Ogerpon Boss target map.

Archaludon mirror trace pass:

- Trace source:
  - `analysis_outputs/trace_t14_l7_archaludon_g16_seed395000_games.csv`
  - `analysis_outputs/trace_t14_l7_archaludon_g16_seed395000_score_reasons.csv`
- Result:
  - `t14_l7` vs public Archaludon: `13 / 32` (`0.4062`)
  - Errors: `0`
- Observation:
  - Losses mostly remain normal mirror attrition: repeated `Duraludon` / `Archaludon ex` board collapse and prize-race losses.
  - The public Archaludon proxy has `Relicanth`; current `t14_l7` instead keeps the Ogerpon-oriented non-ex `Archaludon` package.
  - Prior Relicanth restore, mirror line-depth, Relicanth Boss, and promotion tweaks were already rejected or marked field-dependent.
- Decision:
  - Do not add a new mirror micro-rule from this trace pass.
  - The next reliable mirror improvement probably needs a larger deck-package pivot or live-history evidence, not another small local rule.

Combo candidate recheck after `t14_l7`:

- Reason:
  - The prior `ogerlow_mirrorline3_relic235` combo candidate had the old Ogerpon low-deck thresholds (`search <= 12`, `Lillie <= 6`), while the promoted broad candidate uses `t14_l7` (`search <= 14`, `Lillie <= 7`).
  - Test whether combining the accepted Ogerpon threshold with the mirror/Ketchum-oriented combo rules gives a better broad candidate.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_t14_l7_mirrorline3_relic235`
  - Deck: unchanged from `t14_l7`.
  - Code: start from `submission_archaludon_safe_gt58guard_strict4_ogerlow_mirrorline3_relic235`, then change Ogerpon low-deck thresholds from `12/6` to `14/7`.
- Light all-bucket output:
  - `analysis_outputs/repeat_combo_t14_all_g12r2_seed396000_summary.csv`
  - `combo_t14` beat `t14_l7` on equal buckets by only `+0.0032`, but gave up Alakazam, Great Tusk, Marnie, and Ketchum Alt in this pass.
- Ogerpon-family focused output:
  - `analysis_outputs/repeat_combo_t14_ogerpon_g40r2_seed397000_summary.csv`
  - `analysis_outputs/repeat_combo_t14_cornerstone_g40r2_seed398000_summary.csv`
  - `analysis_outputs/repeat_combo_t14_raging_g40r2_seed399000_summary.csv`
  - Normal Ogerpon: `t14_l7` `112 / 160` (`0.7000`), `combo_old` `117 / 160` (`0.7312`), `combo_t14` `123 / 160` (`0.7688`)
  - Cornerstone: `t14_l7` `128 / 160` (`0.8000`), `combo_old` `128 / 160` (`0.8000`), `combo_t14` `117 / 160` (`0.7312`)
  - Raging Bolt: `t14_l7` `154 / 160` (`0.9625`), `combo_old` `157 / 160` (`0.9812`), `combo_t14` `152 / 160` (`0.9500`)
- Recheck `t14_l7` vs `combo_old`:
  - Output: `analysis_outputs/repeat_t14_vs_combo_old_all_g24r2_seed400000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.8029`, `combo_old` `0.8013`
  - Public sample 2026-07-02 top20: `t14_l7` `0.8055`, `combo_old` `0.8044`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8157`, `combo_old` `0.8255`
  - Equal buckets: `t14_l7` `0.8333`, `combo_old` `0.8237`
  - Starmie-heavy: `t14_l7` `0.8010`, `combo_old` `0.7531`
  - Ogerpon toolbox: `t14_l7` `0.8117`, `combo_old` `0.7965`
  - Errors: `0`
- Decision:
  - Reject `combo_t14` for broad use. The normal-Ogerpon gain is offset by a large Cornerstone drop.
  - Keep `t14_l7` as the broad default.
  - Keep `combo_old` only as a field-read pivot if live evidence is specifically Ketchum Alt / Marnie / normal Ogerpon-heavy and not Starmie-heavy.

Rejected Ketchum Alt backup-line probes:

- Trace source:
  - `analysis_outputs/trace_t14_l7_ketchum_g16_seed401000_games.csv`
  - `analysis_outputs/trace_t14_l7_ketchum_g16_seed401000_score_reasons.csv`
- Observation:
  - `t14_l7` vs Ketchum Alt scored `20 / 32` (`0.6250`) in the trace pass.
  - Many losses ended with the opponent's Alakazam active and our side benched out or nearly benched out.
  - `t14_l7` already searches up to three `Duraludon` / `Archaludon ex` line pieces against detected Alakazam.
- Candidate 1:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_ketchumline4`
  - Rule: if visible opponent board contains `Dunsparce (65)` plus an Alakazam-line Pokemon, search up to four `Duraludon` / `Archaludon ex` line pieces.
  - Ketchum output: `analysis_outputs/repeat_ketchumline4_ketchum_g60r3_seed402000_summary.csv`
  - Normal Alakazam output: `analysis_outputs/repeat_ketchumline4_alakazam_g40r2_seed403000_summary.csv`
  - Result:
    - Ketchum Alt: `t14_l7` `225 / 360` (`0.6250`), `ketchumline4` `230 / 360` (`0.6389`)
    - Normal Alakazam: `t14_l7` `132 / 160` (`0.8250`), `ketchumline4` `119 / 160` (`0.7438`)
  - Decision: reject. The Ketchum gain is small and the normal-Alakazam loss is too large.
- Candidate 2:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_ketchumstadline4`
  - Rule: only search the fourth line after Ketchum-specific `Jamming Tower (1246)` / `Neutralization Zone (1247)` is visible in stadium or opponent discard, plus an Alakazam-line Pokemon.
  - Ketchum output: `analysis_outputs/repeat_ketchumstadline4_ketchum_g50r2_seed404000_summary.csv`
  - Normal Alakazam output: `analysis_outputs/repeat_ketchumstadline4_alakazam_g40r2_seed405000_summary.csv`
  - Result:
    - Ketchum Alt: `t14_l7` `133 / 200` (`0.6650`), `stadline4` `126 / 200` (`0.6300`)
    - Normal Alakazam: `t14_l7` `133 / 160` (`0.8313`), `stadline4` `138 / 160` (`0.8625`)
  - Decision: reject. The narrower condition no longer helps the intended Ketchum bucket.
- Conclusion:
  - Do not add a fourth-line search rule for Ketchum Alt.
  - Ketchum losses look like board-collapse symptoms, but extra line search spends too much tempo or triggers too late.

Rejected Marnie Ultra Ball emergency Cinderace probe:

- Trace source:
  - `analysis_outputs/trace_t14_l7_marnie_g20_seed406000_games.csv`
  - `analysis_outputs/trace_t14_l7_marnie_g20_seed406000_score_reasons.csv`
- Observation:
  - `t14_l7` scored `37 / 40` (`0.9250`) in the trace pass, so Marnie is not currently a broad weakness.
  - One loss showed a specific bad-looking line: after reaching an empty bench, Ultra Ball searched the deck and only saw `Cinderace (666)` as a possible backup body, but the generic `skip Cinderace` rule made the agent take nothing.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_marnieubcinder`
  - Rule: if visible Marnie IDs (`646/647/648/649/1259`) are present, our bench is empty, and Ultra Ball is selecting from the deck, score `Cinderace` as an emergency backup target.
- First focused checks:
  - `analysis_outputs/repeat_marnieubcinder_marnie_g60r3_seed407000_summary.csv`
  - Marnie: `t14_l7` `308 / 360` (`0.8556`), `marnieubcinder` `321 / 360` (`0.8917`)
  - `analysis_outputs/repeat_marnieubcinder_starmie_g30r2_seed408000_summary.csv`
  - Starmie: `t14_l7` `106 / 120` (`0.8833`), `marnieubcinder` `108 / 120` (`0.9000`)
  - `analysis_outputs/repeat_marnieubcinder_ogerpon_g30r2_seed409000_summary.csv`
  - Normal Ogerpon: `t14_l7` `81 / 120` (`0.6750`), `marnieubcinder` `94 / 120` (`0.7833`)
  - Treat non-Marnie swings as native-engine noise because the rule is Marnie-ID gated.
- All-bucket check:
  - `analysis_outputs/repeat_marnieubcinder_all_g16r2_seed410000_summary.csv`
  - Marnie bucket was tied: both `56 / 64` (`0.8750`)
  - Public sample 2026-07-02: `t14_l7` `0.8088`, `marnieubcinder` `0.7718`
  - Equal buckets: `t14_l7` `0.8281`, `marnieubcinder` `0.8293`
- Focused confirmation:
  - `analysis_outputs/repeat_marnieubcinder_marnie_confirm_g80r3_seed411000_summary.csv`
  - Marnie: `t14_l7` `426 / 480` (`0.8875`), `marnieubcinder` `403 / 480` (`0.8396`)
  - Errors: `0`
- Decision:
  - Reject. The attractive trace-level fix did not reproduce; in the larger Marnie confirmation it clearly worsened the intended bucket.
  - Keep `t14_l7` unchanged as the broad default.

Rejected Relicanth one-slot restore on top of `t14_l7`:

- Motivation:
  - The current `t14_l7` shell is relicless and keeps two non-ex `Archaludon (840)` plus four `Cinderace (666)`.
  - Earlier Relicanth restores were rejected on older branches, but `t14_l7` changed Ogerpon low-deck policy, so the slot question was rechecked directly.
- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_relic1_cutnonex`
    - Deck change: `+1 Relicanth (57)`, `-1 non-ex Archaludon (840)`.
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_relic1_cutcinder`
    - Deck change: `+1 Relicanth (57)`, `-1 Cinderace (666)`.
- All-bucket check:
  - Output: `analysis_outputs/repeat_relic1_slots_all_g12r2_seed412000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.7988`, `relic_cutnonex` `0.7774`, `relic_cutcinder` `0.7588`
  - Public sample 2026-07-02 top20: `t14_l7` `0.8036`, `relic_cutnonex` `0.7797`, `relic_cutcinder` `0.7615`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8177`, `relic_cutnonex` `0.7934`, `relic_cutcinder` `0.7818`
  - Equal public buckets: `t14_l7` `0.8285`, `relic_cutnonex` `0.7965`, `relic_cutcinder` `0.7869`
  - Ogerpon toolbox: `t14_l7` `0.8013`, `relic_cutnonex` `0.7612`, `relic_cutcinder` `0.7740`
  - Errors: `0`
- `relic_cutnonex` focused check:
  - Output: `analysis_outputs/repeat_relic_cutnonex_focus_g40r3_seed413000_summary.csv`
  - Archaludon mirror: `t14_l7` `97 / 240` (`0.4042`), `relic_cutnonex` `117 / 240` (`0.4875`)
  - Ketchum Alt: `t14_l7` `154 / 240` (`0.6417`), `relic_cutnonex` `145 / 240` (`0.6042`)
  - Ogerpon Cornerstone: `t14_l7` `188 / 240` (`0.7833`), `relic_cutnonex` `171 / 240` (`0.7125`)
- Decision:
  - Reject both Relicanth restore slots for broad use.
  - `relic_cutnonex` has a reproducible Archaludon mirror lift, but it gives up too much against Ketchum Alt, Cornerstone, and broad public mixes.
  - Keep `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7` as the default candidate.
  - Keep `relic_cutnonex` only as a mirror-heavy field-read reference, not as a submission candidate.

Rejected mirrorline3-only replay on top of `t14_l7`:

- Motivation:
  - Mirror losses still look like line-collapse games, so the old line-depth idea was retested without also raising opposing Relicanth Boss priority.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_mirrorline3only`
  - Code change: in Archaludon mirrors, `need_archaludon` searches toward three `Archaludon ex` in play, same as the Alakazam rule.
  - Deck: unchanged from `t14_l7`.
- First focused mirror check:
  - Output: `analysis_outputs/repeat_mirrorline3only_arch_g80r3_seed414000_summary.csv`
  - Archaludon mirror: `t14_l7` `223 / 480` (`0.4646`), `mirrorline3only` `253 / 480` (`0.5271`)
- All-bucket check:
  - Output: `analysis_outputs/repeat_mirrorline3only_all_g20r2_seed415000_summary.csv`
  - Archaludon bucket reversed: `t14_l7` `42 / 80` (`0.5250`), `mirrorline3only` `28 / 80` (`0.3500`)
  - Public sample 2026-07-02: `t14_l7` `0.8102`, `mirrorline3only` `0.7809`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8306`, `mirrorline3only` `0.8073`
  - Equal public buckets: `t14_l7` `0.8260`, `mirrorline3only` `0.8288`
- Focused confirmation:
  - Output: `analysis_outputs/repeat_mirrorline3only_arch_g80r3_seed416000_summary.csv`
  - Archaludon mirror: `t14_l7` `232 / 480` (`0.4833`), `mirrorline3only` `217 / 480` (`0.4521`)
  - Errors: `0`
- Decision:
  - Reject. The first mirror gain did not reproduce, and broad public-sample proxies worsened.
  - Keep `t14_l7` as the default candidate.

Rejected Ketchum lock-stadium Full Metal Lab priority:

- Motivation:
  - Ketchum Alt losses often show `Neutralization Zone (1247)` or `Jamming Tower (1246)` in the game, so a narrow Full Metal Lab overwrite rule was tested.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_ketchumfml`
  - Detects active Ketchum lock stadium only when the current stadium is `1246/1247` and visible opponent board has an Alakazam-line Pokemon.
  - If detected:
    - Play `Full Metal Lab (1244)` at score `28000`.
    - Take `Full Metal Lab` from selection at score `17000` if not already in hand.
    - Avoid discarding `Full Metal Lab`.
  - Deck: unchanged from `t14_l7`.
- Focused check:
  - Output: `analysis_outputs/repeat_ketchumfml_alak_g50r3_seed417000_summary.csv`
  - Normal Alakazam: `t14_l7` `241 / 300` (`0.8033`), `ketchumfml` `243 / 300` (`0.8100`)
  - Ketchum Alt: `t14_l7` `198 / 300` (`0.6600`), `ketchumfml` `180 / 300` (`0.6000`)
  - Errors: `0`
- Decision:
  - Reject. The rule slightly improved normal Alakazam in this pass but worsened the intended Ketchum Alt bucket.
  - The likely issue is tempo: spending selection priority on Full Metal Lab does not solve the board-collapse / attacker-pressure problem quickly enough.
  - Keep `t14_l7` as the default candidate.

Rejected global go-first setup policy:

- Motivation:
  - `t14_l7` always chooses second, which fits the Cinderace opening plan, but Ketchum Alt and mirror outcomes were weak enough to recheck the global first/second policy.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_gofirst`
  - Code change: in `SelectContext.IS_FIRST`, choose first instead of second.
  - Deck: unchanged from `t14_l7`.
- Light all-bucket check:
  - Output: `analysis_outputs/repeat_gofirst_all_g12r2_seed418000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.8076`, `gofirst` `0.7730`
  - Public sample 2026-07-02 top20: `t14_l7` `0.8109`, `gofirst` `0.7750`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8287`, `gofirst` `0.8027`
  - Equal public buckets: `t14_l7` `0.8317`, `gofirst` `0.8189`
  - Ketchum Alt: `t14_l7` `24 / 48` (`0.5000`), `gofirst` `32 / 48` (`0.6667`)
  - Starmie: `t14_l7` `45 / 48` (`0.9375`), `gofirst` `40 / 48` (`0.8333`)
  - Ogerpon Cornerstone: `t14_l7` `41 / 48` (`0.8542`), `gofirst` `35 / 48` (`0.7292`)
  - Errors: `0`
- Decision:
  - Reject. The Ketchum gain is not exploitable because the agent cannot see the opponent deck before the first/second choice, and broad public-sample proxies worsened.
  - Keep the default choose-second setup policy.

Alt-deck pivot recheck after `t14_l7`:

- Motivation:
  - Local rule probes on `t14_l7` are mostly failing, so retained Great Tusk and Marnie branches were rechecked as possible environment pivots.
- Candidates:
  - `submission_great_tusk_crustle_setupaz_targeted19_marnieexplorer`
  - `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr`
  - `submission_marnie_variant_kazuki_boss2`
  - Baseline: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7`
- Light all-bucket check:
  - Output: `analysis_outputs/repeat_arch_vs_altdecks_all_g8r2_seed419000_summary.csv`
  - Public sample 2026-07-02:
    - `t14_l7` `0.8232`
    - `gt_marnieexplorer` `0.7829`
    - `gt_cutterr` `0.7895`
    - `marnie_kazuki_boss2` `0.4433`
  - Public sample 2026-07-03 top20:
    - `t14_l7` `0.8542`
    - `gt_marnieexplorer` `0.7613`
    - `gt_cutterr` `0.7552`
    - `marnie_kazuki_boss2` `0.3802`
  - Equal public buckets:
    - `t14_l7` `0.8486`
    - `gt_marnieexplorer` `0.7404`
    - `gt_cutterr` `0.7236`
    - `marnie_kazuki_boss2` `0.4856`
  - Ketchum Alt:
    - `t14_l7` `21 / 32` (`0.6562`)
    - `gt_marnieexplorer` `30 / 32` (`0.9375`)
    - `gt_cutterr` `27 / 32` (`0.8438`)
  - Starmie:
    - `t14_l7` `28 / 32` (`0.8750`)
    - `gt_marnieexplorer` `15 / 32` (`0.4688`)
    - `gt_cutterr` `14 / 32` (`0.4375`)
  - Ogerpon Cornerstone:
    - `t14_l7` `27 / 32` (`0.8438`)
    - `gt_marnieexplorer` `14 / 32` (`0.4375`)
    - `gt_cutterr` `18 / 32` (`0.5625`)
  - Errors: `0`
- Decision:
  - Do not switch away from `t14_l7` for broad or uncertain queues.
  - Great Tusk remains a possible field-read pivot only if the live queue is strongly Ketchum/Alakazam/Archaludon-heavy and clearly low on Starmie, Cornerstone Ogerpon, and Chandelure.
  - The local Marnie branch is not competitive against the current proxy set.

Rejected setup-bench Duraludon probes on top of `t14_l7`:

- Motivation:
  - Some live and local losses look like board-collapse games, but older setup-bench probes were tested on older deck/rule branches.
  - Retest a narrower rule on top of `t14_l7`: only bench a setup Duraludon behind an active Cinderace, rather than benching broadly.
- Candidate 1:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_setupcinder_dura1`
  - Rule: during setup bench selection, if active is `Cinderace (666)`, bench is empty, and `Duraludon (169)` is available, bench exactly one Duraludon.
- Candidate 2:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_setupcinder_dura1_hasex`
  - Same as candidate 1, but only when `Archaludon ex (190)` is already in hand.
- First all-bucket check:
  - Output: `analysis_outputs/repeat_setupcinder_dura1_all_g16r2_seed420000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.7985`, `setupcinder_dura1` `0.8100`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8030`, `setupcinder_dura1` `0.8385`
  - Equal public buckets: `t14_l7` `0.8293`, `setupcinder_dura1` `0.8401`
  - Ogerpon: `t14_l7` `42 / 64` (`0.6562`), `setupcinder_dura1` `51 / 64` (`0.7969`)
- Focused confirmation:
  - Output: `analysis_outputs/repeat_setupcinder_dura1_focus_g50r3_seed421000_summary.csv`
  - Alakazam: `t14_l7` `251 / 300` (`0.8367`), `setupcinder_dura1` `260 / 300` (`0.8667`)
  - Ketchum Alt: `t14_l7` `182 / 300` (`0.6067`), `setupcinder_dura1` `196 / 300` (`0.6533`)
  - Ogerpon: `t14_l7` `203 / 300` (`0.6767`), `setupcinder_dura1` `224 / 300` (`0.7467`)
  - Starmie: `t14_l7` `265 / 300` (`0.8833`), `setupcinder_dura1` `275 / 300` (`0.9167`)
  - Archaludon mirror: `t14_l7` `146 / 300` (`0.4867`), `setupcinder_dura1` `137 / 300` (`0.4567`)
- All-bucket confirmation:
  - Output: `analysis_outputs/repeat_setupcinder_dura1_all_confirm_g20r2_seed422000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.8092`, `setupcinder_dura1` `0.7977`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8219`, `setupcinder_dura1` `0.8208`
  - Equal public buckets: `t14_l7` `0.8404`, `setupcinder_dura1` `0.8375`
  - Alakazam fell in this pass: `t14_l7` `71 / 80` (`0.8875`), `setupcinder_dura1` `64 / 80` (`0.8000`)
- Narrow `hasex` check:
  - Output: `analysis_outputs/repeat_setupcinder_hasex_all_g12r2_seed423000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.8257`, `setupcinder_hasex` `0.8087`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8409`, `setupcinder_hasex` `0.8281`
  - Equal public buckets: `t14_l7` `0.8494`, `setupcinder_hasex` `0.8429`
  - Ketchum Alt improved in this small pass, but normal Ogerpon and public proxies fell.
  - Errors across these checks: `0`
- Decision:
  - Reject both setup-bench variants for broad use.
  - The unrestricted Cinderace-behind-Duraludon rule produced attractive Ogerpon/Starmie/Ketchum runs, but the all-bucket confirmations did not reproduce broad improvement.
  - The `hasex` narrower trigger removed some downside but also lost the useful Ogerpon/public-sample signal.
  - Keep `t14_l7` as the default candidate.

Rejected parameter probes on top of `t14_l7`:

- Motivation:
  - Move from hand-written one-off edits toward small, reproducible rule-weight sweeps.
  - Check whether broad tactical priorities can improve the current default without changing the 60-card list.
- Helper:
  - `tools/generate_archaludon_param_variants.py`
  - Generates exact-copy candidates from a base submission directory and applies narrow string-replacement recipes.
- Generated candidates:
  - `submission_archaludon_param_t14_takeboss6500`: raise generic `take Boss's Orders` score from `2500` to `6500`.
  - `submission_archaludon_param_t14_takefml8000`: raise generic `take Full Metal Lab` score from `5000` to `8000`.
  - `submission_archaludon_param_t14_ubempty1500`: raise empty-bench Ultra Ball target score from `300` to `1500`.
  - `submission_archaludon_param_t14_ubempty3500`: raise empty-bench Ultra Ball target score from `300` to `3500`.
  - `submission_archaludon_param_t14_benchboss8500`: raise generic bench-KO Boss line from `4000 + pv * 200 + energy * 100` to `8500 + pv * 400 + energy * 200`.
  - `submission_archaludon_param_t14_lillie7500`: raise generic Lillie's Determination score from `5000` to `7500`.
  - `submission_archaludon_param_t14_benchboss8500_ubempty3500`: combine the bench-KO Boss and empty-bench Ultra Ball changes.
- Light all-bucket sweep:
  - Output: `analysis_outputs/repeat_param_sweep_t14_all_g6r2_seed424000_summary.csv`
  - `benchboss8500` looked best in this pass:
    - Public sample 2026-07-02: `t14_l7` `0.7840`, `benchboss8500` `0.8268`
    - Public sample 2026-07-03 top20: `t14_l7` `0.7731`, `benchboss8500` `0.8507`
    - Equal public buckets: `t14_l7` `0.8173`, `benchboss8500` `0.8622`
    - Ogerpon toolbox: `t14_l7` `0.7692`, `benchboss8500` `0.8397`
  - `ubempty3500` also looked positive in this pass, especially public sample and Starmie-heavy buckets.
  - `takeboss6500`, `takefml8000`, `ubempty1500`, and `lillie7500` were weaker or mixed.
- Promising-candidate rerun:
  - Output: `analysis_outputs/repeat_param_promising_all_g16r2_seed425000_summary.csv`
  - `benchboss8500` reproduced a broad gain:
    - Public sample 2026-07-02: `t14_l7` `0.7743`, `benchboss8500` `0.7993`
    - Public sample 2026-07-03 top20: `t14_l7` `0.7830`, `benchboss8500` `0.8251`
    - Equal public buckets: `t14_l7` `0.8149`, `benchboss8500` `0.8365`
  - But it worsened Cornerstone Ogerpon in that pass: `t14_l7` `57 / 64`, `benchboss8500` `50 / 64`.
  - `ubempty3500` was also positive but still had matchup-specific concerns.
- Combo rerun:
  - Output: `analysis_outputs/repeat_param_combo_all_g12r2_seed426000_summary.csv`
  - `combo` looked attractive in one all-bucket run:
    - Public sample 2026-07-02: `t14_l7` `0.7758`, `combo` `0.8147`
    - Public sample 2026-07-03 top20: `t14_l7` `0.7911`, `combo` `0.8241`
    - Starmie-heavy: `t14_l7` `0.7688`, `combo` `0.8250`
    - Archaludon mirror improved: `t14_l7` `24 / 48`, `combo` `31 / 48`
  - But Ogerpon toolbox fell: `t14_l7` `0.8237`, `combo` `0.7933`.
- Focused confirmation of combo:
  - Output: `analysis_outputs/repeat_param_combo_focus_g50r2_seed427000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.7608`, `combo` `0.7356`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8115`, `combo` `0.7829`
  - Equal public buckets: `t14_l7` `0.7856`, `combo` `0.7762`
  - Starmie: `t14_l7` `185 / 200` (`0.9250`), `combo` `171 / 200` (`0.8550`)
  - Marnie: `t14_l7` `181 / 200` (`0.9050`), `combo` `172 / 200` (`0.8600`)
  - Chandelure: `t14_l7` `184 / 200` (`0.9200`), `combo` `190 / 200` (`0.9500`)
  - Cornerstone Ogerpon: `t14_l7` `150 / 200` (`0.7500`), `combo` `157 / 200` (`0.7850`)
  - Errors: `0`
- Decision:
  - Reject the combo for broad use.
  - The early public-sample gains did not reproduce in the focused confirmation, and the Starmie/Marnie/public drops are too large for a default submission.
  - Keep `t14_l7` as the default candidate.
  - Keep `benchboss8500` as a watchlist idea only; it produced two good broad runs, but the combined and focused checks show enough volatility that it needs a safer, narrower trigger before promotion.

Rejected mirror Relicanth and Starmie FML probes on top of `t14_l7`:

- Motivation:
  - Mirror traces showed the public Archaludon opponent using Relicanth-enabled `Raging Hammer` from damaged `Archaludon ex` for large comeback damage.
  - Starmie-heavy proxy losses suggested Full Metal Lab might be worth preserving more aggressively against Mega Starmie ex.
- Trace sample:
  - Output: `analysis_outputs/trace_t14_l7_arch_g12_seed428000_summary.csv`
  - `t14_l7` vs public Archaludon: `10 / 24` (`0.4167`) in this trace sample.
  - In one losing mirror trace, the opponent's `Archaludon ex` used `Raging Hammer (224)` for `300` damage with Relicanth on board.
  - Score traces also showed several `save Boss: can KO Active` choices while Relicanth remained available on the opposing bench.
- Candidate 1:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_mirrorrelicprio20`
  - Rule: raise existing `Boss: remove mirror Relicanth` play score from `15500` to `20500`.
- Candidate 2:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_mirrorrelic_nonexactive`
  - Rule: when the opponent Active is non-ex and KO-able, allow Boss on killable bench Relicanth instead of taking the non-ex Active.
- Mirror check:
  - Output: `analysis_outputs/repeat_mirrorrelic_arch_g60r2_seed429000_summary.csv`
  - `t14_l7`: `127 / 240` (`0.5292`)
  - `mirrorrelicprio20`: `122 / 240` (`0.5083`)
  - `mirrorrelic_nonexactive`: `118 / 240` (`0.4917`)
  - Errors: `0`
- Decision:
  - Reject both Relicanth Boss probes.
  - Removing Relicanth is strategically attractive, but forcing that line loses too much tempo or gives up better Active KOs in local mirror tests.

- Candidate 3:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_starmiefmlkeep`
  - Rule: against detected Starmie, score `Full Metal Lab` higher in `TO_HAND` selection and avoid discarding it while no Full Metal Lab is in play.
- Starmie check:
  - Output: `analysis_outputs/repeat_starmiefmlkeep_starmie_g80r2_seed430000_summary.csv`
  - `t14_l7`: `275 / 320` (`0.8594`)
  - `starmiefmlkeep`: `274 / 320` (`0.8562`)
  - Errors: `0`
- Decision:
  - Reject.
  - The existing line already plays Full Metal Lab well enough; preserving it harder gives no measurable gain and slightly reduces flexibility.

Rejected FML-aware Boss KO estimate on top of `t14_l7`:

- Motivation:
  - Recheck an older semantically accurate idea on the current default: Boss / target-selection KO estimates should subtract Full Metal Lab's `-30` when the target is a Metal Pokemon.
  - This only changes KO checks used by Boss play and Boss target selection; it does not change attack scoring or the deck.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_fmlbossko`
  - Add `fml_in_play()` and `estimated_damage_to()` helpers.
  - Replace Boss-related `effective_damage(...) >= hp` checks with `estimated_damage_to(...) >= hp`.
- First focus:
  - Output: `analysis_outputs/repeat_fmlbossko_focus_g50r2_seed431000_summary.csv`
  - `Archaludon`: `t14_l7` `97 / 200` (`0.4850`), `fmlbossko` `93 / 200` (`0.4650`)
  - `Starmie`: `t14_l7` `170 / 200` (`0.8500`), `fmlbossko` `175 / 200` (`0.8750`)
  - `Cornerstone Ogerpon`: `t14_l7` `161 / 200` (`0.8050`), `fmlbossko` `175 / 200` (`0.8750`)
- All-bucket check:
  - Output: `analysis_outputs/repeat_fmlbossko_all_g16r2_seed432000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.8084`, `fmlbossko` `0.8146`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8273`, `fmlbossko` `0.8312`
  - Equal public buckets: `t14_l7` `0.8305`, `fmlbossko` `0.8317`
  - But Starmie fell from `57 / 64` to `51 / 64`, Great Tusk fell from `57 / 64` to `52 / 64`, and Marnie fell from `59 / 64` to `56 / 64`.
- Focused confirmation:
  - Output: `analysis_outputs/repeat_fmlbossko_focus2_g40r2_seed433000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.7477`, `fmlbossko` `0.7281`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8021`, `fmlbossko` `0.7903`
  - Equal public buckets: `t14_l7` `0.7417`, `fmlbossko` `0.7365`
  - Archaludon: `t14_l7` `71 / 160` (`0.4437`), `fmlbossko` `66 / 160` (`0.4125`)
  - Ogerpon: `t14_l7` `111 / 160` (`0.6937`), `fmlbossko` `117 / 160` (`0.7312`)
  - Ketchum Alt: `t14_l7` `100 / 160` (`0.6250`), `fmlbossko` `104 / 160` (`0.6500`)
  - Starmie: `t14_l7` `145 / 160` (`0.9062`), `fmlbossko` `137 / 160` (`0.8562`)
  - Marnie: `t14_l7` `147 / 160` (`0.9187`), `fmlbossko` `142 / 160` (`0.8875`)
  - Errors: `0`
- Decision:
  - Reject for broad use.
  - The code is semantically cleaner for Metal targets, but the Archaludon-mirror gain did not reproduce and the public-sample confirmation moved negative.
  - Treat non-Metal matchup differences as stochastic engine noise unless a larger same-code control proves otherwise.
  - Keep `t14_l7` as the default candidate.

Promoted local candidate: Ketchum pivot Boss rule on top of `t14_l7`:

- Motivation:
  - Ketchum Alt traces remain one of the lower buckets for `t14_l7`.
  - New trace output: `analysis_outputs/trace_t14_l7_ketchum_g20_seed434000_summary.csv`
  - `t14_l7` went `23 / 40` (`0.5750`) in this trace sample.
  - The 17 losses almost always ended with no Active Pokemon and an empty or very thin bench while opposing `Alakazam (743)` remained Active.
  - Previous broad Alakazam Boss probes were rejected because they hurt normal Alakazam, but the current trace again showed Ketchum's pivot pattern: `Dunsparce (65)` / `Dudunsparce (66)` buying time while Alakazam-line attackers sit on the bench.
- Candidate:
  - Directory: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_ketchumpivotboss`
  - Archive: `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_ketchumpivotboss.tar.gz`
  - Deck: unchanged from `t14_l7`.
  - Rule:
    - Detect Ketchum Alt only when `Dunsparce (65)` is visible with an Alakazam-line Pokemon.
    - If the opponent Active is a pivot `65` or `66` and a benched `Kadabra (742)` / `Alakazam (743)` is KO-able, raise Boss's Orders priority.
    - In Boss target selection, prefer those KO-able benched Alakazam-line targets.
- Focused Alakazam check:
  - Output: `analysis_outputs/repeat_ketchumpivotboss_alak_g60r2_seed435000_summary.csv`
  - Normal Alakazam: `t14_l7` `203 / 240` (`0.8458`), `ketchumpivotboss` `203 / 240` (`0.8458`)
  - Ketchum Alt: `t14_l7` `141 / 240` (`0.5875`), `ketchumpivotboss` `150 / 240` (`0.6250`)
  - Errors: `0`
- Light all-bucket check:
  - Output: `analysis_outputs/repeat_ketchumpivotboss_all_g12r2_seed436000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.7505`, `ketchumpivotboss` `0.7697`
  - Public sample 2026-07-03 top20: `t14_l7` `0.7720`, `ketchumpivotboss` `0.7807`
  - Equal public buckets: both `0.8189`
  - Ketchum Alt: `t14_l7` `29 / 48` (`0.6042`), `ketchumpivotboss` `31 / 48` (`0.6458`)
  - Starmie looked worse in this small run, but the Ketchum rule should not trigger there.
- Starmie side check:
  - Output: `analysis_outputs/repeat_ketchumpivotboss_starmie_g80r2_seed437000_summary.csv`
  - Starmie: `t14_l7` `277 / 320` (`0.8656`), `ketchumpivotboss` `278 / 320` (`0.8688`)
  - This supports treating the earlier Starmie drop as local-engine variance rather than a real rule side effect.
- All-bucket confirmation:
  - Output: `analysis_outputs/repeat_ketchumpivotboss_all_confirm_g20r2_seed438000_summary.csv`
  - Public sample 2026-07-02: `t14_l7` `0.7937`, `ketchumpivotboss` `0.8211`
  - Public sample 2026-07-03 top20: `t14_l7` `0.8066`, `ketchumpivotboss` `0.8437`
  - Equal public buckets: `t14_l7` `0.8154`, `ketchumpivotboss` `0.8490`
  - Ketchum Alt: `t14_l7` `40 / 80` (`0.5000`), `ketchumpivotboss` `48 / 80` (`0.6000`)
  - Ogerpon toolbox: `t14_l7` `0.7750`, `ketchumpivotboss` `0.8192`
  - Starmie-heavy: `t14_l7` `0.7288`, `ketchumpivotboss` `0.8025`
  - Normal Alakazam moved down slightly in this pass: `68 / 80` to `66 / 80`, so keep watching it in future runs.
- Trigger trace:
  - Output: `analysis_outputs/trace_ketchumpivotboss_ketchum_g12_seed439000_summary.csv`
  - Score traces show the new reason `Ketchum: Boss bench Alakazam line` firing and selecting a benched `Kadabra (742)` over pivot targets.
- Decision:
  - Promote `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_ketchumpivotboss.tar.gz` as the next local candidate.
  - Do not submit automatically; use it as the next candidate if the user wants another submission or if live losses continue to show Ketchum/Alakazam pivot patterns.
  - Keep `t14_l7` as the conservative fallback because the improvement is still based on local proxies and the engine has visible variance.

Rechecked and demoted `ketchumpivotboss` after a larger opposite-seed Alakazam pass:

- Reason:
  - The first focused pass and all-bucket confirmation were positive, but the rule fires rarely and may be dominated by native-engine variance.
  - Before treating it as the next default, rerun normal Alakazam and Ketchum Alt with a different seed at higher volume.
- Confirmation:
  - Output: `analysis_outputs/repeat_ketchumpivotboss_alak_confirm_g80r2_seed440000_summary.csv`
  - Normal Alakazam: `t14_l7` `269 / 320` (`0.8406`), `ketchumpivotboss` `266 / 320` (`0.8313`)
  - Ketchum Alt: `t14_l7` `211 / 320` (`0.6594`), `ketchumpivotboss` `196 / 320` (`0.6125`)
  - Equal Alakazam-only buckets: `t14_l7` `0.7500`, `ketchumpivotboss` `0.7219`
  - Errors: `0`
- Trace check:
  - Output: `analysis_outputs/trace_compare_ketchumpivot_seed441000_summary.csv`
  - `t14_l7` and `ketchumpivotboss` both went `29 / 40` (`0.7250`) against Ketchum Alt.
  - `analysis_outputs/trace_compare_ketchumpivot_seed441000_score_reason_games.csv` showed no `Ketchum: Boss` trigger in that trace sample.
- Decision:
  - Demote `ketchumpivotboss` from promoted local candidate to unstable specialist idea.
  - Keep the archive for future live-log-specific use, but do not treat it as the broad next submission.
  - Restore `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7.tar.gz` as the conservative local baseline.

Rejected Ogerpon active-Cornerstone ex-evolution guards on top of `t14_l7`:

- Motivation:
  - Fresh Ogerpon loss traces often ended with our board empty while opposing `Cornerstone Mask Ogerpon ex (117)` remained active.
  - A previous branch benefited from an active-Cornerstone-only `Archaludon ex` evolution guard, but that branch had different Ogerpon detection and low-deck policy.
- Candidates:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_oger_active_exblock`
    - Rule: in detected Ogerpon matchups, if opponent Active is `117`, score `Duraludon -> Archaludon ex` at `-10000`.
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_oger_active_exblock_toolboxonly`
    - Same rule, but disable it when Cornerstone/Sylveon-style side-line IDs `{134, 712, 713, 748}` are visible.
- Focused Ogerpon-family check:
  - Output: `analysis_outputs/repeat_oger_active_exblock_oger3_g40r2_seed443000_summary.csv`
  - Normal Ogerpon: `t14_l7` `117 / 160` (`0.7312`), `oger_active_exblock` `124 / 160` (`0.7750`)
  - Raging Bolt Ogerpon: `157 / 160` (`0.9812`) to `153 / 160` (`0.9563`)
  - Cornerstone Ogerpon: `134 / 160` (`0.8375`) to `127 / 160` (`0.7937`)
  - Equal Ogerpon-family buckets: `0.8500` to `0.8417`
- Narrow-version check:
  - Output: `analysis_outputs/repeat_oger_exblock_toolboxonly_oger3_g40r2_seed444000_summary.csv`
  - Normal Ogerpon: `t14_l7` `112 / 160` (`0.7000`), `exblock_toolboxonly` `114 / 160` (`0.7125`)
  - Raging Bolt Ogerpon: both `156 / 160` (`0.9750`)
  - Cornerstone Ogerpon: `136 / 160` (`0.8500`) to `127 / 160` (`0.7937`)
  - Equal Ogerpon-family buckets: `0.8417` to `0.8271`
- Decision:
  - Reject both.
  - The active-Cornerstone guard can help the normal Ogerpon proxy, but it repeatedly gives up too much against the dedicated Cornerstone proxy.
  - Keep `t14_l7` unchanged.

Rejected Relicanth one-slot restore with `-1 Jumbo Ice Cream` on top of `t14_l7`:

- Motivation:
  - Mirror traces still show opposing Relicanth enabling high-damage `Raging Hammer`.
  - `t14_l7` had already rejected `+1 Relicanth, -1 non-ex Archaludon` and `+1 Relicanth, -1 Cinderace`.
  - Check the remaining obvious one-card slot: `+1 Relicanth (57), -1 Jumbo Ice Cream (1147)`.
- Candidate:
  - `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7_relic1_cutice`
  - Deck-only change: one `1147` replaced with `57`.
- Focused check:
  - Output: `analysis_outputs/repeat_t14_relic1_cutice_focus_g40r2_seed446000_summary.csv`
  - Archaludon mirror: `t14_l7` `73 / 160` (`0.4562`), `relic1_cutice` `72 / 160` (`0.4500`)
  - Normal Ogerpon: `118 / 160` (`0.7375`) to `113 / 160` (`0.7063`)
  - Cornerstone Ogerpon: `121 / 160` (`0.7562`) to `118 / 160` (`0.7375`)
  - Starmie: `148 / 160` (`0.9250`) to `145 / 160` (`0.9062`)
  - Normal Alakazam: `122 / 160` (`0.7625`) to `121 / 160` (`0.7562`)
  - Errors: `0`
- Decision:
  - Reject.
  - Restoring one Relicanth by cutting Ice Cream did not improve the mirror and slightly worsened every checked side bucket.
  - Keep `t14_l7` as the current local baseline.

## 2026-07-05 Submission Attempt And Bench-Boss Gating Pass

Submission attempt:

- Tried to submit `submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7.tar.gz` with the message `Archaludon t14_l7 conservative local baseline after rejecting Ketchum/Oger/Relicanth probes`.
- Kaggle CLI uploaded the file but returned `400 Client Error: Bad Request`.
- A follow-up `kaggle competitions submissions -c pokemon-tcg-ai-battle` check showed no new row.
- Likely cause: the 2026-07-04 UTC submission quota was already full with five complete submissions.
- Keep `t14_l7` as the conservative pending-submit fallback until the quota resets.

Rejected broad `benchboss8500` gating variants:

- Motivation:
  - Earlier parameter sweeps showed occasional gains from raising generic bench-KO Boss scoring from `4000 + pv * 200 + energy * 100` to `8500 + pv * 400 + energy * 200`.
  - The broad version was volatile, especially around Starmie-heavy and Ogerpon/Cornerstone mixes.
- Candidates:
  - `submission_archaludon_param_t14_benchboss8500_nocorner`
    - Use high bench-KO Boss score except when Ogerpon is detected and `Cornerstone Mask Ogerpon ex (117)` is visible.
  - `submission_archaludon_param_t14_benchboss8500_nonoger`
    - Use high bench-KO Boss score only outside detected Ogerpon matchups.
  - `submission_archaludon_param_t14_benchboss8500_safegate`
    - Revert to baseline in `starmie`, `archaludon`, `alakazam`, or visible-`117` Ogerpon states.
  - `submission_archaludon_param_t14_benchboss8500_visiblegood`
    - Use high score only for visible `crustle`/Great Tusk, `lucario`, `chandelure`, or Ogerpon without visible `117`.
- Broad screen:
  - Output: `analysis_outputs/repeat_benchboss_safe_all_g16r2_seed447000_summary.csv`
  - `nocorner` improved `equal_public_buckets` from `0.8329` to `0.8413`, but dropped Starmie from `61 / 64` to `50 / 64` and Starmie-heavy from `0.8156` to `0.6859`.
  - `nonoger` improved Ketchum Alt from `36 / 64` to `45 / 64`, but dropped public 2026-07-02 from `0.8133` to `0.7845`.
  - Global `benchboss8500` was roughly flat on equal buckets and worse on public 2026-07-02 / Starmie-heavy.
- Safer gate screen:
  - Output: `analysis_outputs/repeat_benchboss_safegate_all_g24r2_seed448000_summary.csv`
  - `safegate` improved equal buckets `0.8221` to `0.8301`, but dropped Archaludon from `52 / 96` to `40 / 96` and Ogerpon toolbox from `0.8189` to `0.8013`.
- Visible-good screen and confirmation:
  - First output: `analysis_outputs/repeat_benchboss_visiblegood_all_g20r2_seed449000_summary.csv`
  - First pass looked strong: public 2026-07-02 `0.7615` to `0.8270`, public 2026-07-03 top20 `0.7896` to `0.8615`, equal buckets `0.8183` to `0.8471`.
  - Confirmation output: `analysis_outputs/repeat_benchboss_visiblegood_focus_g30r2_seed450000_summary.csv`
  - The broad gain did not reproduce: public 2026-07-02 fell `0.8113` to `0.7885`; equal buckets were flat `0.8108` to `0.8100`.
- Decision:
  - Reject the broad bench-Boss variants.
  - The gains are seed- and field-sensitive. The safer gates still leak early or matchup-specific downside, especially into Archaludon/Starmie/Alakazam style buckets.

Promoted small Ogerpon-only bench-Boss candidate:

- Candidate:
  - Directory: `submission_archaludon_param_t14_benchboss8500_oger_no117`
  - Archive: `submission_archaludon_param_t14_benchboss8500_oger_no117.tar.gz`
  - Deck: unchanged from `t14_l7`.
  - Rule: in detected Ogerpon games, if `Cornerstone Mask Ogerpon ex (117)` is not visible, use the higher bench-KO Boss score `8500 + pv * 400 + energy * 200`; otherwise keep the baseline score.
- Ogerpon-family confirmation:
  - Output: `analysis_outputs/repeat_benchboss_oger_no117_oger3_g60r3_seed451000_summary.csv`
  - Normal Ogerpon: `t14_l7` `258 / 360` (`0.7167`), `oger_no117` `260 / 360` (`0.7222`)
  - Raging Bolt Ogerpon: `352 / 360` (`0.9778`) to `353 / 360` (`0.9806`)
  - Cornerstone Ogerpon: `276 / 360` (`0.7667`) to `282 / 360` (`0.7833`)
  - Ogerpon toolbox scenario: `0.8494` to `0.8574`
  - Errors: `0`
- Decision:
  - Promote as a small local next candidate, not a high-confidence replacement.
  - The measured lift is small, but it is narrowly Ogerpon-gated and did not show Ogerpon-family downside in the larger check.
  - Keep `t14_l7` as the conservative fallback and use `oger_no117` only if we want to submit a slightly more aggressive Ogerpon-targeted variant after the quota resets.

Added local loss-pattern analyzer:

- Tool:
  - `tools/analyze_local_loss_patterns.py`
  - Joins a local `*_games.csv` file with its `*_trace_summary.csv` file and summarizes candidate losses by final Active, bench emptiness, opponent Active, Relicanth/Alakazam bench presence, and key attack patterns.
- Archaludon mirror output:
  - `analysis_outputs/loss_patterns_t14_l7_arch_seed445000.csv`
  - In the checked trace sample, all `11 / 11` `t14_l7` losses ended with no candidate Active.
  - `7 / 11` losses also had an empty candidate bench.
  - `9 / 11` losses had opposing Relicanth still on the bench.
  - `8 / 11` losses included `Raging Hammer`.
- Ketchum Alt output:
  - `analysis_outputs/loss_patterns_t14_l7_ketchum_seed434000.csv`
  - All `17 / 17` losses ended with no candidate Active.
  - `11 / 17` losses had an empty candidate bench.
  - `15 / 17` losses included `Powerful Hand`.
  - Opponent Active was always `Alakazam`.

Rejected narrow damaged-Active Relicanth removal on top of `oger_no117`:

- Motivation:
  - The new loss-pattern analyzer confirmed that mirror losses frequently leave opposing Relicanth on board.
  - Previous Relicanth-priority probes were broad; this one only fires if our Active is a damaged `Archaludon ex` and Relicanth is KO-able.
- Candidate:
  - `submission_archaludon_param_t14_benchboss8500_oger_no117_mirrorrelic_damaged`
  - Rule: in Archaludon mirrors, when Active KO is available but our Active `Archaludon ex` has at least `180` damage and opposing Relicanth is KO-able, play Boss's Orders to remove Relicanth.
- Check:
  - Output: `analysis_outputs/repeat_mirrorrelic_damaged_arch_g60r2_seed452000_summary.csv`
  - `oger_no117`: `125 / 240` (`0.5208`)
  - `mirrorrelic_damaged`: `121 / 240` (`0.5042`)
  - Errors: `0`
- Decision:
  - Reject.
  - Even when narrowed to damaged-Active states, spending Boss on Relicanth loses too much prize-race tempo.
  - Keep `oger_no117` as the only promoted local next candidate.

## 2026-07-05 Ketchum Alakazam Stadium-Ice Probe

Rejected broad Alakazam Ice Cream pickup:

- Candidate:
  - `submission_archaludon_param_t14_benchboss8500_oger_no117_alakice`
  - Rule: during Explorer's Guidance, take `Jumbo Ice Cream (1147)` against any detected Alakazam matchup when the Active `Archaludon ex` is damaged and no Ice Cream is already in hand.
- Checks:
  - First output: `analysis_outputs/repeat_alakice_alak_g60r2_seed453000_summary.csv`
    - Normal Alakazam: `197 / 240` to `207 / 240`
    - Ketchum Alt: `142 / 240` to `147 / 240`
  - Confirmation output: `analysis_outputs/repeat_alakice_alak_confirm_g80r2_seed455000_summary.csv`
    - Normal Alakazam: `267 / 320` to `263 / 320`
    - Ketchum Alt: `200 / 320` to `213 / 320`
- Decision:
  - Reject as too broad.
  - The Ketchum Alt gain reproduced, but normal Alakazam moved the wrong way on confirmation.

Rejected Dunsparce/Ketchum-visible Ice Cream pickup:

- Candidate:
  - `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumice`
  - Rule: take Ice Cream when Alakazam plus Dunsparce/Dudunsparce or Ketchum lock stadiums are visible.
- Check:
  - Output: `analysis_outputs/repeat_ketchumice_alak_g60r2_seed456000_summary.csv`
  - Normal Alakazam: `210 / 240` to `196 / 240`
  - Ketchum Alt: `150 / 240` to `146 / 240`
- Decision:
  - Reject.
  - Dunsparce/Dudunsparce is not a clean Ketchum discriminator in this local proxy set.

Promoted Ketchum-stadium-only Ice Cream pickup:

- Candidate:
  - Directory: `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice`
  - Archive: `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice.tar.gz`
  - Rule: during Explorer's Guidance, take `Jumbo Ice Cream (1147)` only when Alakazam is visible and a Ketchum lock stadium (`1246` or `1247`) is either active or in the opponent discard.
- Focused checks:
  - First output: `analysis_outputs/repeat_ketchumstadice_alak_g60r2_seed457000_summary.csv`
    - Normal Alakazam: `202 / 240` to `206 / 240`
    - Ketchum Alt: `146 / 240` to `153 / 240`
  - Confirmation output: `analysis_outputs/repeat_ketchumstadice_alak_confirm_g80r2_seed458000_summary.csv`
    - Normal Alakazam: `271 / 320` to `275 / 320`
    - Ketchum Alt: `205 / 320` to `208 / 320`
- Side-bucket check:
  - Output: `analysis_outputs/repeat_ketchumstadice_side_g30r2_seed459000_summary.csv`
  - Marnie: `100 / 120` to `102 / 120`
  - Archaludon: `52 / 120` to `56 / 120`
  - Ogerpon: `88 / 120` to `96 / 120`
  - Starmie: `109 / 120` to `108 / 120`
  - Raging Bolt Ogerpon: `117 / 120` to `118 / 120`
  - Cornerstone Ogerpon: `90 / 120` to `92 / 120`
- Decision:
  - Promote as the next submit candidate over plain `oger_no117`.
  - The measured gain is modest and probably contains noise, but the trigger is narrowly Ketchum-stadium gated and the checked non-Alakazam buckets did not show meaningful downside.

Rejected follow-up probes on top of `ketchumstadice`:

- Mirror empty-bench Lillie:
  - Candidate: `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice_mirrorbenchdraw`
  - Motivation: trace `analysis_outputs/trace_ketchumstadice_arch_seed460000` showed many mirror losses ending with no Active and no bench.
  - Rule: in Archaludon mirrors, if the bench is empty and the Active has `<= 220` HP, play Lillie instead of saving it behind Boss/attacker-ready logic.
  - Check: `analysis_outputs/repeat_mirrorbenchdraw_arch_g60r2_seed461000_summary.csv`
  - Result: mirror `ketchumstadice` `118 / 240` (`0.4917`) to `mirrorbenchdraw` `108 / 240` (`0.4500`)
  - Decision: reject. Drawing for backup loses too much attack tempo.
- Mirror empty-bench Ultra Ball:
  - Candidate: `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice_mirrorubempty`
  - Motivation: mirror score traces often contained `Ultra Ball: bench empty (donk risk)` while later losses showed board collapse.
  - Rule: in Archaludon mirrors, with empty bench, no Duraludon in hand, and at most one line Pokemon in play, raise Ultra Ball from `300` to `17500`.
  - Check: `analysis_outputs/repeat_mirrorubempty_arch_g60r2_seed462000_summary.csv`
  - Result: mirror `ketchumstadice` `117 / 240` (`0.4875`) to `mirrorubempty` `102 / 240` (`0.4250`)
  - Decision: reject. Searching for backup in these spots costs more tempo/resources than it saves.
- Generic Ketchum-stadium Ice Cream pickup:
  - Candidate: `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice_takeanyice`
  - Motivation: `ketchumstadice` only took Ice Cream from Explorer; trace-score counts showed the trigger firing rarely.
  - Rule: outside Explorer, take `Jumbo Ice Cream` at score `10000` when Alakazam plus Ketchum lock stadium is visible and Active `Archaludon ex` is damaged.
  - Check: `analysis_outputs/repeat_takeanyice_alak_g60r2_seed464000_summary.csv`
  - Result: normal Alakazam `205 / 240` (`0.8542`) to `197 / 240` (`0.8208`); Ketchum Alt `155 / 240` (`0.6458`) to `157 / 240` (`0.6542`)
  - Decision: reject. The small Ketchum gain is not worth the normal Alakazam loss.

Current pending-submit candidate remains:

- `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice.tar.gz`
- Do not replace it with the three follow-up probes above.

## 2026-07-05 Live-947 Transplant Pass

Compared the current pending `ketchumstadice` line against the live 947.0 submission:

- Live 947 directory:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`
- Current local line:
  - `submission_archaludon_param_t14_benchboss8500_oger_no117_ketchumstadice`
- Light all-bucket comparison:
  - Output: `analysis_outputs/repeat_live947_vs_ketchumstadice_all_g12r2_seed465000_summary.csv`
  - `ketchumstadice` improved Great Tusk, Ogerpon, Cornerstone, and Ketchum Alt, but was weaker on Archaludon mirror, normal Alakazam, and Chandelure-heavy mixes in that pass.
  - Decision: do not assume `ketchumstadice` is strictly better than the live 947 line; try transplanting the narrow useful rules back onto the live 947 base.

Rejected direct Ketchum/Oger no117 transplant onto live 947:

- Candidate:
  - `submission_archaludon_live947_kstadice_ogerno117`
- Rules:
  - Ketchum lock-stadium Explorer Ice Cream pickup.
  - Ogerpon no-visible-117 high bench-KO Boss score.
- Check:
  - Output: `analysis_outputs/repeat_live947_hybrid_kstad_ogerno117_key_g16r2_seed466000_summary.csv`
  - The candidate did not reliably preserve the live 947 baseline and was weaker on several key buckets.
- Decision:
  - Reject this direct transplant.

Promoted live-947 Great Tusk + Ogerpon transplant:

- Candidate:
  - Directory: `submission_archaludon_live947_gtguard_ogerlow_no117`
  - Archive: `submission_archaludon_live947_gtguard_ogerlow_no117.tar.gz`
- Rules:
  - Detect `Great Tusk (58/607)` as a Crustle-style deck pressure matchup.
  - When Great Tusk is visible, preserve deck by suppressing Poke Pad/Pokegear, later Explorer, and late Ultra Ball; allow high-hand Lillie to refill deck earlier.
  - When Ogerpon Cornerstone `117` is visible and non-ex Archaludon is already in play, preserve low deck by suppressing late search/draw.
  - In Ogerpon games without visible `117`, use the higher bench-KO Boss score.
- Focused check:
  - Output: `analysis_outputs/repeat_live947_gt_oger_key_g24r2_seed468000_summary.csv`
  - Great Tusk: live947 `31 / 96` (`0.3229`) to `gt_oger` `76 / 96` (`0.7917`)
  - Ogerpon Cornerstone: `72 / 96` (`0.7500`) to `77 / 96` (`0.8021`)
  - Archaludon: `47 / 96` (`0.4896`) to `52 / 96` (`0.5417`)
  - Starmie moved down in this pass: `86 / 96` (`0.8958`) to `79 / 96` (`0.8229`), but the new rules should not trigger there; treat as a side bucket to monitor.
- Full light check:
  - Output: `analysis_outputs/repeat_live947_gt_oger_all_g16r2_seed470000_summary.csv`
  - Equal public buckets: live947 `0.7812`, `gt_oger` `0.8305`
  - Public sample 2026-07-02: `0.7833` to `0.7706`
  - Public sample 2026-07-03 top20: `0.7830` to `0.7964`
  - Great Tusk: `24 / 64` (`0.3750`) to `57 / 64` (`0.8906`)
  - Archaludon: `23 / 64` (`0.3594`) to `30 / 64` (`0.4688`)
  - Ketchum Alt: `38 / 64` (`0.5938`) to `46 / 64` (`0.7188`) in this pass, despite no Ketchum-specific rule.
  - Normal Alakazam fell `54 / 64` to `50 / 64`; normal Ogerpon fell `42 / 64` to `39 / 64`.
- Decision:
  - Promote `live947_gt_oger` as the next pending-submit candidate over plain `ketchumstadice`, because it keeps the live 947 base while addressing a very weak Great Tusk bucket and improving the Ogerpon/Cornerstone pressure bucket.
  - Monitor normal Alakazam and normal Ogerpon after live submission because light local runs still have visible variance.

Rejected Ketchum Ice on top of `live947_gt_oger`:

- Candidate:
  - `submission_archaludon_live947_gt_oger_kstadice`
- Check:
  - Output: `analysis_outputs/repeat_live947_gt_oger_kstadice_alak_g60r2_seed469000_summary.csv`
  - Normal Alakazam: `198 / 240` (`0.8250`) to `197 / 240` (`0.8208`)
  - Ketchum Alt: `154 / 240` (`0.6417`) to `141 / 240` (`0.5875`)
- Decision:
  - Reject. The Ketchum Ice pickup is actively harmful on this stronger base.

Follow-up ablation for `live947_gt_oger`:

- Candidates:
  - Baseline: `submission_archaludon_live947_greattuskguard`
  - Cornerstone low-deck only: `submission_archaludon_live947_gtguard_cornerlow_only`
  - Ogerpon no-visible-117 Boss only: `submission_archaludon_live947_gtguard_ogerno117_only`
  - Both rules: `submission_archaludon_live947_gtguard_ogerlow_no117`
- Broad ablation:
  - Output: `analysis_outputs/repeat_gtguard_oger_ablation_g32r2_seed472000_summary.csv`
  - `both` vs `gtguard`:
    - Great Tusk: `106 / 128` to `113 / 128`
    - Ogerpon Cornerstone: `92 / 128` to `105 / 128`
    - Ogerpon: `104 / 128` to `91 / 128`
    - Starmie: `110 / 128` to `115 / 128`
    - Alakazam: `107 / 128` to `100 / 128`
    - Equal public buckets: `0.8372` to `0.8451`
- Focused risk confirmation:
  - Output: `analysis_outputs/repeat_gtguard_vs_both_risk_g40r2_seed473000_summary.csv`
  - Ogerpon: `110 / 160` to `130 / 160`
  - Ogerpon Cornerstone: `125 / 160` to `126 / 160`
  - Alakazam: `129 / 160` to `132 / 160`
  - Starmie: `146 / 160` to `137 / 160`
- Decision:
  - Keep `submission_archaludon_live947_gtguard_ogerlow_no117.tar.gz` as the next pending-submit candidate.
  - The direct Ogerpon/Alakazam risk check supports the combined rule, and Starmie movement is likely local variance because the diff from `gtguard` is only Ogerpon-triggered logic.
  - Submit after the Kaggle daily quota resets; at `2026-07-05 04:39 JST`, the 2026-07-04 UTC submission window still contains five submissions.

RL lane note:

- Kaggle Notebook GPU/TPU can help once a policy/value network is introduced, but the current local battle engine is CPU-bound for self-play generation.
- The practical order is:
  - generate and label many CPU self-play/replay states;
  - train a small policy/value model on Kaggle GPU;
  - distill the model back into cheap rule weights or a lightweight inference module that fits submission limits.

## 2026-07-05 Follow-up Rule Probes Before Quota Reset

The pending-submit candidate remains:

- `submission_archaludon_live947_gtguard_ogerlow_no117.tar.gz`

Rejected probes:

- Mirror Relicanth Boss priority:
  - Candidate: `submission_archaludon_live947_gtoger_mirrorrelic19`
  - Change: raise `Boss: remove mirror Relicanth` from `15500` to `19000`.
  - Check: `analysis_outputs/repeat_gtoger_mirrorrelic19_arch_g24r2_seed477000_summary.csv`
  - Result: Archaludon mirror `49 / 96` to `44 / 96`.
  - Decision: reject. Bossing Relicanth earlier costs too much tempo.
- Add Relicanth back to the deck:
  - Candidates:
    - `submission_archaludon_live947_gtoger_relic1_cutice`
    - `submission_archaludon_live947_gtoger_relic1_cutnonex`
  - Check: `analysis_outputs/repeat_gtoger_relic1_arch_g32r2_seed478000_summary.csv`
  - Results:
    - Base mirror `70 / 128`
    - `relic1_cutice` `49 / 128`
    - `relic1_cutnonex` `66 / 128`
  - Decision: reject both. Relicanth does not improve this base, and cutting Ice Cream is especially harmful.
- Alakazam empty-bench Ultra Ball rescue:
  - Candidate: `submission_archaludon_live947_gtoger_alakubempty`
  - Change: only versus Alakazam, allow empty-bench Ultra Ball at score `18000` when `safe_discard_count >= 2` and another Duraludon line is needed.
  - Check: `analysis_outputs/repeat_gtoger_alakubempty_g40r2_seed480000_summary.csv`
  - Result: Alakazam `130 / 160` to `123 / 160`.
  - Decision: reject. Searching a backup line from these positions loses more tempo than it saves.
- Ogerpon second non-ex Archaludon search:
  - Candidate: `submission_archaludon_live947_gtoger_ogernonex2search`
  - Change: `need_nonex_archaludon` asks for two non-ex Archaludon in Ogerpon matchups instead of stopping after one.
  - Check: `analysis_outputs/repeat_gtoger_ogernonex2_g32r2_seed483000_summary.csv`
  - Results:
    - Ogerpon `92 / 128` to `96 / 128`
    - Cornerstone `105 / 128` to `98 / 128`
    - Raging Bolt `123 / 128` to `120 / 128`
  - Decision: reject. The normal Ogerpon gain is not worth the Cornerstone/Raging Bolt loss.

Trace-only observations:

- Starmie trace check: `analysis_outputs/trace_both_starmie_seed474000_summary.csv`
  - `22 / 24`; no rule change found.
- Great Tusk trace check: `analysis_outputs/trace_both_gt_seed481000_summary.csv`
  - `29 / 32`; remaining losses are long-game edge cases, not enough evidence for a safer threshold change.

## 2026-07-05 Public Notebook Check: Koushikrudra Great Tusk / Crustle LO

Source:

- Notebook: `https://www.kaggle.com/code/koushikrudra/i-have-one-rear-card`
- Kaggle CLI pull: `external/koushikrudra_i_have_one_rear_card`
- Local imported opponent: `meta_agents/koushikrudra_i_have_one_rear_card`

Notebook facts:

- Public Kaggle code title: `I have one REAR card`
- Kaggle page showed a silver notebook medal and 59 votes.
- Kaggle kernels search showed direct/near title copies:
  - `koushikrudra/i-have-one-rear-card`
  - `makthanithin/i-have-one-rear-card`
  - `seokjeongeum/i-have-one-rear-card-0b024f`
- Great Tusk search also showed related LO notebooks such as `[Max Elo: 1208] LibraryOut w/ Crustle & Great Tusk`.

Extracted deck:

- `58` Great Tusk x4
- `344/345` Dwebble/Crustle x4/x4
- `607` Terrakion x1
- Support/control shell:
  - Fighting Gong x4, Pokegear x4, Switch x4, Poke Pad x4
  - Explorer's Guidance x4, Xerosic's Machinations x4, Boss's Orders x4, Lisia's Appeal x2
  - Colress's Tenacity x2, Neutralization Zone x1, Jumbo Ice Cream x1
  - Rock Fighting Energy x4, Mist Energy x4

Direct local check against pending Archaludon candidate:

- Candidate: `submission_archaludon_live947_gtguard_ogerlow_no117`
- Opponent: `meta_agents/koushikrudra_i_have_one_rear_card`
- Outputs:
  - `analysis_outputs/current_vs_koushik_488000_summary.jsonl`
  - `analysis_outputs/koushik_vs_current_489000_summary.jsonl`
- Result:
  - Current as player A: `36 / 40`
  - Current as player B: `35 / 40`
  - Combined: `71 / 80` (`0.8875`)

Loss pattern:

- Most losses are still Great Tusk/Crustle long-game edge cases:
  - a few no-active/no-bench collapses after failing to keep attackers chained;
  - a few deckout races where both decks are near zero and turn order decides the result.
- The existing Great Tusk deck-preservation rule is already doing useful work; this notebook is not a new hard counter to the pending candidate.

Decision:

- Treat Koushikrudra Great Tusk / Crustle LO as an important live-meta bucket because it is public, silver-medal, heavily voted, and has visible copies.
- Do not pivot the deck solely for this notebook: the pending candidate already wins the extracted exact notebook proxy at about 89%.
- If live battle history shows many Great Tusk/Crustle losses anyway, next useful work is not a broad deck change but a narrow anti-LO polish:
  - avoid the remaining self-deckout cases a little earlier;
  - preserve one extra backup attacker line when Great Tusk plus Crustle is visible;
  - verify against normal Great Tusk, Archaludon mirror, and Starmie so the patch does not trade away broader equity.

Rejected follow-up probe:

- Candidate: `submission_archaludon_live947_gtoger_gtallowex`
- Idea: the exact Koushik losses sometimes ended with Duraludon-only board collapse, so test allowing `Archaludon ex` evolution when Great Tusk is visible instead of applying the broad Crustle `do not evolve to ex` rule.
- Result against the extracted Koushik notebook proxy:
  - Base candidate: `71 / 80` (`0.8875`)
  - `gtallowex`: `45 / 80` (`0.5625`)
- Decision: reject. Allowing `Archaludon ex` in this LO matchup creates more long games and deckout losses. The existing Crustle/Great Tusk ex-evolution ban is an important part of why the current candidate already beats this public notebook.

## 2026-07-05 Live 947 Ogerpon Non-ex Ice Cream Probe

Rejected mirror probe:

- Candidate: `submission_archaludon_live947_gtoger_mirrorrelic_latebehind`
- Idea: in Archaludon mirrors, if we are at least three prizes behind and can KO opposing benched `Relicanth`, use Boss even when Active KO is available.
- Focused mirror output: `analysis_outputs/repeat_latebehind_arch_g60r2_seed490000_summary.csv`
- Result: base `104 / 240`, `latebehind` `95 / 240`.
- Decision: reject. Even late Relicanth Bossing gives up too much tempo.

Rejected Ogerpon Boss cash-out probe:

- Candidate: `submission_archaludon_live947_gtoger_ogerbosskillable`
- Idea: when damaged non-ex `Archaludon` faces active Cornerstone `117`, use Boss to take an immediately KO-able non-Cornerstone bench target before being KO'd.
- Focused Ogerpon output: `analysis_outputs/repeat_ogercash_oger_g40r2_seed491000_summary.csv`
- Results:
  - Ogerpon: base `105 / 160`, `cash` `106 / 160`
  - Cornerstone: base `124 / 160`, `cash` `118 / 160`
  - Raging Bolt: both `156 / 160`
- Decision: reject. The normal-Ogerpon gain is negligible and Cornerstone worsens.

Promoted local candidate:

- Directory: `submission_archaludon_live947_gtoger_ogernonexheal`
- Archive: `submission_archaludon_live947_gtoger_ogernonexheal.tar.gz`
- Rule:
  - Allow `Jumbo Ice Cream` on active non-ex `Archaludon (840)` only when:
    - matchup detection is Ogerpon,
    - opponent Active is `Cornerstone Mask Ogerpon ex (117)`,
    - our active non-ex `Archaludon` has `<= 80` HP.
  - This is intentionally narrower than earlier rejected non-ex healing probes.

Focused Ogerpon output:

- `analysis_outputs/repeat_ogernonexheal_oger_g40r2_seed492000_summary.csv`
- Results:
  - Ogerpon: base `109 / 160`, `heal` `116 / 160`
  - Cornerstone: base `122 / 160`, `heal` `127 / 160`
  - Raging Bolt: both `157 / 160`
  - Ogerpon-weighted discussion scenario: `0.8417` to `0.8618`
  - Equal across the three Ogerpon buckets: `0.8083` to `0.8333`

Side checks:

- Non-Ogerpon side output: `analysis_outputs/repeat_ogernonexheal_side_g24r2_seed493000_summary.csv`
  - Equal public buckets moved `0.7738` to `0.7857`.
  - Ketchum and mirror rows were noisy despite the rule not being able to trigger there, so direct checks were run.
- Direct Archaludon mirror:
  - `analysis_outputs/direct_base_arch_495000_summary.jsonl`
  - `analysis_outputs/direct_heal_arch_495000_summary.jsonl`
  - `analysis_outputs/direct_arch_base_496000_summary.jsonl`
  - `analysis_outputs/direct_arch_heal_496000_summary.jsonl`
  - base `41 / 80`, `heal` `40 / 80`; treated as no material side effect.
- Direct Ketchum Alt:
  - base `45 / 80`, `heal` `48 / 80`.
- Direct Ogerpon:
  - normal Ogerpon base `42 / 64`, `heal` `50 / 64`.
  - Cornerstone first direct check base `53 / 64`, `heal` `50 / 64`, but larger follow-up base `93 / 120`, `heal` `99 / 120`.

Decision:

- Promote `submission_archaludon_live947_gtoger_ogernonexheal` as the next local candidate over `submission_archaludon_live947_gtguard_ogerlow_no117`.
- The rule is narrow, fixes a real trace pattern, improves Ogerpon-focused checks, and direct mirror/Ketchum checks do not show a reproducible side effect.

Rejected threshold widening:

- Candidates:
  - `submission_archaludon_live947_gtoger_ogernonexheal120`
  - `submission_archaludon_live947_gtoger_ogernonexheal140`
- Idea: widen the non-ex `Jumbo Ice Cream` permission from active HP `<= 80` to `<= 120` or `<= 140`.
- First threshold screen: `analysis_outputs/repeat_ogernonexheal_thresholds_g32r2_seed505000_summary.csv`
  - `h140` looked best in this pass, with Ogerpon equal buckets `0.8307` vs `h80` `0.7865`.
- Direct h80/h140 checks:
  - normal Ogerpon: `h80` `57 / 80`, `h140` `53 / 80`
  - Cornerstone: `h80` `63 / 80`, `h140` `65 / 80`
- Repeat h80/h140 confirmation: `analysis_outputs/repeat_ogernonexheal_h80_h140_g40r2_seed510000_summary.csv`
  - Ogerpon: `h80` `109 / 160`, `h140` `113 / 160`
  - Cornerstone: `h80` `128 / 160`, `h140` `127 / 160`
  - Raging Bolt: `h80` `154 / 160`, `h140` `151 / 160`
  - Ogerpon-weighted discussion scenario: `h80` `0.8458`, `h140` `0.8410`
  - Equal across the three Ogerpon buckets: both `0.8146`
- Decision: keep the narrower HP `<= 80` threshold. The wider threshold can improve normal Ogerpon in some runs, but it does not beat h80 on the weighted Ogerpon scenario and slightly worsens Raging Bolt / Cornerstone in confirmation.

## 2026-07-05 Live 947 Post-h80 Follow-up Probes

The current local candidate remains:

- `submission_archaludon_live947_gtoger_ogernonexheal`
- `submission_archaludon_live947_gtoger_ogernonexheal.tar.gz`

Rejected follow-up probes:

- Mirror low-deck Lillie skip:
  - Candidate: `submission_archaludon_live947_gtoger_mirrorlillieskip6`
  - Rule: in Archaludon mirrors, skip Lillie at deck `<= 6` when an attack is already planned.
  - Check: `analysis_outputs/repeat_mirrorlillieskip6_arch_g50_seed512000_summary.csv`
  - Result: mirror `h80` `52 / 100`, `mirrorlillieskip6` `50 / 100`.
  - Decision: reject.
- Great Tusk non-ex Archaludon ready evolution:
  - Candidate: `submission_archaludon_live947_gtoger_gtnonexready`
  - Rule: versus visible Great Tusk, allow ready 3-energy Duraludon to evolve into non-ex `Archaludon (840)`.
  - Exact Koushik proxy improved on the first seed pair (`77 / 96` to `84 / 96`), but the normal Great Tusk confirmation worsened.
  - Confirmation: `analysis_outputs/repeat_gtnonexready_greattusk_g64_seed518000_summary.csv`
  - Result: normal Great Tusk `h80` `115 / 128`, `gtnonexready` `106 / 128`.
  - Side check: `analysis_outputs/repeat_gtnonexready_arch_corner_g64_seed517000_summary.csv`
  - Decision: reject. The Koushik gain did not hold against the same-deck normal Great Tusk bucket.
- Great Tusk low-deck Raging Hammer priority:
  - Candidate: `submission_archaludon_live947_gtoger_gtrhprio_lowdeck`
  - Rule: versus visible Great Tusk, raise `Raging Hammer` priority at low deck count or when it KOs the Active.
  - Check: `analysis_outputs/gtrhprio_greattusk_g64_seed519000_summary.csv`
  - Result: Great Tusk `h80` `112 / 128`, `rhprio` `110 / 128`.
  - Decision: reject.
- Mirror Cinderace-solo Pokegear/Poke Pad suppression:
  - Candidate: `submission_archaludon_live947_gtoger_mirrorcindersologearskip`
  - Rule: in Archaludon mirrors, if Active is Cinderace with empty bench and no Duraludon/Archaludon ex in play, suppress Pokegear/Poke Pad.
  - First check: `analysis_outputs/mirrorcinderskip_arch_g60_seed520000_summary.csv`
  - Result: mirror `53 / 120` to `56 / 120`.
  - Confirmation: `analysis_outputs/mirrorcinderskip_arch_g100_seed521000_summary.csv`
  - Result: mirror `98 / 200` to `93 / 200`.
  - Decision: reject. The initial small gain did not reproduce.
- Current-base Ketchum pivot Boss transplant:
  - Candidate: `submission_archaludon_live947_gtoger_ketchumpivotboss`
  - Rule: when Ketchum-style `Dunsparce/Dudunsparce` pivot is Active and benched Kadabra/Alakazam is KO-able, prioritize Boss.
  - Check: `analysis_outputs/ketchumpivot_h80_alak_g64_seed522000_summary.csv`
  - Result: Ketchum Alt `82 / 128` to `80 / 128`; normal Alakazam `109 / 128` to `107 / 128`.
  - No `Ketchum: Boss` trigger appeared in this trace set.
  - Decision: reject.

Conclusion:

- Keep `submission_archaludon_live947_gtoger_ogernonexheal` unchanged as the local submission candidate.
- The remaining mirror/Ketchum edge cases are real, but the obvious local rule patches either do not trigger reliably or trade away tempo.
- Next useful improvement should come from fresh live-submission loss logs or a broader deck-family pivot, not more ungrounded micro-rules on this branch.

## 2026-07-05 Post-h80 Bench Boss Probes

Starting point remained:

- `submission_archaludon_live947_gtoger_ogernonexheal`
- `submission_archaludon_live947_gtoger_ogernonexheal.tar.gz`

Global bench-KO Boss priority:

- Candidate: `submission_archaludon_live947_gtoger_h80_benchboss8500`
- Rule: when a benched opponent Pokemon is immediately KO-able, raise Boss target priority from the generic `4000 + prize/energy` range to `8500 + prize/energy`.
- Key-bucket screen: `analysis_outputs/h80_benchboss_key_g48_seed523000_summary.csv`
  - Selected equal buckets improved `0.6927` to `0.7257`.
  - Main gains were Alakazam, Ogerpon, Ketchum, and Archaludon in that seed.
  - Cornerstone worsened `76 / 96` to `68 / 96`.
- Full all-bucket check: `analysis_outputs/h80_benchboss_all_g24_seed525000_summary.csv`
  - Equal public buckets improved only slightly: `0.8221` to `0.8285`.
  - 2026-07-03 top20 proxy worsened: `0.8154` to `0.8102`.
  - Ketchum worsened `31 / 48` to `28 / 48`.
  - Chandelure worsened `48 / 48` to `42 / 48`.
  - Great Tusk worsened `42 / 48` to `37 / 48`.
- Focused risk confirmation: `analysis_outputs/h80_benchboss_risk_g64_seed528000_summary.csv`
  - Four risk buckets combined worsened `0.8301` to `0.8262`.
  - Great Tusk improved `108 / 128` to `112 / 128`.
  - Ketchum worsened `80 / 128` to `77 / 128`.
  - Chandelure worsened `121 / 128` to `119 / 128`.
  - Marnie worsened `116 / 128` to `115 / 128`.
- Decision: do not promote as default. It is a plausible field-read branch only if live history becomes clearly Ogerpon/Starmie/Archaludon-heavy and Ketchum/Chandelure/Marnie are less important.

Safer gated bench-KO Boss priority:

- Candidate: `submission_archaludon_live947_gtoger_h80_benchboss_safe`
- Rule: apply the high bench-KO Boss priority only to selected detected matchups and avoid obvious Ketchum-style Alakazam markers.
- Check: `analysis_outputs/h80_benchsafe_all_g24_seed526000_summary.csv`
  - Equal public buckets moved `0.8429` to `0.8413`.
  - Ketchum still worsened `36 / 48` to `31 / 48`.
  - Starmie improved `40 / 48` to `44 / 48`, but the broader result did not justify adoption.
- Decision: reject.

Targeted bench-KO Boss priority:

- Candidate: `submission_archaludon_live947_gtoger_h80_benchboss_targeted`
- Rule: apply high bench-KO Boss priority only to Archaludon, Starmie, and Ogerpon-related matchups.
- Check: `analysis_outputs/h80_targetboss_key_g48_seed527000_summary.csv`
  - Selected equal buckets improved `0.7170` to `0.7396`.
  - However, intended target buckets were unstable: Archaludon `45 / 96` to `42 / 96`, Starmie `83 / 96` to `79 / 96`, Cornerstone `81 / 96` to `74 / 96`.
  - Non-target gains such as Great Tusk and Ketchum are treated as run variance because the new rule should not be the direct cause.
- Decision: reject for now. The target buckets did not improve in the direction the rule intended.

Current decision remains:

- Keep `submission_archaludon_live947_gtoger_ogernonexheal` as the local submission candidate.
- Do not spend another submission on bench-KO Boss priority unless fresh live logs show a field where the global branch's risk is acceptable.

## 2026-07-05 Post-h80 Board-Preservation Probes

Starting point remained:

- `submission_archaludon_live947_gtoger_ogernonexheal`

Trace context:

- Fresh scored traces: `analysis_outputs/h80_arch_ketchum_trace_g40_seed529000_summary.csv`
- Result:
  - Archaludon mirror: `36 / 80` (`0.4500`)
  - Ketchum Alt: `51 / 80` (`0.6375`)
- Loss pattern summary: `analysis_outputs/h80_arch_ketchum_trace_g40_seed529000_loss_patterns.csv`
  - `73 / 73` sampled losses ended with no active Pokemon on our side.
  - `65 / 73` losses included an `Archaludon ex` leaving our board.
  - Ketchum losses usually ended with opponent `Alakazam (743)` active and repeated `Powerful Hand`.

Rejected setup bench probes on the current h80 branch:

- Candidate: `submission_archaludon_live947_gtoger_h80_setupdura1`
  - Rule: during setup, bench exactly the first available `Duraludon`.
  - Check: `analysis_outputs/h80_setupdura1_arch_ketchum_g64_seed530000_summary.csv`
  - Result:
    - Archaludon: `58 / 128` to `61 / 128`
    - Ketchum Alt: `90 / 128` to `80 / 128`
    - Equal selected: `0.5781` to `0.5508`
  - Decision: reject. The mirror gain is not worth the Ketchum drop.
- Candidate: `submission_archaludon_live947_gtoger_h80_setupcinder_hasex`
  - Rule: during setup, if Active is `Cinderace`, bench is empty, and `Archaludon ex` is already in hand, bench one `Duraludon`.
  - Check: `analysis_outputs/h80_setuphasex_arch_ketchum_g64_seed531000_summary.csv`
  - Result:
    - Archaludon: `66 / 128` to `60 / 128`
    - Ketchum Alt: `85 / 128` to `81 / 128`
    - Equal selected: `0.5898` to `0.5508`
  - Decision: reject.

Rejected Alakazam active-evolution probes:

- Candidate: `submission_archaludon_live947_gtoger_h80_alakactive_readyevolve`
  - Rule: versus detected Alakazam, suppress active `Duraludon -> Archaludon ex` evolution unless the turn can plausibly reach three energy after `Assemble Alloy` and a possible manual attach.
  - Key check: `analysis_outputs/h80_alakready_key_g64_seed532000_summary.csv`
    - Ketchum Alt improved `78 / 128` to `83 / 128`.
    - Archaludon improved `56 / 128` to `59 / 128`.
    - Normal Alakazam fell `107 / 128` to `106 / 128`.
    - Equal selected improved `0.6276` to `0.6458`.
  - Full all-bucket check: `analysis_outputs/h80_alakready_all_g24_seed533000_summary.csv`
    - Equal public buckets worsened `0.8478` to `0.8205`.
    - Ogerpon family and several non-target rows moved down enough that the key-bucket gain was not trusted.
  - Decision: reject as default.
- Candidate: `submission_archaludon_live947_gtoger_h80_alakactive_backuphold`
  - Rule: same idea, but only hold active evolution when a backup `Duraludon` / `Archaludon ex` already exists on the bench.
  - Check: `analysis_outputs/h80_backuphold_key_g64_seed534000_summary.csv`
  - Result:
    - Normal Alakazam improved `108 / 128` to `113 / 128`.
    - Ketchum Alt worsened `93 / 128` to `80 / 128`.
    - Equal selected worsened `0.6641` to `0.6432`.
  - Decision: reject.

Current decision:

- Keep `submission_archaludon_live947_gtoger_ogernonexheal` unchanged.
- The board-preservation symptoms are real, but setup-benching and active-evolution suppression trade away too much Ketchum or broader public-proxy equity.

## 2026-07-05 Post-h80 Live-Mirror / Relicanth Follow-up

Starting point remained:

- `submission_archaludon_live947_gtoger_ogernonexheal`
- `submission_archaludon_live947_gtoger_ogernonexheal.tar.gz`

Live context from the fetched `submission_54315481` replays:

- Parsed final states to `analysis_outputs/kaggle_live/submission_54315481/rurumi_final_states.csv`.
- In that fetched set, `rurumi` losses were concentrated in Archaludon mirrors: `8 / 12` losses were against `archaludon_metal`.
- Visible opposing Archaludon lists commonly included `Relicanth (57)` and sometimes `Judge (1213)` / `Carmine (1192)`, while the current h80 candidate keeps the Ogerpon non-ex package and has no Relicanth.

Rejected Cinderace backup rule:

- Candidate: `submission_archaludon_live947_gtoger_h80_cinderbackup`
- Rule: against visible Archaludon or Alakazam, if the bench is empty, the Active `Duraludon` / `Archaludon ex` is in KO range, and no better Duraludon line is in hand, allow playing `Cinderace` as an emergency backup body.
- Check: `analysis_outputs/h80_cinderbackup_arch_ketchum_g64_seed535000_summary.csv`
- Result:
  - Archaludon: `h80` `60 / 128`, `cbackup` `56 / 128`
  - Ketchum Alt: `h80` `78 / 128`, `cbackup` `72 / 128`
- Trigger audit: `analysis_outputs/h80_cinderbackup_arch_ketchum_score_reasons.csv` did not show selected `play Cinderace backup` reasons.
- Decision: reject. The condition did not produce a useful board-preservation pattern and the focused comparison moved down.

Rejected mirror Raging-Hammer-trap Boss rule:

- Candidate: `submission_archaludon_live947_gtoger_h80_mirror_rhtrapboss`
- Rule: in Archaludon mirrors, when a KO-able benched opposing `Relicanth` exists and damaging opposing `Archaludon ex` without KO would let it answer with a lethal Relicanth-enabled `Raging Hammer`, raise Boss priority to remove Relicanth.
- Check: `analysis_outputs/h80_rhtrap_arch_ketchum_g64_seed536000_summary.csv`
- Trigger audit: `analysis_outputs/h80_rhtrap_arch_ketchum_score_reasons.csv`
  - The new reason fired `31` times in `archaludon_vs_rhtrap` and `22` times in `rhtrap_vs_archaludon`.
- Result:
  - Archaludon: `h80` `61 / 128`, `rhtrap` `53 / 128`
  - Ketchum Alt: `h80` `86 / 128`, `rhtrap` `75 / 128`
- Decision: reject. The trigger fired, but spending the Boss turn on Relicanth still lost too much tempo.

Rejected public-Arch deck reset with current h80 rules:

- Candidate: `submission_archaludon_live947_gtoger_h80_publicarchdeck`
- Change: keep current h80 rules but replace the deck with the public Archaludon-style shell:
  - `Relicanth (57)` x1
  - `Jumbo Ice Cream (1147)` x4
  - `Full Metal Lab (1244)` x4
  - `Metal Energy (8)` x11
  - no non-ex `Archaludon (840)`
- Check: `analysis_outputs/h80_publicarchdeck_key_g40_seed537000_summary.csv`
- Result:
  - Archaludon: `h80` `34 / 80`, `pubdeck` `38 / 80`
  - Ketchum Alt: `49 / 80` to `52 / 80`
  - Ogerpon: `53 / 80` to `28 / 80`
  - Cornerstone: `65 / 80` to `41 / 80`
  - Great Tusk: `64 / 80` to `61 / 80`
  - Starmie: `75 / 80` to `71 / 80`
  - Equal selected buckets: `0.7083` to `0.6062`
- Decision: reject as a broad candidate. The public Arch shell confirms that Relicanth/public-mirror construction helps mirror a little, but removing the non-ex Ogerpon package is too costly.

Rejected Relicanth 1 / Cinderace 3 hybrid:

- Candidate: `submission_archaludon_live947_gtoger_h80_relic1_cutcinder`
- Change: keep the current h80 deck and rules, but replace one `Cinderace (666)` with one `Relicanth (57)`.
- Key check: `analysis_outputs/h80_relic1_cutcinder_key_g40_seed538000_summary.csv`
  - Archaludon: `39 / 80` to `40 / 80`
  - Ketchum Alt: `49 / 80` to `51 / 80`
  - Ogerpon: `54 / 80` to `57 / 80`
  - Great Tusk: `69 / 80` to `64 / 80`
  - Starmie: `77 / 80` to `68 / 80`
  - Cornerstone: `60 / 80` to `55 / 80`
- Full all-bucket check: `analysis_outputs/h80_relic1_cutcinder_all_g24_seed539000_summary.csv`
  - Equal public buckets: `h80` `0.8333`, `reliccutcinder` `0.7965`
  - Public 2026-07-03 top20 proxy: `0.8218` to `0.7731`
  - Live-submission weighted proxy from fetched `submission_54315481` opponent mix: `h80` `0.7299`, `reliccutcinder` `0.7250`
- Decision: reject. Relicanth x1 helps some mirror/Alakazam rows in short screens, but the Cinderace cut costs too much Starmie/Chandelure/Marnie/Lucario stability and does not beat h80 even under the fetched live-weight proxy.

Current decision:

- Keep `submission_archaludon_live947_gtoger_ogernonexheal` as the local candidate.
- The newest tests support the earlier conclusion: mirror losses are real, but naive Relicanth/Boss/backup patches trade away too much broad equity.

## 2026-07-05 h80 Follow-up: Deck Identity and Great Tusk Guard

Deck identity check:

- The current h80 branch is not an exact copy of the public/gold-like Archaludon shell.
- Current h80 deck:
  - `Duraludon (169)` x4
  - `Archaludon ex (190)` x4
  - `Cinderace (666)` x4
  - non-ex `Archaludon (840)` x2
  - no `Relicanth (57)`
  - `Metal Energy (8)` x12
- Imported public Archaludon-style deck used for comparison:
  - `Duraludon (169)` x4
  - `Archaludon ex (190)` x4
  - `Cinderace (666)` x4
  - `Relicanth (57)` x1
  - no non-ex `Archaludon (840)`
  - `Metal Energy (8)` x11
  - more `Jumbo Ice Cream (1147)` / `Full Metal Lab (1244)` count
- Conclusion: current h80 is the same broad Archaludon-metal archetype as some top/public lists, but the list is intentionally different. The non-ex `Archaludon` package is kept for Ogerpon/Cornerstone coverage, and the public Relicanth shell was rejected as a broad default in `analysis_outputs/h80_publicarchdeck_key_g40_seed537000_summary.csv`.

Submitted same-deck rule-difference check:

- Compared `submission_archaludon_gt_deckguard.tar.gz` and `submission_archaludon_lucariodonkwall_strict.tar.gz`.
- Their `deck.csv` files are identical.
- Kaggle live scores diverged sharply (`gt_deckguard` around `948.0`; `lucariodonkwall_strict` around `834.6` in the latest CLI check), so rules / play policy alone can be a large factor.
- Local h80 vs submitted `gt_deckguard` check: `analysis_outputs/h80_vs_submitted_gtdeck_key_g48_seed540000_summary.csv`
  - h80 equal selected buckets: `0.7274`
  - gtdeck equal selected buckets: `0.6580`
  - h80 Great Tusk: `84 / 96`
  - gtdeck Great Tusk: `45 / 96`
- Decision: do not revert to the submitted `gtdeck` rules even though it had a strong live score; the current h80 branch has much better local Great Tusk / Cornerstone coverage.

Rejected non-ex heal threshold widening:

- Candidate: `submission_archaludon_live947_gtoger_ogernonexheal120`
- Rule change: allow `Jumbo Ice Cream` on active non-ex `Archaludon (840)` versus Cornerstone/Ogerpon at `hp <= 120` instead of `hp <= 80`.
- Check: `analysis_outputs/h80_h120_key_g64_seed541000_summary.csv`
- Result:
  - h80 equal selected buckets: `0.7623`
  - h120 equal selected buckets: `0.7467`
  - h120 helped Great Tusk / Starmie / Ketchum / Raging Bolt slightly, but hurt Archaludon, Ogerpon, and Cornerstone.
- Decision: reject; keep the tighter `hp <= 80` heal gate.

Rejected Ogerpon low-deck threshold changes:

- Candidates:
  - `submission_archaludon_live947_gtoger_h80_ogerlow_t12_l6`
  - `submission_archaludon_live947_gtoger_h80_ogerlow_t16_l8`
- First medium check: `analysis_outputs/h80_ogerlow_thresholds_key_g40_seed542000_summary.csv`
  - t12/l6 and t16/l8 looked slightly ahead on the mixed key set, but the rule should only matter in Ogerpon-like games, so broad gains were treated as noise.
- Focused Oger-family check: `analysis_outputs/h80_ogerlow_thresholds_oger_g32_seed544100_summary.csv`
  - h80 Oger family equal: `0.8542`
  - t12/l6 Oger family equal: `0.8229`
  - t16/l8 Oger family equal: `0.8125`
- Decision: reject both; keep current Ogerpon low-deck thresholds.

Promoted Great Tusk guard hardening:

- Candidate: `submission_archaludon_live947_gtoger_h80_gtguard_hard`
- Deck is identical to h80.
- Rule-only change:
  - Great Tusk-visible `Lillie` low-deck threshold: `40` to `45`
  - Great Tusk-visible `Explorer` preservation threshold: `42` to `46`
  - Great Tusk-visible `Ultra Ball` preservation threshold: `36` to `40`
- Check: `analysis_outputs/h80_gtguard_hard_key_g48_seed545000_summary.csv`
- Result:
  - h80 equal selected buckets: `0.6962`
  - gthard equal selected buckets: `0.7326`
  - Great Tusk: `79 / 96` to `87 / 96`
  - Archaludon: `39 / 96` to `49 / 96`
  - Ketchum Alt: `51 / 96` to `58 / 96`
  - Ogerpon: `74 / 96` to `72 / 96`
  - Starmie: `80 / 96` to `79 / 96`
  - Cornerstone: `78 / 96` to `77 / 96`
- Built archive: `submission_archaludon_live947_gtoger_h80_gtguard_hard.tar.gz`
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Decision: promote `submission_archaludon_live947_gtoger_h80_gtguard_hard.tar.gz` as the current local candidate, with `submission_archaludon_live947_gtoger_ogernonexheal.tar.gz` as the previous fallback.

## 2026-07-05 Live Score Override

Kaggle submission check after `h80_gtguard_hard` reached complete status:

- `submission_archaludon_live947_gtoger_h80_gtguard_hard.tar.gz`: public score `700.3`
- `submission_archaludon_lucariodonkwall_strict.tar.gz`: public score `838.8`
- `submission_archaludon_gt_deckguard.tar.gz`: public score `921.7`
- `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`: public score `947.0`

Decision update:

- Demote `submission_archaludon_live947_gtoger_h80_gtguard_hard.tar.gz`. The local Great Tusk/selected-bucket gain did not transfer to the real queue.
- Do not make another speculative local-only rule patch before recovering the active submission quality.
- Next recovery submission candidate:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`
- Backup if the long archive is not desired:
  - `submission_archaludon_gt_deckguard.tar.gz`

## 2026-07-07 Latest Submission Feedback

Latest Kaggle CLI check:

- Latest submitted archive: `submission_archaludon_gt_deckguard.tar.gz`
- Public score at check time: `929.3`
- Previous high reference still visible in history:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`: `947.0`

Recovered live games for latest submission `54349636`:

- Win: episode `84575528` vs `HayatoFujihara`, opponent archetype `hop_trevenant`.
- Loss: episode `84569848` vs `tubotu`, opponent archetype `alakazam_psychic`.
- Loss: episode `84566774` vs `Wasabi`, opponent archetype looked like Iono/Bellibolt electric.

Common live loss pattern:

- Both visible losses ended with active `Archaludon ex (190)` giving the opponent the final 2 prizes.
- The Alakazam loss had our `Archaludon ex` active and a `Duraludon` on bench while opponent had 2 prizes remaining.
- The Iono/Bellibolt loss also ended through active `Archaludon ex`, but no bench rescue was visible at the end.

Rejected broad non-ex endgame evolution:

- Candidate: `submission_archaludon_gtdeckguard_endgame_nonex`
- Idea: when opponent has 2 prizes remaining versus Alakazam/Iono, bias toward non-ex `Archaludon (840)`.
- Check: `analysis_outputs/gtdeck_endnonex_key_g48_seed707000_summary.csv`
- Result:
  - Normal Alakazam improved: `76 / 96` to `83 / 96`
  - Starmie improved: `85 / 96` to `93 / 96`
  - Archaludon mirror fell: `48 / 96` to `40 / 96`
  - Ogerpon fell: `68 / 96` to `63 / 96`
  - Equal selected buckets fell: `0.7517` to `0.7396`
- Decision: reject; the search/evolution bias is too broad.

Rejected ready-only non-ex endgame evolution:

- Candidate: `submission_archaludon_gtdeckguard_endgame_nonex_readyonly`
- Idea: only evolve into non-ex `Archaludon` in endgame if the target `Duraludon` already has 3 energy.
- Check: `analysis_outputs/gtdeck_readyonly_key_g48_seed708000_summary.csv`
- Result:
  - Ketchum Alt improved: `54 / 96` to `62 / 96`
  - Starmie improved: `78 / 96` to `82 / 96`
  - Normal Alakazam fell: `79 / 96` to `74 / 96`
  - Archaludon mirror fell: `51 / 96` to `38 / 96`
  - Equal selected buckets fell: `0.7396` to `0.7222`
- Decision: reject; still too much mirror damage.

Promoted filtered endgame retreat:

- Candidate directory: `submission_archaludon_gtdeckguard_endgame_retreat_alakfilter`
- Archive: `submission_archaludon_gtdeckguard_endgame_retreat_alakfilter.tar.gz`
- Rule-only change:
  - If opponent has 2 prizes remaining and active is `Archaludon ex`, consider retreating to a 1-prize target.
  - Do not retreat if current active attack already wins.
  - Apply this under Alakazam/Iono pressure.
  - For Alakazam, suppress the retreat rule when the opponent looks like the `65` Dunsparce/Ketchum-style line unless live-style markers such as `Battle Cage (1264)`, `Psyduck (858)`, or `Fan Rotom (174)` are visible.
- Direct core check: `analysis_outputs/gtdeck_retreat_filter_core_g48_seed714000_summary.csv`
- Result:
  - Normal Alakazam: `76 / 96` to `77 / 96`
  - Ketchum Alt: `65 / 96` to `63 / 96`
  - Archaludon mirror: `43 / 96` to `45 / 96`
  - Great Tusk: `48 / 96` to `57 / 96`
  - Ogerpon: `71 / 96` to `80 / 96`
  - Equal selected buckets: `0.6312` to `0.6708`
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Decision: promote `submission_archaludon_gtdeckguard_endgame_retreat_alakfilter.tar.gz` as the next local candidate. Main risk is that the Iono/Bellibolt branch is only inferred from live history and is not covered by a dedicated local mimic yet.

## 2026-07-07 Iono Endgame Recheck

Added local Iono/Bellibolt mimic:

- Directory: `meta_agents/iono_bellibolt_live_wasabi_simple`
- Deck source: recovered Wasabi live deck from episode `84566774`
- Tool registration: `tools/run_meta_suite.py` now includes `iono_bellibolt`
- Purpose: stress the live loss pattern, not a full top-player imitation.

Important live replay audit:

- Live loss episode: `84566774`
- Critical step: `steps[171][1]`
- State:
  - Opponent had 2 prizes remaining.
  - Our active was `Duraludon (169)`.
  - Our bench was empty.
  - Our hand included `Archaludon (840)` and `Archaludon ex (190)`.
- Baseline action chose option `[3]`, which was `Archaludon ex (190)`.
- New Iono endgame guard chooses option `[0]`, which is non-ex `Archaludon (840)`.

Rejected broader Alakazam/Iono filtered retreat as promoted default:

- Archive from prior pass: `submission_archaludon_gtdeckguard_endgame_retreat_alakfilter.tar.gz`
- Multi-run aggregation showed overall selected-bucket gain, but the buckets the rule actually touches were weaker:
  - Alakazam aggregate: `gtdeck 314/384`, `filter 310/384`
  - Ketchum Alt aggregate: `gtdeck 249/384`, `filter 238/384`
- Decision: do not keep Alakazam endgame retreat in the default candidate.

Promoted Iono-only endgame guard:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_endgame_guard`
- Archive: `submission_archaludon_gtdeckguard_iono_endgame_guard.tar.gz`
- Rule-only change:
  - Detect Iono line IDs `{265, 268, 269, 270, 271}`.
  - If opponent has 2 prizes left and we have no 1-prize bench backup, prefer non-ex `Archaludon (840)` over `Archaludon ex (190)`.
  - If active is `Archaludon ex` in the same Iono endgame pressure, retreat/promote to a 1-prize target when available.
  - If opponent has 3 or fewer prizes and active is `Archaludon ex` with no bench `Duraludon`, prioritize taking/benching/recovering `Duraludon`.
- Local check after live-step patch: `analysis_outputs/gtdeck_ionoonly_nonex_key_g48_seed726000_summary.csv`
- Result:
  - Alakazam: `71 / 96` to `80 / 96`
  - Ketchum Alt: `46 / 96` to `68 / 96`
  - Archaludon mirror: `42 / 96` to `45 / 96`
  - Great Tusk: `51 / 96` to `52 / 96`
  - Ogerpon: `72 / 96` to `69 / 96`
  - Starmie: `88 / 96` to `84 / 96`
  - Iono mimic: `95 / 96` to `95 / 96`
  - Equal selected buckets: `0.6920` to `0.7336`
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
- Decision: replace the previous `alakfilter` archive with `submission_archaludon_gtdeckguard_iono_endgame_guard.tar.gz` as the next local candidate, because it directly changes the verified live losing decision while avoiding the Alakazam/Ketchum endgame-retreat regression.

Minimal Iono non-ex-only follow-up:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_nonex_only`
- Archive: `submission_archaludon_gtdeckguard_iono_nonex_only.tar.gz`
- Reason for simplifying:
  - The verified live fix was specifically the evolution choice at `steps[171][1]`: choose non-ex `Archaludon (840)` instead of `Archaludon ex (190)`.
  - The broader `iono_endgame_guard` also included retreat and backup-Duraludon heuristics that are plausible but less directly proven by the live replay.
- Minimal rule-only change:
  - Detect Iono line IDs `{265, 268, 269, 270, 271}`.
  - If opponent has 2 prizes remaining and our bench has no 1-prize backup, score non-ex `Archaludon (840)` evolution above `Archaludon ex (190)`.
- Live-step verification:
  - Baseline action at the critical replay state: `[3]` (`Archaludon ex`)
  - Minimal candidate action at the same state: `[0]` (`Archaludon`)
- Local check: `analysis_outputs/gtdeck_iono_minimal_compare_g48_seed727000_summary.csv`
- Result:
  - Alakazam: `76 / 96` to `82 / 96`
  - Ketchum Alt: `61 / 96` to `64 / 96`
  - Archaludon mirror: `38 / 96` to `52 / 96`
  - Great Tusk: `44 / 96` to `62 / 96`
  - Ogerpon: `70 / 96` to `63 / 96`
  - Starmie: `83 / 96` to `87 / 96`
  - Iono mimic: `95 / 96` to `96 / 96`
  - Equal selected buckets: `0.6949` to `0.7530`
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/` only.
- Decision: promote `submission_archaludon_gtdeckguard_iono_nonex_only.tar.gz` above `submission_archaludon_gtdeckguard_iono_endgame_guard.tar.gz` as the current next local candidate. It is easier to justify because it is the smallest change that fixes the confirmed live losing choice.

## 2026-07-07 Latest Submission Feedback Follow-up

Kaggle CLI check:

- Latest completed submission: `submission_archaludon_gt_deckguard.tar.gz`
- Submitted at: `2026-07-05 03:55:17.647000`
- Public score at check time: `930.5`
- This is below the earlier `947.0` recovery submission, so fresh live losses are useful debugging data rather than proof that the whole branch is better.

Live replay audit from submission `54349636`:

- Win: episode `84575528` vs Hop/Trevenant.
- Loss: episode `84566774` vs Wasabi Iono/Bellibolt.
- Loss: episode `84569848` vs tubotu Alakazam.
- Both losses contained the same prize-map failure shape: opponent had 2 prizes remaining and our active `Archaludon ex (190)` became the final 2-prize liability.

Alakazam live-step finding:

- Live loss episode: `84569848`
- Critical step: `steps[92][0]`
- State:
  - Opponent had 2 prizes remaining.
  - Our active was `Duraludon (169)`.
  - Our bench was empty.
  - Our hand included non-ex `Archaludon (840)` and `Archaludon ex (190)`.
  - Opponent public-visible cards included live tubotu markers such as `1264`.
- Baseline action chose option `[7]`, which was `Archaludon ex (190)`.
- Iono-only candidate still chose `[7]`.
- New live-Alakazam filtered candidate chooses option `[0]`, which is non-ex `Archaludon (840)`.

Rejected broad Alakazam non-ex guard:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alak_nonex_only`
- The broad rule applied the Iono final-prize non-ex guard to all Alakazam buckets.
- Targeted local check: `analysis_outputs/gtdeck_iono_alak_targeted_g24_seed732000_summary.csv`
- Result showed the idea was too broad:
  - Public Alakazam: `gtdeck 44/48`, broad `43/48`
  - Ketchum Alt: `gtdeck 34/48`, broad `30/48`
  - Iono mimic: `gtdeck 47/48`, broad `48/48`
- Decision: do not promote the broad Alakazam guard.

Promoted live-Alakazam filtered non-ex guard:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_nonex`
- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_nonex.tar.gz`
- Rule-only change relative to `submission_archaludon_gtdeckguard_iono_nonex_only`:
  - Keep the Iono final-prize non-ex evolution guard.
  - Add the same non-ex evolution guard for Alakazam only when live tubotu-like markers `{1264, 858, 174}` are publicly visible.
  - Do not fire if Ketchum-style markers `{1246, 1247}` are visible.
- Exact live-step verification:
  - Alakazam `steps[92][0]`: action changed from ex evolve to non-ex evolve.
  - Iono `steps[171][1]`: action remains non-ex evolve.
- Action-equivalence check:
  - `submission_archaludon_gtdeckguard_iono_nonex_only` and `submission_archaludon_gtdeckguard_iono_alaklive_nonex` had zero action differences across sampled local trajectories against public Alakazam, Ketchum Alt, and Iono/Bellibolt mimics.
  - Therefore local win-rate swings between these two should be treated as harness/noise unless a live-marker Alakazam state appears.
- Targeted local check: `analysis_outputs/gtdeck_iono_alaklive_targeted_g24_seed733000_summary.csv`
- Smoke checks:
  - `analysis_outputs/smoke_alaklive_vs_alakazam_seed735000.jsonl`
  - `analysis_outputs/smoke_alaklive_vs_iono_seed735100.jsonl`
  - `analysis_outputs/smoke_ketchum_vs_alaklive_seed735200.jsonl`
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/` only.
- Decision: promote `submission_archaludon_gtdeckguard_iono_alaklive_nonex.tar.gz` as the current next submission candidate over Iono-only. It keeps the proven Iono fix and adds a narrow live-tubotu Alakazam fix without changing sampled non-live local behavior.

## 2026-07-07 Tubotu Live-Marker Follow-up

Additional live replay scan:

- Tried scanning `84575529` to `84600000`; this was too slow and was stopped.
- Short scan `84575529` to `84576528`: `checked=1000`, `existing=0`, `hits=0`.
- Probe scans around `84585000`, `84590000`, and `84595000`: no existing episodes.
- Decision: no additional live replays were available through practical ID scanning during this pass.

Added tubotu live Alakazam mimic:

- Directory: `meta_agents/alakazam_tubotu_live_84569848_simple`
- Source deck: tubotu player deck recovered from live loss episode `84569848`.
- Base policy: copied from the Ketchum-style Alakazam local agent, then added live card IDs:
  - `Battle Cage (1264)` as a stadium.
  - `Fan Rotom (174)` and `Psyduck (858)` as low-priority basics.
- Registered in `tools/run_meta_suite.py` as `alakazam_tubotu_live`.
- Purpose: test rules that are intentionally gated to live tubotu-like markers `{1264, 858, 174}`.

Rejected broad Alakazam line-4 probe:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_alakline4`
- Rule: versus all Alakazam, raise desired `Duraludon` / `Archaludon ex` line count from 3 to 4.
- Check: `analysis_outputs/alakline4_target_g32_seed736000_summary.csv`
- Result:
  - Normal Alakazam: `54 / 64` to `57 / 64`
  - Ketchum Alt: `51 / 64` to `39 / 64`
  - Iono mimic: `61 / 64` to `63 / 64`
- Decision: reject. The Ketchum loss is too large.

Promoted live-marker-only line-4 probe:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers`
- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers.tar.gz`
- Rule-only change relative to `submission_archaludon_gtdeckguard_iono_alaklive_nonex`:
  - If Alakazam is visible and tubotu-like markers `{1264, 858, 174}` are publicly visible, raise desired `Duraludon` / `Archaludon ex` line count from 3 to 4.
  - If Ketchum markers `{1246, 1247}` are visible, do not apply this rule.
  - Existing final-prize non-ex guard remains unchanged.
- Live-step verification:
  - Alakazam `steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `steps[171][1]`: still chooses non-ex `Archaludon (840)`.
  - Existing live tubotu replay `84569848`: no action differences from the current candidate, so this does not claim to fix that exact recorded game beyond the already-promoted non-ex final-prize change.
- Targeted local check: `analysis_outputs/line4markers_target_g32_seed738000_summary.csv`
- Result:
  - Tubotu live mimic: `51 / 64` to `55 / 64`
  - Normal Alakazam: `54 / 64` to `48 / 64`
  - Ketchum Alt: `44 / 64` to `44 / 64`
  - Iono mimic: `64 / 64` to `63 / 64`
- Action-equivalence audit:
  - Normal Alakazam, Ketchum Alt, Archaludon, Great Tusk, Ogerpon, Starmie, Hop, and Iono/Bellibolt: zero action differences in sampled trajectories.
  - Tubotu live mimic: action differences appeared only after live-marker cards became visible.
  - Therefore the normal-Alakazam and Iono score changes in the targeted check are treated as harness/noise rather than direct policy effects.
- Smoke checks:
  - `analysis_outputs/smoke_line4markers_vs_tubotu_seed741000.jsonl`
  - `analysis_outputs/smoke_line4markers_vs_ketchum_seed741100.jsonl`
  - `analysis_outputs/smoke_line4markers_vs_iono_seed741200.jsonl`
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/` only.
- Decision: promote `submission_archaludon_gtdeckguard_iono_alaklive_line4markers.tar.gz` as the current next submission candidate. It keeps the exact live-loss fixes and adds a tubotu-marker-only setup preference with no sampled action changes in the broader local meta.

## 2026-07-07 Score 935.2 Feedback Follow-up

Latest submitted archive checked by Kaggle CLI:

- Archive: `submission_archaludon_gt_deckguard.tar.gz`
- Public score at check time: `935.2`
- Known saved public episodes for submission `54349636`:
  - `84566774`: loss vs Wasabi / Iono-Bellibolt style. Exact-step replay check shows the line4markers candidate chooses non-ex `Archaludon (840)` at the endgame evolution choice.
  - `84569848`: loss vs tubotu / live Alakazam style. Exact-step replay check shows the line4markers candidate chooses non-ex `Archaludon (840)` at the critical final-prize evolution choice.
  - `84575528`: win vs HayatoFujihara.

Rejected 947-base/no-Great-Tusk-deckguard probe:

- Candidate directory: `submission_archaludon_947base_iono_alaklive_line4markers`
- Rule change relative to line4markers: removed only the visible-Great-Tusk Crustle deck-preservation block.
- Initial single-batch check was noisy and mixed by setup randomness:
  - `analysis_outputs/no_gtdeckguard_compare_g24_seed743000_summary.csv`
- Repeated focused check:
  - `analysis_outputs/repeat_no_gtdeckguard_focus_g8r3_seed744000_diff.csv`
  - Great Tusk dropped from `28 / 48` to `17 / 48` (`diff=-0.2291`, approx z `-2.249`).
  - Ogerpon was flat, tubotu-live Alakazam and Starmie were only tiny gains.
- Decision: reject the no-Great-Tusk-deckguard variant for now. The older public `947.0` score is useful evidence that the previous branch can spike, but the repeated local check says removing this guard is not a clean improvement from the current line4markers base.

Current next submission candidate remains:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers.tar.gz`
- Smoke checks rerun:
  - `analysis_outputs/smoke_verify_line4markers_tubotu_745000.jsonl`
  - `analysis_outputs/smoke_verify_line4markers_iono_745100.jsonl`
  - `analysis_outputs/smoke_verify_line4markers_ketchum_745200.jsonl`
- All three completed with `action_errors: 0`.

## 2026-07-07 Ogerpon Rule Recheck On Line4Markers

Weak-bucket trace pass:

- Trace output:
  - `analysis_outputs/line4markers_weak_trace_g12_seed746000_summary.csv`
  - `analysis_outputs/line4markers_weak_trace_g12_seed746000_games.csv`
  - `analysis_outputs/line4markers_weak_trace_g12_seed746000_traces/`
- Observation:
  - Great Tusk losses still often end as slow low-damage races into deckout.
  - The obvious non-ex `Archaludon (840)` Great Tusk route was not retried because `submission_archaludon_live947_gtoger_gtnonexready` had already failed confirmation: normal Great Tusk `115 / 128` to `106 / 128`.
  - Archaludon mirror losses again show the known prize-race / Relicanth pressure pattern, but prior Relicanth Boss, non-ex mirror, and bench-draw patches were already rejected.

Rejected Ogerpon h80 rule-set port:

- Candidate: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_ogerh80`
- Changes:
  - When Cornerstone `117` is visible and non-ex `Archaludon` is already in play, skip extra search/draw near low deck.
  - Allow `Jumbo Ice Cream` on active non-ex `Archaludon (840)` only versus active Cornerstone at `hp <= 80`.
- First screen:
  - `analysis_outputs/ogerh80_line4_compare_g24_seed747000_summary.csv`
  - Ogerpon and Cornerstone were slightly up in the first screen, but weighted Ogerpon was essentially flat.
- Repeated Ogerpon-family confirmation:
  - `analysis_outputs/repeat_ogerh80_line4_oger_g24r3_seed748000_diff.csv`
  - Normal Ogerpon dropped `110 / 144` to `95 / 144`.
  - Cornerstone dropped `109 / 144` to `104 / 144`.
  - Raging Bolt dropped `143 / 144` to `141 / 144`.
- Decision: reject. The older h80 rule does not transfer cleanly onto the current line4markers base.

Rejected Ogerpon ice-only split:

- Candidate: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_ogerice80`
- Change:
  - Only allow `Jumbo Ice Cream` on active non-ex `Archaludon (840)` versus active Cornerstone at `hp <= 80`; no low-deck draw/search suppression.
- Repeated Ogerpon-family confirmation:
  - `analysis_outputs/repeat_ogerice80_line4_oger_g24r3_seed749000_diff.csv`
  - Normal Ogerpon: `101 / 144` to `98 / 144`.
  - Cornerstone: `115 / 144` to `118 / 144`.
  - Raging Bolt: `139 / 144` to `137 / 144`.
  - Discussion Ogerpon-weighted scenario: `0.8511` to `0.8472`.
- Decision: reject. The Cornerstone-only gain is too small and does not beat the weighted Ogerpon-family result.

Current next submission candidate remains unchanged:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers.tar.gz`

## 2026-07-07 Great Tusk Strict58 Recheck On Line4Markers

Promoted Great Tusk strict58 candidate:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58`
- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58.tar.gz`
- Rule-only changes relative to `line4markers`:
  - Treat visible Great Tusk IDs `{58, 607}` as the Crustle/Great Tusk matchup for earlier recognition.
  - Tighten visible-Great-Tusk deck preservation thresholds:
    - `Lillie` refill/skip starts at deck `<= 25` instead of `<= 20`.
    - `Poke Pad` / `Pokegear` skip starts at deck `<= 30` instead of `<= 24`.
    - `Explorer` skip starts at deck `<= 24`, or `<= 30` when the line/stable attacker is established.
    - `Ultra Ball` skip starts at deck `<= 24` with enough line pieces instead of `<= 16`.
- Exact live-step verification:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Local ID audit:
  - Great Tusk / Crustle IDs `{58, 607, 344, 345, 532}` appear only in the Great Tusk local agents (`great_tusk_crustle_public` and the imported Koushik proxy), not in Alakazam/Ketchum/other meta agents.

Focused repeated check:

- Output: `analysis_outputs/repeat_gtstrict58_line4_focus_g16r3_seed751000_diff.csv`
- Results:
  - Great Tusk: `42 / 96` to `69 / 96` (`+0.2813`, approx z `3.946`).
  - Archaludon: `37 / 96` to `47 / 96` (`+0.1042`).
  - Starmie: `84 / 96` to `91 / 96` (`+0.0729`).
  - Alakazam tubotu-live: `81 / 96` to `79 / 96` (`-0.0209`).
  - Ketchum Alt: `56 / 96` to `53 / 96` (`-0.0312`).
  - Equal selected buckets: `0.6372` to `0.6979`.
  - Public sample 2026-07-03 top20 proxy: `0.6361` to `0.6896`.

Light all-meta screen:

- Output: `analysis_outputs/gtstrict58_line4_all_g12_seed752000_summary.csv`
- Results:
  - Great Tusk: `12 / 24` to `20 / 24`.
  - Equal public buckets: `0.8056` to `0.8222`.
  - Public sample 2026-07-03 top20 proxy: `0.7234` to `0.8484`.
  - Ketchum Alt dropped in this short screen, but the rule cannot trigger from the Ketchum deck list; treat this as native shuffle/setup noise unless live results contradict it.

Smoke checks:

- `analysis_outputs/smoke_gtstrict58_greattusk_753000.jsonl`
- `analysis_outputs/smoke_gtstrict58_tubotu_753100.jsonl`
- `analysis_outputs/smoke_gtstrict58_iono_753200.jsonl`
- `analysis_outputs/smoke_gtstrict58_ketchum_753300.jsonl`
- All completed with `action_errors: 0`.

Decision:

- Promote `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58.tar.gz` as the current next submission candidate over plain `line4markers`.
- Rationale: it keeps the live Iono/Alakazam fixes, restores the previously successful stricter Great Tusk deckout guard on the current base, and has repeated local evidence of a large Great Tusk gain.

## 2026-07-07 Latest Submission Score 935 Feedback

Latest live checks:

- Kaggle CLI still shows latest submitted archive as `submission_archaludon_gt_deckguard.tar.gz`.
- Public score observed during this pass moved from `939.2` to `935.0`, while the Kaggle page panel also showed a stale-looking `933.6`.
- Browser Game History showed the saved losses vs Wasabi and tubotu, a win vs HayatoFujihara, a visible win vs Kamal Das, and an in-progress game vs Yigit Kayali. The browser list was too slow to reliably open the new rows for episode IDs.

Rejected Alakazam active-Duraludon Cape probe:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_alakcapedura`
- Rule:
  - Versus visible Alakazam only, if active `Duraludon (169)` has no energy, no tool, and no Duraludon/Archaludon ex backup exists, allow `Hero's Cape` when the estimated `Powerful Hand` floor or ceiling would be survived after the +100 HP.
- Exact live-step verification stayed intact:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Focused repeated check:
  - Output: `analysis_outputs/repeat_alakcapedura_focus_g16r3_seed755000_diff.csv`
  - Normal Alakazam: `82 / 96` to `80 / 96`.
  - Ketchum Alt: `68 / 96` to `65 / 96`.
  - tubotu-live Alakazam: `90 / 96` to `79 / 96`.
  - Archaludon mirror: `52 / 96` to `39 / 96`.
  - Great Tusk: `76 / 96` to `75 / 96`.
  - Equal public buckets: `0.7667` to `0.7042`.
- Decision: reject. The rule was intended to patch early Alakazam survival, but it worsened every checked bucket except roughly flat Great Tusk, with especially large damage into tubotu-live Alakazam and Archaludon mirror.

Current next submission candidate remains:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58.tar.gz`

Rejected mirror Active 1-Metal evolution probe:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_mirroractive1metal`
- Rule:
  - In detected Archaludon mirrors only, if active `Duraludon (169)` can evolve into `Archaludon ex (190)` and still reach an attack route with one Metal in discard plus current/manual energy, score the evolution above the default `delay Active evolve: 1 Metal`.
- Exact live-step verification stayed intact:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Mirror-only screen:
  - Output: `analysis_outputs/repeat_mirroractive1metal_arch_g24r3_seed756000_diff.csv`
  - Archaludon mirror improved `71 / 144` to `77 / 144`, but the effect was small (`approx_z=0.706`).
- Focused side-effect check:
  - Output: `analysis_outputs/repeat_mirroractive1metal_focus_g16r3_seed757000_diff.csv`
  - Archaludon mirror improved `47 / 96` to `53 / 96`.
  - tubotu-live Alakazam dropped `83 / 96` to `75 / 96`.
  - Ketchum Alt dropped `64 / 96` to `56 / 96`.
  - Great Tusk dropped `69 / 96` to `67 / 96`.
  - Starmie dropped `88 / 96` to `86 / 96`.
  - Equal public buckets dropped `0.7312` to `0.7021`.
- Decision: reject. The intended mirror gain was real but too small, and the broader repeated check showed unacceptable Alakazam-side downside.

Superseded next submission candidate after the later Great Tusk mid-guard check:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`

## 2026-07-07 Continued Local Feedback Engineering

Fresh all-bucket trace for current `gtstrict58`:

- Output:
  - `analysis_outputs/gtstrict58_alltrace_g8_seed760000_summary.csv`
  - `analysis_outputs/gtstrict58_alltrace_g8_seed760000_loss_patterns.csv`
- Main local loss buckets in this thin pass:
  - Great Tusk: `6` losses.
  - Archaludon mirror: `6` losses.
  - Ketchum Alt Alakazam: `6` losses.
  - Ogerpon: `4` losses.
  - Marnie: `4` losses.

Rejected Marnie Duraludon backup port:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_marniedurabackup`
- Rule:
  - Add Marnie-line detection `{646, 647, 648, 649}`.
  - In Marnie games only, if our bench is empty and active HP is `<= 180`, prioritize hand-played `Duraludon`.
  - Under the same condition, allow `Ultra Ball` and prefer active evolution or backup `Duraludon`.
- Exact live-step verification stayed intact:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Repeated Marnie check:
  - Output: `analysis_outputs/repeat_marniedura_gtstrict58_marnie_g60r3_seed761000_diff.csv`
  - Marnie dropped from `318 / 360` to `302 / 360` (`diff=-0.0444`, approx z `-1.722`).
- Decision: reject. The older watchlist rule does not transfer to the current `gtstrict58` base.

Promoted Great Tusk mid guard:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard`
- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`
- Rule-only change relative to `gtstrict58`:
  - In detected Crustle/Great Tusk games only, and only when Great Tusk IDs are visible:
    - raise the Great Tusk-visible `Lillie` low-deck threshold from `25` to `38`;
    - raise the Great Tusk-visible `Explorer` preservation threshold from `24` to `40`;
    - raise the Great Tusk-visible `Ultra Ball` preservation threshold from `24` to `34`.
- Exact live-step verification stayed intact:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Great Tusk focused repeated check:
  - Output: `analysis_outputs/repeat_gtmidguard_greattusk_g40r3_seed763000_diff.csv`
  - Great Tusk improved from `166 / 240` to `190 / 240` (`diff=+0.1000`, approx z `2.503`).
- Side-effect check:
  - Output: `analysis_outputs/repeat_gtmidguard_side_g16r3_seed764000_diff.csv`
  - The rule cannot trigger outside Great Tusk-visible games; non-Great-Tusk bucket swings are treated as native-engine noise unless exact-state audits contradict that.
  - Ketchum Alt and tubotu-live Alakazam moved positive in this pass, Ogerpon/Starmie were flat, and Archaludon mirror moved negative.
- Light all-bucket check:
  - Output: `analysis_outputs/repeat_gtmidguard_all_g8r2_seed765000_diff.csv`
  - Great Tusk improved `22 / 32` to `28 / 32`.
  - Equal public buckets were essentially flat: `0.8146` to `0.8125`.
  - Public sample 2026-07-03 top20 proxy improved `0.7743` to `0.7891`.
  - Public sample 2026-07-02 proxy dropped `0.7656` to `0.7393`, but this includes large non-triggering bucket noise.
- Smoke:
  - `analysis_outputs/smoke_gtmidguard_seed766000_summary.csv`
  - Great Tusk, tubotu-live Alakazam, Ketchum Alt, and Iono/Bellibolt all completed with `errors=0`.
- Archive root verified to contain `main.py`, `deck.csv`, `requirements.txt`, and `cg/` only.
- Decision: promote `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz` as the current next submission candidate over plain `gtstrict58`. It keeps the verified live Iono/Alakazam fixes and narrows the new change to visible Great Tusk games.

Current next submission candidate:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`

Rejected Alakazam Cinderace retreat suppression:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_alaknoretreatdura`
- Rule:
  - Versus Alakazam only, if Cinderace is active and `archaludon_ex_attack_route()` would retreat into a benched `Duraludon` while no benched `Archaludon ex` exists, lower the retreat score to keep Duraludon benched.
  - Motivation came from tubotu-live trace losses where Cinderace promoted, then retreated into Duraludon, and Alakazam removed the line.
- Exact live-step verification stayed intact:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Repeated targeted check:
  - Output: `analysis_outputs/repeat_alaknoretreat_tubotu_g24r3_seed759000_diff.csv`
  - tubotu-live Alakazam dropped from `126 / 144` to `116 / 144` (`diff=-0.0694`, approx z `-1.607`).
- Decision: reject. The replay symptom was real, but preserving the benched Duraludon by skipping retreat costs too much tempo into the live Alakazam mimic.

Superseded by the later promoted Great Tusk mid-guard candidate:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`

## 2026-07-08 Latest gtmidguard Early Feedback

Latest submission check:

- Kaggle API submission ref: `54448251`.
- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
- The first CLI read showed `674.2`, but a direct Kaggle API/browser refresh shortly after showed `878.3`.
- A final Kaggle API refresh in this pass showed `929.9`, very close to the older active fallback's `930.2`.
- Browser game history at the same check showed the latest submission was only about 17 minutes old, with one in-progress game and several visible recent wins. Treat the score as early calibration, not a confirmed regression yet.
- Active fallback remains the older `submission_archaludon_gt_deckguard.tar.gz` at `930.2`.

Rejected Starmie Ultra Ball backup probe:

- Candidate directory: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_starmieub`
- Motivation:
  - Fresh all-trace loss review for `gtmidguard` showed several Starmie losses with empty bench / no-active endings.
  - In `analysis_outputs/gtmidguard_alltrace_g8_seed767000_traces/gtmidguard_vs_starmie/game_0132.jsonl`, the agent preferred Pokegear/Lillie over Ultra Ball while active Cinderace had no bench backup.
- Rule:
  - Versus detected Starmie only, if bench is empty, active HP is within opponent max damage, and two safe discards exist, boost `Ultra Ball`.
  - In the corresponding Ultra Ball search, prefer active `Archaludon ex` evolution, backup `Duraludon`, then fallback `Cinderace`/`Relicanth`.
- Exact live-step verification stayed intact:
  - Alakazam `84569848 steps[92][0]`: still chooses non-ex `Archaludon (840)`.
  - Iono `84566774 steps[171][1]`: still chooses non-ex `Archaludon (840)`.
- Repeated Starmie check:
  - Output: `analysis_outputs/repeat_starmieub_starmie_g40r3_seed768000_diff.csv`
  - Starmie dropped from `211 / 240` to `208 / 240`.
- Decision: reject. The trace symptom was real, but the broad Starmie repeated result got worse.

Fallback screen after the early low score:

- Output: `analysis_outputs/repeat_livefallback_screen_g12r2_seed770000_diff.csv`
- Compared:
  - `gtdeck`: extracted live-stable `submission_archaludon_gt_deckguard.tar.gz`
  - `line4`: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers`
  - `gtstrict`: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58`
  - `gtmid`: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard`
- Notable local results against `gtdeck`:
  - `gtmid` Great Tusk: `22 / 48` to `41 / 48`.
  - `gtmid` public sample 2026-07-03 top20 proxy: `0.6528` to `0.7431`.
  - `gtmid` equal selected buckets: `0.7344` to `0.7656`.
  - `gtmid` mirror/tubotu/Starmie buckets were lower in this small screen, but the Great Tusk-visible rules should not trigger outside visible Great Tusk games, so treat non-triggering swings as native shuffle/setup noise unless exact live-state audits contradict this.

Current decision:

- Do not submit a replacement immediately.
- Keep `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz` under live observation unless it continues to lose after more completed games.
- If a safety replacement is needed before testing a new idea, resubmit the known live-stable `submission_archaludon_gt_deckguard.tar.gz` rather than replacing it with an unproven branch. This avoids dropping the only active 900+ fallback from the latest-two active submissions.

## 2026-07-09 gtmidguard Late Slowdown Check

Current submission status:

- Submission ref: `54448251`.
- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
- Current public score from Kaggle API/browser: `953.8`.
- Browser score panel range: `600 - 1072`, so the submission did peak around the 1000+ band and then settled lower.
- The older active fallback `submission_archaludon_gt_deckguard.tar.gz` is now at `924.9`.

Visible recent game history:

- Win vs `カントー地方マスター`; saved as `analysis_outputs/kaggle_live/submission_54448251/episode_84868280_replay.json`.
  - Opponent was Cynthia Garchomp/Roserade style.
  - Score movement from the episode metadata: `950.40 -> 953.85`.
- Visible losses after the peak:
  - `YIN`
  - `maxwell_ml`
  - `Hase2727`
  - `Topdecking is All You Need`
  - `Rmy`
  - `tantk7`
  - `kuromoka`
- Kaggle page exposed episode IDs for some losses (`84855542`, `84847637`, `84842062`), but both the page and `tools/scan_kaggle_episodes.py` reported them unavailable at this time.

Latest leaderboard snapshot:

- Saved to `analysis_outputs/leaderboard_current_2026_07_09/pokemon-tcg-ai-battle-publicleaderboard-2026-07-08T16_55_22.csv`.
- Relevant current ranks/scores:
  - `Rmy`: rank `8`, score `1111.8`.
  - `Hase2727`: rank `36`, score `1035.0`.
  - `Topdecking is All You Need`: rank `59`, score `1014.4`.
  - `kuromoka`: rank `76`, score `1005.8`.
  - `kawachi`: rank `80`, score `1001.9`.
  - `TeamSCSQ(チームスクスク)`: rank `171`, score `958.3`.
  - `rurumi`: rank `180`, score `953.8`.
  - `maxwell_ml`: rank `237`, score `936.1`.
  - `tantk7`: rank `303`, score `919.1`.
  - `YIN`: rank `371`, score `906.6`.
  - `カントー地方マスター`: rank `403`, score `901.5`.

Interpretation:

- The slowdown is not evidence that the submission became broadly bad. It is still above the previous active fallback and above the earlier `947.0` historical spike.
- The most likely cause is rating calibration plus stronger-matchup exposure:
  - while climbing into the 1000+ band, matchmaking started serving top/high-score teams;
  - visible late losses include several teams currently above our score, especially `Rmy`, `Hase2727`, `Topdecking`, and `kuromoka`;
  - a loss against those teams costs more after the submission has already inflated near the peak.
- The current `gtmidguard` branch was selected because it strongly improved Great Tusk/Crustle-local buckets. The late visible losses are not obviously Great Tusk losses. If they are mainly mirror, Archaludon variants, Starmie, or Alakazam/Ogerpon top builds, the Great Tusk gain will not protect the rating.
- Existing local fallback screen already hinted at this tradeoff:
  - `gtmid` vs `gtdeck` improved Great Tusk heavily (`22 / 48` to `41 / 48`);
  - but small-screen mirror, tubotu Alakazam, and Starmie buckets were lower.

Next analysis direction:

- Do not immediately undo `gtmidguard`; current live score is still good.
- Prioritize collecting downloadable replays for the visible late-loss teams once Kaggle exposes them.
- For local work, focus next probes on high-score non-Great-Tusk pressure:
  - Archaludon mirror sequencing and target priority;
  - Starmie and Alakazam bench-preservation failures;
  - Ogerpon/Cynthia-style high-pressure board states.
- Avoid further Great Tusk-only tuning until the late-loss replays prove that Great Tusk is still a material source of rating loss.

## 2026-07-09 Late Loss Replays Became Available

The late-loss episode IDs that were unavailable immediately after the first slowdown check became downloadable a few hours later. This suggests Kaggle's game history can expose episode IDs before the internal `GetEpisode` / replay endpoint is ready.

Downloaded loss replays:

- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84855542_replay.json`
  - Opponent: `YIN`
  - Result: loss
  - Archetype: `archaludon_metal`
  - End pattern: Archaludon mirror tempo loss; our active `Archaludon ex` was KO'd with no backup active available.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84847637_replay.json`
  - Opponent: `maxwell_ml`
  - Result: loss
  - Archetype: `alakazam_psychic`
  - End pattern: `Alakazam ex` `Powerful Hand` closed the game after our `Metal Defender`; our board was active `Archaludon ex` plus one benched `Duraludon`.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84842062_replay.json`
  - Opponent: `Hase2727`
  - Result: loss
  - Archetype: `Mega Kangaskhan ex` / `Crustle` with heavy Crushing Hammer and energy denial.
  - End pattern: our board collapsed to lone `Cinderace`; `Mega Kangaskhan ex` finished with `Rapid-Fire Combo`.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84835528_replay.json`
  - Opponent: `Topdecking is All You Need`
  - Result: loss
  - Archetype: Cynthia Garchomp/Roserade.
  - End pattern: our lone `Duraludon` was KO'd by `Cynthia's Garchomp ex`.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84826699_replay.json`
  - Opponent: `Rmy`
  - Result: loss
  - Archetype: `alakazam_psychic`
  - End pattern: `Alakazam ex` `Powerful Hand` closed after our `Metal Defender`.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84821720_replay.json`
  - Opponent: `tantk7`
  - Result: loss
  - Archetype: `alakazam_psychic`
  - End pattern: our active `Archaludon ex` had no bench and was KO'd by `Powerful Hand`.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84821115_replay.json`
  - Opponent: `kuromoka`
  - Result: loss
  - Archetype: Cynthia Garchomp/Roserade.
  - End pattern: our lone `Duraludon` was KO'd by `Cynthia's Garchomp ex` `Draconic Buster`.
- `analysis_outputs/kaggle_live/submission_54448251_loss_probe/episode_84814851_replay.json`
  - Opponent: `MeMu`
  - Result: loss
  - Archetype: `alakazam_psychic`
  - End pattern: `Alakazam ex` `Powerful Hand` closed after our `Metal Defender`.

Aggregate read:

- Opponent buckets among downloaded late losses:
  - Alakazam psychic: `4`
  - Cynthia Garchomp/Roserade: `2`
  - Archaludon mirror: `1`
  - Mega Kangaskhan/Crustle energy-denial: `1`
- Great Tusk-specific late losses were not observed in these downloadable games.
- The late slowdown is therefore more specifically a high-pressure attacker / board-preservation problem, not primarily a Great Tusk deckout problem.

Next tuning targets:

- Alakazam: preserve or create a meaningful backup board before `Powerful Hand` endgame, without repeating the rejected broad Cinderace-retreat suppression.
- Cynthia Garchomp: avoid ending on lone `Duraludon`; evaluate whether earlier evolution, backup search, or Boss targeting improves the prize race.
- Mirror: revisit mirror tempo and prize-wall sequencing with exact live replay states, not broad mirror heuristics.

## 2026-07-09 Cynthia Line Search Probe

Candidate directory:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_cynthline`

Motivation:

- Two downloaded late losses were Cynthia Garchomp/Roserade (`Topdecking is All You Need`, `kuromoka`).
- In `episode_84835528`, the current agent treated the matchup as generic and selected `Metal + Hero's Cape` from `Explorer`, discarding `Ultra Ball`. The later board ended as lone `Duraludon` into `Cynthia's Garchomp ex`.
- In `episode_84821115`, the current agent also kept no useful Archaludon line in an early `Explorer` selection while active `Cinderace` was buying time.

Rule-only change:

- Detect visible Cynthia IDs: `Cynthia's Roselia`, `Cynthia's Roserade`, `Cynthia's Gible`, `Cynthia's Gabite`, `Cynthia's Garchomp ex`.
- Versus detected Cynthia only:
  - treat opponent max damage as `350`;
  - raise `Explorer` priority for `Duraludon`, `Archaludon ex`, and `Ultra Ball` when our Archaludon line is missing or incomplete;
  - allow `Ultra Ball` through the empty-bench gate when it can fuel Alloy or has safe discard material;
  - make `Ultra Ball` prefer `Archaludon ex` over another backup `Duraludon` when a `Duraludon` line is already available.

Exact replay-state checks:

- `episode_84835528` step `69` changed from taking `Metal + Hero's Cape` to taking `Metal + Ultra Ball`.
- `episode_84821115` step `17` changed from a zero-score generic keep to preserving `Ultra Ball` for the line-search route.

Local caveat:

- `analysis_outputs/cynthline_side_g8_seed782000_summary.csv` completed with `errors=0`, but the packaged engine did not produce stable identical games across repeated same-seed single runs. Treat non-Cynthia bucket win-rate swings in that file as unsuitable for promotion/rejection by themselves.
- No local Cynthia mimic is available yet, so the promotion case is based on concrete downloadable loss-replay decisions rather than a full Cynthia self-play batch.

## 2026-07-09 Cynthline Live Regression and Replay Recovery

Latest submitted archive:

- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_cynthline.tar.gz`
- Kaggle submission id: `54470098`
- Current public score check: `814.0`

Downloaded visible Game History replays:

- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84907144_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84907518_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84907764_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84914894_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84917825_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84938737_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84947741_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84961535_replay.json`
- `analysis_outputs/kaggle_live/submission_54470098_probe/episode_84975135_replay.json`

Visible loss buckets:

- Mega Lucario: `2`
- Dragapult: `1`
- Great Tusk / Crustle: `1`
- Alakazam psychic: `1`

Read:

- The Cynthia-specific fix did not address the visible live loss mix after submission.
- Cynthline should not be promoted further until a local Cynthia mimic exists and broader buckets are protected.
- The next submission should be a safety replacement, not another narrow branch.

Fallback comparison:

- Output: `analysis_outputs/fallback_compare_after_cynthline_g8_seed800000_summary.csv`
- `gtdeck` was strongest in the small fair-seed screen:
  - `public_sample_2026_07_02_top20`: `0.8125`
  - `public_sample_2026_07_03_top20`: `0.7826`
  - `equal_public_buckets`: `0.7857`
  - `bucket:lucario`: `16 / 16`
  - `bucket:alakazam`: `15 / 16`
- `gtmid` stayed better into `bucket:great_tusk` (`13 / 16` vs `8 / 16`), so Great Tusk remains a follow-up target.

Decision:

- Submit `submission_archaludon_gt_deckguard.tar.gz` as the one safety replacement after the 6-hour interval.
- Kaggle submission id after submit: `54485645` (`PENDING` at the first post-submit check).
- Do not submit another experimental archive in the same cycle.
- Next analysis target after the replacement gets games: add a local Dragapult mimic from extracted live deck lists, then inspect Great Tusk and Mega Lucario losses with exact action traces.

## 2026-07-09 Stable Replacement Early Read and Dragapult Mimic

Submitted stable replacement:

- Archive: `submission_archaludon_gt_deckguard.tar.gz`
- Submission id: `54485645`
- First completed score check: `732.9`

Downloaded early replays:

- `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84978587_replay.json`
  - Type: validation self-play
  - Result: win from the target agent row, updated score `600`
- `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84978674_replay.json`
  - Type: public
  - Opponent: `Sifar12`
  - Opponent submission id: `53800074`
  - Opponent archetype: `mega_lucario`
  - Result: win, score `600 -> 732.998`

Read:

- The `732.9` score is not currently evidence of many losses.
- At this point the replacement has only one visible public game, and it won.
- Respect the 6-hour cadence; the next submit window after `2026-07-09T07:06:35Z` is `2026-07-09T13:06:35Z` / `2026-07-09 22:06:35 JST`.

New local meta opponent:

- Added directory: `meta_agents/dragapult_live_simple`
- Source deck: live Dragapult rows from `episode_84907518` and `episode_84961535`
- Registered bucket: `dragapult`
- Registered scenario: `live_dragapult_2026_07_09`

Local checks:

- Smoke: `analysis_outputs/dragapult_smoke_summary.jsonl`
- Focused compare: `analysis_outputs/dragapult_added_compare_g12_seed920000_summary.csv`
- Broad compare: `analysis_outputs/gtdetect_lite_broad_g8_seed950000_summary.csv`

Candidate probe:

- Created `submission_archaludon_gtdeckguard_gtdetect_lite`
- Change: only detect `Great Tusk` as part of the existing Crustle/deckout matchup.
- Focused 4-bucket run looked promising:
  - `gtdetect` equal-public over Alakazam/Great Tusk/Lucario/Dragapult proxy: `0.8438`
  - `gtdeck`: `0.7891`
  - `gtmid`: `0.8516`
- Broad all-bucket run rejected it:
  - `gtdetect` `equal_public_buckets`: `0.7812`
  - `gtdeck` `equal_public_buckets`: `0.8359`
  - `gtmid` `equal_public_buckets`: `0.8594`
  - `gtdetect` `public_sample_2026_07_03_top20`: `0.7708`, below both `gtdeck` (`0.8247`) and `gtmid` (`0.8281`)

Decision:

- Do not submit `gtdetect_lite`.
- Continue monitoring `54485645`; its low visible score is still early calibration, not a loss sample.
- If `54485645` remains bad after enough public games, the current evidence favors restoring `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz` over submitting the rejected `gtdetect_lite`.

## 2026-07-09 Stable Replacement Live Losses and Lucario Rescue Probe

Later score check:

- `submission_archaludon_gt_deckguard.tar.gz` / submission `54485645` fell to `603.5`.
- Visible public games recovered:
  - `episode_84978674`: win vs `Sifar12`, `mega_lucario`
  - `episode_84979147`: loss vs `Nicolai Karcher`, `mega_lucario`
  - `episode_84979645`: loss vs `akr2428`, `mega_lucario`
  - `episode_84980129`: win vs `zone9studio`, Mega Zygarde / Koraidon / Mega Kangaskhan fighting deck

Replay files:

- `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84979147_replay.json`
- `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84979645_replay.json`
- `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84980129_replay.json`

Loss reads:

- `episode_84979147`: board collapsed to lone `Cinderace (666)` after active `Archaludon ex` was KO'd; opponent closed with the Lucario/Solrock-Hariyama line.
- `episode_84979645`: Cinderace-only start. At Explorer selection, visible cards included `Ultra Ball (1121)` and `Archaludon ex (190)`, but the agent selected two Metal Energy and discarded the recovery route. Mega Lucario then KO'd the lone Cinderace.

Existing Lucario branch check:

- Output: `analysis_outputs/lucario_branches_compare_g8_seed960000_summary.csv`
- `gtmid` was the best all-around candidate in this check:
  - `equal_public_buckets`: `0.875`
  - `bucket:lucario`: `16 / 16`
  - `bucket:great_tusk`: `15 / 16`
  - `bucket:dragapult`: `16 / 16`
- Lucario-specialist branches did not beat it broadly:
  - `lucwall` had only `12 / 16` into Lucario and collapsed into Great Tusk (`3 / 16`).
  - `lucboss` and `lucrexplorer` were narrower and had lower equal-bucket scores.

New rejected probe:

- Candidate: `submission_archaludon_gtmid_lucario_explorer_rescue`
- Change: port only the Cinderace-solo Lucario Explorer rescue into `gtmid`.
- Exact replay decision check:
  - In `episode_84979645`, Explorer step changed from Metal + Metal to `Ultra Ball + Metal`.
- Local key check:
  - Output: `analysis_outputs/gtmid_lucrescue_key_g16_seed970000_summary.csv`
  - `gtmid`: `equal_public_buckets 0.8375`, `bucket:lucario 0.9062`
  - `gtmid_lucrescue`: `equal_public_buckets 0.7875`, `bucket:lucario 0.875`
- Decision: reject. The exact replay symptom is real, but the rule lowers even the Lucario bucket in local play and hurts Alakazam / mirror.

Next submission posture:

- Do not submit before `2026-07-09 22:06:35 JST`.
- If no stronger candidate emerges, restore the known stronger active archive:
  - `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`
- Do not submit `gtdetect_lite` or `gtmid_lucario_explorer_rescue`.

## 2026-07-09 Live Lucario / Alakazam Follow-up

Current live read:

- Latest submitted archive: `submission_archaludon_gt_deckguard.tar.gz` / submission `54485645`
- Score recovered from `603.5` to `724.4` after more games, but still below the prior stable candidates.
- Latest visible loss recovered:
  - `episode_84982062`: loss vs `Noor`, `alakazam_psychic`
  - Saved at `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84982062_replay.json`

Local opponent additions:

- Added `meta_agents/mega_lucario_live_simple` from the live Nicolai/Sifar-style deck.
- Added `lucario_live` and `live_lucario_2026_07_09` to `tools/run_meta_suite.py`.
- Smoke passed:
  - `analysis_outputs/lucario_live_smoke_summary.jsonl`

Candidate comparison:

- Output: `analysis_outputs/candidate_compare_live_g10_seed990000_summary.csv`
- `gtmid` remained best on the live-relevant equal bucket:
  - `gtmid`: `equal_public_buckets 0.87`, `bucket:great_tusk 0.70`, `bucket:lucario 0.95`, `bucket:lucario_live 0.90`, `bucket:dragapult 1.00`
  - `gtdeck`: `equal_public_buckets 0.81`, weak into Great Tusk (`0.45`)
  - `chandlow`: `equal_public_buckets 0.84`, strong into Alakazam/Dragapult/Lucario but too weak into Great Tusk (`0.35`)
- Existing Chandlow + Great Tusk variants were checked:
  - Output: `analysis_outputs/chand_gt_candidates_g8_seed991000_summary.csv`
  - `gtmid`: `equal_public_buckets 0.8875`, `public_sample_2026_07_03_top20 0.8819`
  - Best Chandlow hybrid (`chgtsep`) improved Chandlow but still trailed `gtmid`: `equal_public_buckets 0.8625`, `public_sample_2026_07_03_top20 0.8681`

Noor Alakazam loss read:

- The board collapsed to active `Archaludon ex` with an empty bench.
- Earlier in the game, an Ultra Ball search could take `Duraludon (169)` as backup, but `gtmid` valued `Archaludon ex (190)` higher.
- Probe candidate: `submission_archaludon_gtmid_alakdura_backup`
  - Change: in Alakazam matchup, when the board line is thin, prioritize taking Duraludon backup from search.
  - Exact replay decision changed at step 48 from Archaludon ex to Duraludon.
- Broad local compare rejected the probe:
  - Output: `analysis_outputs/alakdura_compare_g14_seed993000_summary.csv`
  - `gtmid`: `equal_public_buckets 0.9000`, `public_sample_2026_07_03_top20 0.8849`, `bucket:alakazam 0.8929`
  - `alakdura`: `equal_public_buckets 0.8857`, `public_sample_2026_07_03_top20 0.8413`, `bucket:alakazam 0.7857`

Decision:

- Do not submit `submission_archaludon_gtmid_alakdura_backup`.
- Current next submission candidate remains:
  - `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`
- Submit only after `2026-07-09 22:06:35 JST` and only if no stronger validated candidate appears before then.

### 2026-07-09 16:49 JST Score Check

Live score:

- `submission_archaludon_gt_deckguard.tar.gz` / submission `54485645`: `791.7`
- It has recovered from `603.5 -> 724.4 -> 791.7`, but still trails:
  - `cynthline`: `814.0`
  - historical `gtmid`: `918.5`

New visible history:

- `episode_84983053`: win vs `Kei Yamashita`, `marnie_grimmsnarl`
  - Saved at `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84983053_replay.json`
  - Deck extracted to `analysis_outputs/kaggle_live/submission_54485645_probe/decks_refresh_84983053`
- `episode_84982062`: loss vs `Noor`, `alakazam_psychic`
  - Already analyzed above.

Loss index:

- Regenerated `analysis_outputs/kaggle_live/saved_loss_replays_summary.csv`
- Current saved loss replay count: `37`

Decision:

- No submission now: current time is `2026-07-09 16:48 JST`, before the next allowed submit time `2026-07-09 22:06:35 JST`.
- Keep watching whether `54485645` stabilizes above `814`; if it stays below the historical `gtmid` range, submit `gtmid` at the next allowed window.

## 2026-07-09 Live Noor / Kei Local Opponents

New local opponents:

- `meta_agents/alakazam_noor_live_84982062_simple`
  - Source: live loss `episode_84982062`, `Noor`, `alakazam_psychic`
  - Based on `meta_agents/alakazam_psychic_public_simple`, with the live Noor deck list.
- `meta_agents/marnie_kei_live_84983053_simple`
  - Source: live win `episode_84983053`, `Kei Yamashita`, `marnie_grimmsnarl`
  - Based on `submission_marnie_variant_tonakaiiii`, with the live Kei deck list.

Registration:

- Added buckets to `tools/run_meta_suite.py`:
  - `alakazam_noor_live`
  - `marnie_kei_live`
- Added focused scenarios:
  - `live_noor_alakazam_2026_07_09`
  - `live_kei_marnie_2026_07_09`

Smoke checks:

- `analysis_outputs/noor_alakazam_smoke_summary.jsonl`: passed, no action errors.
- `analysis_outputs/kei_marnie_smoke_summary.jsonl`: passed, no action errors.

Focused live comparison:

- Output: `analysis_outputs/live_noor_kei_compare_g16_seed996000_summary.csv`
- Compared `gtdeck`, `gtmid`, `cynthline`, and the rejected `alakdura` probe against:
  - `alakazam_noor_live`
  - `marnie_kei_live`
  - `lucario_live`
  - `great_tusk`
  - `dragapult`
- Results:
  - `gtmid`: `equal_public_buckets 0.8812`
  - `cynthline`: `equal_public_buckets 0.8812`
  - `alakdura`: `equal_public_buckets 0.8688`
  - `gtdeck`: `equal_public_buckets 0.8250`
- Interpretation:
  - `gtdeck` is still weak into Great Tusk (`0.4688`) despite good Lucario live performance.
  - `cynthline` slightly improves Noor Alakazam / Lucario live in this focused run, but has already underperformed live at `814.0`.
  - `gtmid` keeps the best Great Tusk / Kei Marnie balance.

All-bucket `gtmid` vs `cynthline` check:

- Output: `analysis_outputs/gtmid_cynthline_all_g6_seed997000_summary.csv`
- With all currently registered local buckets:
  - `gtmid`: `equal_public_buckets 0.8202`
  - `cynthline`: `equal_public_buckets 0.8070`
- On `public_sample_2026_07_03_top20`:
  - `gtmid`: `0.8380`
  - `cynthline`: `0.7130`

Decision:

- Keep `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz` as the next submission candidate.
- Do not submit before `2026-07-09 22:06:35 JST`.
- If latest `54485645` remains below `cynthline` / historical `gtmid` by the submit window, submit `gtmid`.

## 2026-07-09 Late-Afternoon Replay Mining and Family Check

Current time / submission state:

- Local check time: `2026-07-09 17:03 JST`.
- Kaggle CLI now reports latest `submission_archaludon_gt_deckguard.tar.gz` (`54485645`) public score as `835.9`.
- Last submission time remains `2026-07-09 07:06:35 UTC` / `16:06:35 JST`.
- Next allowed submit time remains `2026-07-09 22:06:35 JST`.

Episode mining:

- Scanned `84983054-84986000` for submission `54485645`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_84983054_84986000.csv`
  - Hits: `1`
  - New saved replay: `analysis_outputs/kaggle_live/submission_54485645_probe/episode_84983544_replay.json`
  - Result: win vs `Aib4`, updated score `824.4652970578061`.
- Scanned `84986001-84990000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_84986001_84990000.csv`
  - Existing episodes: `0`
  - Hits: `0`

Latest loss pattern:

- Latest submission losses still available locally:
  - `84982062`: loss vs `Noor`, `alakazam_psychic`
  - `84979645`: loss vs `akr2428`, `mega_lucario`
  - `84979147`: loss vs `Nicolai Karcher`, `mega_lucario`
- All three terminal boards share the same practical failure mode: our bench is empty and the active Pokemon is KO'd.
- The Alakazam loss is not a simple "never benched backup" error:
  - The agent did take/play Duraludon backup earlier.
  - By the final turn, all four Duraludon copies had been used as active / bench / evolution material or were already in discard.
  - A naive Cinderace-as-backup patch is risky because Cinderace is mainly enabled by setup `Explosiveness`; it does not appear to be a normal reliable bench candidate after setup.

Focused family check:

- Output: `analysis_outputs/live_loss_family_g12_seed998000_summary.csv`
- Candidates:
  - `gtdeck`
  - `gtmid`
  - `cynthline`
  - `marniedura`
  - `alaknoretreat`
  - `alakcapedura`
- Focus buckets: `alakazam_noor_live`, `lucario_live`, `great_tusk`, `marnie_kei_live`, `dragapult`.
- Total focused wins:
  - `alaknoretreat`: `107 / 120`
  - `alakcapedura`: `104 / 120`
  - `gtmid`: `104 / 120`
  - `marniedura`: `103 / 120`
  - `cynthline`: `102 / 120`
  - `gtdeck`: `100 / 120`

Broad family check:

- Output: `analysis_outputs/broad_family_g6_seed999000_summary.csv`
- Candidates: `gtdeck`, `gtmid`, `alaknoretreat`, `alakcapedura`, `marniedura`.
- All local game wins:
  - `gtmid`: `196`
  - `alakcapedura`: `194`
  - `alaknoretreat`: `193`
  - `marniedura`: `190`
  - `gtdeck`: `186`
- Equal public buckets:
  - `gtmid`: `0.8596`
  - `alakcapedura`: `0.8509`
  - `alaknoretreat`: `0.8465`
  - `marniedura`: `0.8333`
  - `gtdeck`: `0.8158`
- `public_sample_2026_07_03_top20`:
  - `alakcapedura`: `0.8866`
  - `alaknoretreat`: `0.8102`
  - `marniedura`: `0.8056`
  - `gtmid`: `0.7894`
  - `gtdeck`: `0.7824`

Decision:

- Do not submit before the six-hour gate.
- Keep `gtmid` as the first fallback because it remains strongest on equal buckets and on the live Alakazam/Lucario failure pattern.
- Keep `alakcapedura` as an environment-shift candidate: it is stronger on the `2026-07-03_top20` proxy and Ogerpon/Starmie-heavy proxies, but it is weaker into the Noor/Ketchum Alakazam buckets that caused a live loss.
- Current latest `54485645` should continue running unless it clearly stalls below the historical `gtmid` score band by the next submit window.

## 2026-07-09 17:12 JST Current Score and Aib4 Lucario Bucket

Kaggle status:

- Current local time: `2026-07-09 17:12 JST`.
- Latest submission `submission_archaludon_gt_deckguard.tar.gz` now reports public score `871.7`.
- This is still before the next allowed submission time `2026-07-09 22:06:35 JST`, so no submit was made.

Replay mining:

- Rescanned `84983545-84992000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_84983545_84992000_rescan.csv`
  - Existing episodes: `16`
  - Hits for submission `54485645`: `0`
  - Downloaded replays: `0`
- Interpretation: the score rise from `835.9` to `871.7` is likely a delayed rating update from already-seen public games or from games not yet available through this anonymous/internal API route.

New local opponent:

- Extracted `episode_84983544` decks to `analysis_outputs/kaggle_live/submission_54485645_probe/decks_refresh_84983544`.
- Opponent `Aib4` is classified as `mega_lucario`.
- Added `meta_agents/mega_lucario_aib4_live_84983544_simple`.
  - Agent logic copied from `meta_agents/mega_lucario_live_simple`.
  - Deck replaced with Aib4's live deck:
    - `673 673 674 674 675 675 676 676 676 677 677 677 678 678 678 678 1102 1102 1102 1102 1123 1123 1141 1141 1141 1141 1142 1142 1142 1142 1152 1152 6 1159 1182 1182 1192 1192 1192 1192 1227 1227 1227 1227 6 6 6 6 6 6 6 6 6 6 6 6 6 1182 677 1252`
- Registered in `tools/run_meta_suite.py` as:
  - bucket `lucario_aib4_live`
  - scenario `live_aib4_lucario_2026_07_09`

Smoke and quick comparison:

- Smoke output: `analysis_outputs/aib4_lucario_smoke_summary.jsonl`
  - `gtmid` vs Aib4 mimic: 2 games, action errors `0`.
- Comparison output: `analysis_outputs/aib4_lucario_compare_g12_seed1002000_summary.csv`
  - `gtdeck` vs `lucario_aib4_live`: `24 / 24`, win rate `1.0`
  - `gtmid` vs `lucario_aib4_live`: `20 / 24`, win rate `0.8333`

Decision update:

- The current live score rise and Aib4 local check support continuing to let `gtdeck` run until the submit window.
- `gtmid` remains the first fallback if `gtdeck` stalls below the historical stable band, but Aib4/Lucario evidence is not a reason by itself to replace `gtdeck`.

## 2026-07-09 17:20 JST Score Dip and Post-Aib4 Candidate Checks

Kaggle status:

- Current local time: `2026-07-09 17:20 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score changed to `856.8`.
- Still before the next allowed submission time `2026-07-09 22:06:35 JST`; no submit was made.

Episode mining:

- Scanned `84992001-84995000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_84992001_84995000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`
- No new loss replay is currently available from the internal episode scan.

Post-Aib4 broad check:

- Output: `analysis_outputs/post_aib4_broad_g4_seed1003000_summary.csv`
- Candidates: `gtdeck`, `gtmid`, `chand947`, `alakcapedura`.
- Equal public buckets:
  - `alakcapedura`: `0.9000`
  - `gtmid`: `0.8938`
  - `gtdeck`: `0.8500`
  - `chand947`: `0.8125`
- `public_sample_2026_07_03_top20`:
  - `alakcapedura`: `0.8993`
  - `gtmid`: `0.8333`
  - `gtdeck`: `0.7778`
  - `chand947`: `0.7257`
- Initial read: `alakcapedura` looked promising, but the sample was small and Alakazam-sensitive.

Top-3 live-focus check:

- Output: `analysis_outputs/top3_live_focus_g10_seed1004000_summary.csv`
- Candidates: `gtdeck`, `gtmid`, `alakcapedura`.
- Focus buckets:
  - `alakazam_noor_live`
  - `alakazam_ketchum_alt`
  - `alakazam_tubotu_live`
  - `great_tusk`
  - `lucario_live`
  - `lucario_aib4_live`
  - `marnie_kei_live`
  - `dragapult`
- Equal focus buckets:
  - `gtdeck`: `132 / 160` (`0.8250`)
  - `gtmid`: `129 / 160` (`0.8063`)
  - `alakcapedura`: `122 / 160` (`0.7625`)
- Notable bucket splits:
  - Noor Alakazam: `gtdeck 0.9000`, `alakcapedura 0.9000`, `gtmid 0.6500`
  - Great Tusk: `gtmid 0.8500`, `gtdeck 0.5500`, `alakcapedura 0.4500`
  - Aib4 Lucario: `gtdeck 0.9000`, `gtmid 0.8000`, `alakcapedura 0.8000`
  - Kei Marnie: `gtmid 0.9500`, `gtdeck 0.9000`, `alakcapedura 0.7500`
- `public_sample_2026_07_03_top20` inside this focused opponent subset:
  - `gtmid`: `0.8500`
  - `gtdeck`: `0.5500`
  - `alakcapedura`: `0.4500`

Decision update:

- Do not replace current `gtdeck` before the submit window.
- Current `gtdeck` is still the best local choice for the newly visible Lucario/Noor-style live mix.
- `gtmid` remains the fallback if the environment shifts toward Great Tusk / top20 proxy pressure or if the live score remains materially below the historical `918.5` baseline at the next submit window.
- `alakcapedura` remains a secondary environment-shift candidate, but the focused check shows it is too weak into Great Tusk and some live buckets to submit immediately.

## 2026-07-09 17:26 JST Live Coverage Aggregation

Kaggle status:

- Current local time: `2026-07-09 17:26 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score: `870.6`.
- Still before `2026-07-09 22:06:35 JST`; no submit was made.

Episode mining:

- Scanned `84995001-84998000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_84995001_84998000.csv`
  - Existing episodes: `0`
  - Hits: `0`

Tooling update:

- Updated `tools/aggregate_meta_summaries.py` so coverage calculations include the live buckets now registered in `tools/run_meta_suite.py`:
  - `dragapult`
  - `lucario_live`
  - `lucario_aib4_live`
  - `alakazam_noor_live`
  - `marnie_kei_live`
  - `alakazam_tubotu_live`

Aggregate outputs:

- Equal buckets with live coverage:
  - `analysis_outputs/aggregate_equal_gtdeck_gtmid_alakcapedura_livecoverage_20260709_1728.csv`
  - `analysis_outputs/aggregate_equal_fullcoverage_gtdeck_gtmid_alakcapedura_20260709_1728.csv`
- Top20 full coverage:
  - `analysis_outputs/aggregate_top20_fullcoverage_gtdeck_gtmid_alakcapedura_20260709_1728.csv`

Full-coverage equal bucket view:

- Source: `analysis_outputs/post_aib4_broad_g4_seed1003000_summary.csv`
- `alakcapedura`: `0.9000`
- `gtmid`: `0.8938`
- `gtdeck`: `0.8500`

Full-coverage `public_sample_2026_07_03_top20` view:

- `alakcapedura`: `0.8993` in `post_aib4_broad_g4_seed1003000`
- `alakcapedura`: `0.8866` in `broad_family_g6_seed999000`
- `gtmid`: best full-coverage rows are `0.8380` / `0.8333` / `0.8281`
- `gtdeck`: best full-coverage rows are `0.8247` / `0.8073` / `0.7824` / `0.7778`

Interpretation:

- If choosing only from broad/full-coverage local proxies, `alakcapedura` is increasingly attractive.
- If choosing from the freshest live mix, current `gtdeck` remains defensible because it leads the `top3_live_focus_g10_seed1004000` live-focus check.
- The next submit-window decision should therefore depend on the live score and any newly recoverable losses:
  - keep `gtdeck` if it keeps recovering toward the historical 900+ band,
  - submit `gtmid` if Great Tusk/top20-like losses appear or current stalls,
  - consider `alakcapedura` only if leaderboard/live samples look broader and less Noor/Lucario-heavy.

## 2026-07-09 17:50 JST Loss Replay Triage And Next Candidate

Kaggle status:

- Current local time checked: `2026-07-09 17:48 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score moved through `880.0 -> 871.4 -> 860.8`.
- Latest submission time remains `2026-07-09 16:06:35 JST`; no submit was made.

Episode mining:

- Scanned `84998001-85003000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_84998001_85003000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`
- No additional public replay for the latest submission was recoverable from this range.

Saved loss replay triage:

- Output: `analysis_outputs/kaggle_live/loss_terminal_classification_20260709_v2.csv`
- Latest submission real losses:
  - `84982062` vs Noor Alakazam: `no_pokemon_after_ko`
  - `84979645` vs akr2428 Mega Lucario: `no_pokemon_after_ko`
  - `84979147` vs Nicolai Karcher Mega Lucario: `no_pokemon_after_ko`
- Main live failure mode is therefore not action error, but losing with no bench after the active attacker is KO'd.
- Decision inspection found one concrete early-Lucario issue:
  - In `84979645`, Cinderace was active with no bench.
  - Explorer saw `Ultra Ball` but the current policy took Energy instead, losing the Duraludon search route.

Candidate experiments:

- `submission_archaludon_gtdeckguard_gt_earlypreserve`
  - Adjusted Great Tusk draw/search preservation thresholds.
  - `analysis_outputs/gtearly_gt_focus_g20_seed1005000_summary.csv`
  - Great Tusk only:
    - `gtdeck`: `0.475`
    - `gtearly`: `0.550`
    - `gtmid`: `0.775`
  - Direction was correct, but still weaker than existing `gtmid`.
- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_benchguard`
  - Broad emergency Ultra Ball rule when bench is empty.
  - Rejected because it overused Ultra Ball into Noor Alakazam and weakened key buckets.
- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_cinderbench`
  - Narrowed emergency Ultra Ball rule to active Cinderace + empty bench only.
  - Rejected for now because live-focus comparison still underperformed `gtmid`, `gtdeck`, and `alakcapedura` in several buckets.

Latest candidate comparison:

- `analysis_outputs/benchguard_broad_g6_seed1008000_summary.csv`
  - Equal public buckets:
    - `alakcapedura`: `0.8583`
    - `gtmid`: `0.8208`
    - `benchguard`: `0.8208`
    - `gtdeck`: `0.8125`
  - `public_sample_2026_07_03_top20`:
    - `alakcapedura`: `0.8472`
    - `gtmid`: `0.7755`
    - `benchguard`: `0.7731`
    - `gtdeck`: `0.7569`
- `analysis_outputs/cinderbench_live_focus_g10_seed1009000_summary.csv`
  - Equal live focus:
    - `alakcapedura`: `0.8917`
    - `gtmid`: `0.8833`
    - `gtdeck`: `0.8667`
    - `cinderbench`: `0.8250`

Aggregate view:

- Equal bucket full coverage:
  - `analysis_outputs/aggregate_equal_candidates_20260709_1749.csv`
  - `alakcapedura` leads the full-coverage rows seen in this pass.
- Top20 full coverage:
  - `analysis_outputs/aggregate_top20_20260703_candidates_20260709_1749.csv`
  - `alakcapedura` leads the full-coverage top20 rows (`0.8866`, `0.8472`).

Next submit-window decision:

- If current `gtdeck` remains in the mid-800s and no new replay contradicts this read, submit `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_alakcapedura.tar.gz` next.
- If the live score recovers toward 900+ before the submit window, keep observing.
- `gtmidguard` remains fallback if newly recovered losses point specifically to Great Tusk/deckout rather than the broader top20 proxy.

## 2026-07-09 17:54 JST Submit-Wait Recheck

Kaggle status:

- Current local time checked: `2026-07-09 17:52 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score fell further to `843.0`.
- Next allowed submit time is still approximately `2026-07-09 22:06:35 JST`; no submit was made.

Episode mining:

- Scanned `85003001-85008000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_85003001_85008000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`

Package check:

- Verified `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_alakcapedura.tar.gz`.
- Archive contents: `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
- Extracted package smoke ran without action errors:
  - `analysis_outputs/alakcapedura_archivecheck_g2_seed1010000_summary.csv`

Thicker live-focus comparison:

- Output: `analysis_outputs/submit_wait_live_g20_seed1011000_summary.csv`
- Candidates: `gtdeck`, `gtmid`, `alakcapedura`.
- Buckets: Noor Alakazam, live Lucario, Aib4 Lucario, Great Tusk, Kei Marnie, Dragapult.
- Equal live focus:
  - `gtmid`: `0.8750`
  - `alakcapedura`: `0.8375`
  - `gtdeck`: `0.8167`
- Important bucket splits:
  - Noor Alakazam: `gtdeck 0.7000`, `alakcapedura 0.7000`, `gtmid 0.6250`
  - Great Tusk: `gtmid 0.8000`, `alakcapedura 0.7000`, `gtdeck 0.4750`
  - Kei Marnie: `gtmid 0.9500`, `gtdeck 0.9000`, `alakcapedura 0.8500`
  - Dragapult: `gtmid 1.0000`, `gtdeck 0.9750`, `alakcapedura 0.9250`

Updated next submit-window decision:

- Because the live score fell to `843.0`, keeping current `gtdeck` is no longer attractive unless it unexpectedly recovers before the window.
- The thicker live-focus check shifts the first replacement candidate back to:
  - `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`
- `alakcapedura` remains the broad/top20-proxy candidate, but is now second choice because the latest live-focus check and its prior real Kaggle score evidence favor `gtmidguard`.

## 2026-07-09 18:00 JST Opponent Coverage Update

Kaggle status:

- Current local time checked: `2026-07-09 17:56 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score was `854.4`.
- Still before the next submit window; no submit was made.

Submission package checks:

- Verified `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
  - Archive contents: `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
  - Extracted package hashes matched the source directory.
  - Smoke output: `analysis_outputs/gtmidguard_archivecheck_g3_seed1012000_summary.csv`
  - No action errors.

Opponent-suite update:

- Added `rocket_mewtwo_spidops` to `tools/run_meta_suite.py`.
  - Path: `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple`
- Added the same bucket to `tools/aggregate_meta_summaries.py`.
- Added weight `2` to `public_sample_2026_07_03_top20`, matching the earlier 2026-07-03 top20 extraction note where `rocket_mewtwo_spidops` appeared twice.

Rocket Mewtwo check:

- Output: `analysis_outputs/rocket_mewtwo_added_g20_seed1013000_summary.csv`
- `rocket_mewtwo_spidops` only:
  - `gtdeck`: `1.000`
  - `gtmid`: `0.975`
  - `alakcapedura`: `1.000`
- This bucket is not a reason to avoid `gtmidguard`; all three candidates are strong locally.

Rocket-inclusive broad check:

- Output: `analysis_outputs/with_rocket_broad_g4_seed1014000_summary.csv`
- Equal public buckets:
  - `alakcapedura`: `0.8631`
  - `gtmid`: `0.8512`
  - `gtdeck`: `0.8095`
- `public_sample_2026_07_03_top20` with Rocket bucket:
  - `alakcapedura`: `0.8684`
  - `gtdeck`: `0.8454`
  - `gtmid`: `0.7599`
- This re-raises `alakcapedura` as a strong broad/top20-proxy option, but it conflicts with the thicker live-focus result where `gtmid` led.

Updated submit-window decision:

- If the ladder still looks like the latest live-focus buckets or the score remains volatile without new replay evidence, `gtmidguard` remains the safer first replacement because it has prior real Kaggle evidence at `918.5`.
- If a fresh pre-submit local check or recovered replay suggests broader public-top pressure rather than the current live-focus mix, `alakcapedura` is the better broad/top20-proxy candidate.
- Do not submit before `2026-07-09 22:06:35 JST`.

## 2026-07-09 18:06 JST Leaderboard And Replay Availability

Kaggle status:

- Current local time checked: `2026-07-09 18:00 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score: `865.3`.
- Still before the next submit window; no submit was made.

Replay mining:

- Patched `tools/scan_kaggle_episodes.py` so transient Kaggle network disconnects such as `RemoteDisconnected` are recorded as non-hit errors instead of aborting the whole scan.
- Re-scanned `85008001-85013000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_85008001_85013000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`
- No newer public replay is currently recoverable for the latest submission.

Current leaderboard snapshot:

- Downloaded current public leaderboard:
  - `analysis_outputs/leaderboard_current_2026_07_09_1800/pokemon-tcg-ai-battle-publicleaderboard-2026-07-09T09_05_39.csv`
- Visible current team row in the downloaded CSV:
  - `rurumi`: rank `554`, score `877.1`, last submission `2026-07-09 07:06:35 UTC`.
- CLI latest submission score is lower (`865.3`), which would be about rank `612` if inserted into this CSV snapshot.
- Score landmarks in this snapshot:
  - Rank `100`: `989.5`
  - Rank `200`: `941.4`
  - Rank `500`: `884.8`
  - Rank `1000`: `816.2`

Public episode index:

- Checked `kaggle/pokemon-tcg-ai-battle-episodes-index`; latest manifest file was created `2026-07-09 00:02 UTC`.
- The manifest still only lists daily datasets through `2026-07-03`.
- There is no newer public top-episode dataset to download yet.

Decision impact:

- The current submission is below the rank-500 score landmark and well below the historical `gtmidguard` Kaggle score (`918.5`).
- Unless the current score recovers near the 900+ band before the submit window, replacing it remains justified.
- Pre-submit choice remains:
  - `gtmidguard` if prioritizing live-focus / proven-Kaggle evidence.
  - `alakcapedura` if a final pre-submit check points toward broader top20 proxy pressure.

## 2026-07-09 18:14 JST Live Aggregate Recheck

Kaggle status:

- Current local time checked: `2026-07-09 18:07 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score recovered to `877.1`.
- This is close to the rank-500 landmark (`884.8`) in the `2026-07-09T09:05:39 UTC` leaderboard snapshot, but still below the desired 900+ replacement threshold.
- Still before the next submit window; no submit was made.

Replay mining:

- Scanned `85013001-85017000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_85013001_85017000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`

Pre-window live-plus-Rocket comparison:

- Output: `analysis_outputs/prewindow_live_plus_rocket_g16_seed1015000_summary.csv`
- Buckets: Noor Alakazam, live Lucario, Aib4 Lucario, Great Tusk, Kei Marnie, Dragapult, Rocket Mewtwo/Spidops.
- Equal selected buckets:
  - `alakcapedura`: `0.8973`
  - `gtmid`: `0.8839`
  - `gtdeck`: `0.8482`
- This single seed favored `alakcapedura`, mainly from better Noor Alakazam and Lucario-live rows.

Live-family aggregate across recent comparable runs:

- Sources:
  - `analysis_outputs/top3_live_focus_g10_seed1004000_summary.csv`
  - `analysis_outputs/submit_wait_live_g20_seed1011000_summary.csv`
  - `analysis_outputs/prewindow_live_plus_rocket_g16_seed1015000_summary.csv`
  - `analysis_outputs/cinderbench_live_focus_g10_seed1009000_summary.csv`
- Aggregate over live buckets shared by these runs:
  - `gtmid`: `616 / 704` (`0.8750`)
  - `alakcapedura`: `605 / 704` (`0.8594`)
  - `gtdeck`: `594 / 704` (`0.8438`)
- Notable aggregate splits:
  - Noor Alakazam: `alakcapedura 0.7857`, `gtdeck 0.7232`, `gtmid 0.6696`
  - Great Tusk: `gtmid 0.8304`, `alakcapedura 0.7232`, `gtdeck 0.5446`
  - Dragapult: `gtmid 0.9911`, `gtdeck 0.9821`, `alakcapedura 0.9286`
  - Kei Marnie: `gtdeck 0.9375`, `gtmid 0.9196`, `alakcapedura 0.8393`

Updated submit-window decision:

- The aggregate live evidence again favors `gtmidguard`.
- `alakcapedura` is still the best answer if a new recovered loss or final pre-submit check points specifically to Noor Alakazam / broad top20 proxy pressure.
- If no new replay appears and current score remains below the 900+ band near the submit window, submit:
  - `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`

Final quick score check in this pass:

- `2026-07-09 18:13 JST`: latest public score recovered to `896.2`.
- This is above the rank-500 score landmark from the saved leaderboard snapshot and close to the 900+ observation band.
- If this recovery continues toward the submit window, do not automatically replace; recheck score and replay availability immediately before any submit.

## 2026-07-09 18:18 JST Candidate Aggregation

Kaggle status:

- Current local time checked: `2026-07-09 18:14 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score stayed at `896.2`.
- Still before the next submit window; no submit was made.

Replay mining:

- Scanned `85017001-85021000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_85017001_85021000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`

Candidate aggregate:

- Sources used:
  - `analysis_outputs/submit_wait_live_g20_seed1011000_summary.csv`
  - `analysis_outputs/prewindow_live_plus_rocket_g16_seed1015000_summary.csv`
  - `analysis_outputs/with_rocket_broad_g4_seed1014000_summary.csv`
  - `analysis_outputs/benchguard_broad_g6_seed1008000_summary.csv`
  - `analysis_outputs/post_aib4_broad_g4_seed1003000_summary.csv`
  - `analysis_outputs/broad_family_g6_seed999000_summary.csv`
- Live-focus aggregate:
  - `gtmid`: `616 / 700` (`0.8800`)
  - `alakcapedura`: `612 / 700` (`0.8743`)
  - `gtdeck`: `581 / 700` (`0.8300`)
- `public_sample_2026_07_03_top20` aggregate:
  - `alakcapedura`: `408 / 472` (`0.8654`)
  - `gtmid`: `379 / 472` (`0.8047`)
  - `gtdeck`: `360 / 472` (`0.7646`)
- Equal-public aggregate:
  - `alakcapedura`: `1090 / 1260` (`0.8659`)
  - `gtmid`: `1086 / 1260` (`0.8627`)
  - `gtdeck`: `1039 / 1260` (`0.8246`)

Updated submit-window decision:

- If current `gtdeck` is still around or above `900` at the submit window, keep observing rather than spending a submit.
- If current is below `900` with no new replay evidence, `gtmidguard` is the default replacement because it is best in the live-focus aggregate and has prior real Kaggle evidence at `918.5`.
- If fresh evidence points away from the live-focus mix and toward broad public-top/top20 proxy pressure, use `alakcapedura`.

## 2026-07-09 18:22 JST Score Drop Recheck

Kaggle status:

- Current local time checked: `2026-07-09 18:21 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score dropped from `896.2` to `884.9`, then to `878.0`.
- Still before the next submit window; no submit was made.

Replay mining:

- Scanned `85021001-85025000`.
  - Output: `analysis_outputs/kaggle_live/scan_54485645_85021001_85025000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`

Package recheck:

- Rechecked `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
  - SHA256: `C8D3D6F810A9293C961A1595DE0DB15D49C28741B1D325AEF8896156DFAFABC7`
  - Archive still contains only the expected top-level submission files plus `cg/`.
  - Smoke output: `analysis_outputs/gtmid_archive_recheck_g2_seed1016000_summary.csv`
  - No action errors.

Updated submit-window decision:

- With current score back under `900`, the default next submit-window action is now to submit:
  - `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`
- Reconsider only if current `gtdeck` recovers clearly above `900` before the window or if a newly recovered replay points specifically toward the `alakcapedura`-favored Noor/top20-proxy environment.

## 2026-07-09 18:44 JST Ogerpon Variants And Old947 Recheck

Kaggle status:

- Current local time checked: `2026-07-09 18:44 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score was `866.7`.
- The next 6-hour submit window remains `2026-07-09 22:06 JST`; no submit was made.

Replay mining:

- Scanned `85025001-85040000`.
  - Output: `analysis_outputs/kaggle_live/submission_54485645_probe/scan_85025001_85040000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`

New local opponent coverage:

- Added public Ogerpon variant buckets from `data/public_decks/discussion_716207`:
  - `ogerpon_clefairy`
  - `ogerpon_hydrapple`
  - `ogerpon_meganium`
  - `ogerpon_meganium_arboliva`
  - `ogerpon_meganium_hydrapple`
  - `ogerpon_multi_mask`
  - `ogerpon_sinistcha`
- Added `discussion_ogerpon_public_variants_2026_07_09` to `tools/run_meta_suite.py` and `tools/aggregate_meta_summaries.py`.
- Shared local policy: `meta_agents/ogerpon_public_variant_policy.py`.

Ogerpon-public variant result:

- Output: `analysis_outputs/ogerpon_public_variants_g8_seed1018000_summary.csv`
- `discussion_ogerpon_public_variants_2026_07_09`:
  - `gtmid`: `0.9722`
  - `alakcapedura`: `0.9583`
  - `gtdeck`: `0.9375`

Old high-score candidate recheck:

- Rechecked the prior real-score `947.0` candidate:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie.tar.gz`
- Mixed live+Ogerpon short result:
  - Output: `analysis_outputs/pre_submit_live_oger_old947_g6_seed1019000_summary.csv`
  - `old947`: `0.9643`
  - `gtdeck`: `0.9226`
  - `gtmid`: `0.9107`
  - `alakcapedura`: `0.8929`
- Public top20 short result:
  - Output: `analysis_outputs/pre_submit_public_top20_old947_g6_seed1020000_summary.csv`
  - `gtmid`: `0.8377`
  - `alakcapedura`: `0.8048`
  - `old947`: `0.7873`
  - `gtdeck`: `0.7829`

Great Tusk safety patch:

- Created `old947gtguard` by copying `old947` and adding the `gtmidguard` Great Tusk deck-preservation rules.
- Package:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_gtguard.tar.gz`
  - SHA256: `614D9FF65F1C5A618FB296E40238C7C1F9871413E4E9ADEE9ECED49D4F18E4FC`
- Focused Great Tusk result:
  - Output: `analysis_outputs/old947_gtguard_great_tusk_g20_seed1021000_summary.csv`
  - `old947`: `0.325`
  - `old947gtguard`: `0.750`
  - `gtmid`: `0.800`
- Package smoke:
  - Output: `analysis_outputs/old947gtguard_archivecheck_g2_seed1022000_summary.csv`
  - No action errors.

Updated submit-window decision:

- If no new replay appears and the current score stays below `900`, prefer replacing `gtdeck` at the window rather than waiting.
- Current first-choice replacement depends on what we want to hedge:
  - `gtmidguard`: safest if public-top20 / Great Tusk / broad meta pressure is expected; prior real Kaggle score `918.5`.
  - `old947`: best recent local live+Ogerpon score and prior real Kaggle score `947.0`, but still Great Tusk-weak.
  - `old947gtguard`: Great Tusk-safe old947 variant, but its short live+Ogerpon result was lower than original `old947`.
- Recheck score and any recoverable replay immediately before `2026-07-09 22:06 JST`.

## 2026-07-09 18:56 JST Decision Recheck

Kaggle status:

- Current local time checked: `2026-07-09 18:56 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score was `854.2`.
- Still before the next 6-hour submit window (`2026-07-09 22:06 JST`); no submit was made.

Replay mining:

- Scanned `85040001-85050000`.
  - Output: `analysis_outputs/kaggle_live/submission_54485645_probe/scan_85040001_85050000.csv`
  - Existing episodes: `0`
  - Hits: `0`
  - Downloaded replays: `0`

Additional decision tests:

- Live-core focused test:
  - Output: `analysis_outputs/decision_live_core_g20_seed1023000_summary.csv`
  - Buckets: `lucario_live`, `lucario_aib4_live`, `alakazam_noor_live`, `marnie_kei_live`, `rocket_mewtwo_spidops`
  - Results:
    - `old947gtguard`: `186 / 200` (`0.9300`)
    - `old947`: `180 / 200` (`0.9000`)
    - `gtmid`: `178 / 200` (`0.8900`)
    - `alakcapedura`: `177 / 200` (`0.8850`)
    - `gtdeck`: `175 / 200` (`0.8750`)
- Public-top20 proxy test:
  - Output: `analysis_outputs/decision_public_top20_g12_seed1024000_summary.csv`
  - Results:
    - `alakcapedura`: `203 / 240` (`0.8458`)
    - `gtdeck`: `197 / 240` (`0.8208`)
    - `old947gtguard`: `196 / 240` (`0.8167`)
    - `old947`: `192 / 240` (`0.8000`)
    - `gtmid`: `189 / 240` (`0.7875`)
- Ogerpon public-variant test:
  - Output: `analysis_outputs/decision_ogerpon_variants_g10_seed1025000_summary.csv`
  - Results:
    - `gtmid`: `173 / 180` (`0.9611`)
    - `old947gtguard`: `171 / 180` (`0.9500`)
    - `old947`: `170 / 180` (`0.9444`)
    - `alakcapedura`: `169 / 180` (`0.9389`)
    - `gtdeck`: `169 / 180` (`0.9389`)

Weighted decision view:

- If weighting the most recent real-loss buckets heavily (`live_core=0.5`, `public_top20=0.3`, `ogerpon_variants=0.2`):
  - `old947gtguard`: `0.9000`
  - `alakcapedura`: `0.8840`
  - `old947`: `0.8789`
  - `gtmid`: `0.8735`
  - `gtdeck`: `0.8715`
- If weighting live and public-top20 equally (`live_core=0.4`, `public_top20=0.4`, `ogerpon_variants=0.2`):
  - `old947gtguard`: `0.8887`
  - `alakcapedura`: `0.8801`
  - `old947`: `0.8689`
  - `gtdeck`: `0.8661`
  - `gtmid`: `0.8632`

Current submit-window candidate:

- First choice if score remains below `900` and no new replay contradicts the current loss picture:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_gtguard.tar.gz`
- Package check:
  - Contains expected top-level `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
  - No `__pycache__` entries.
  - SHA256: `614D9FF65F1C5A618FB296E40238C7C1F9871413E4E9ADEE9ECED49D4F18E4FC`
- `alakcapedura` remains the fallback if the pre-submit signal shifts toward broad public-top20 rather than live-core losses.

## 2026-07-09 19:03 JST Rank Check And Bench-Rescue Rejection

Kaggle status:

- Current local time checked: `2026-07-09 19:03 JST`.
- Latest `submission_archaludon_gt_deckguard.tar.gz` public score was `854.7`.
- Still before the next 6-hour submit window (`2026-07-09 22:06 JST`); no submit was made.

Current leaderboard snapshot:

- Downloaded current leaderboard to `analysis_outputs/leaderboard_current_2026_07_09_1858`.
- Leaderboard CSV: `analysis_outputs/leaderboard_current_2026_07_09_1858/pokemon-tcg-ai-battle-publicleaderboard-2026-07-09T09_58_19.csv`
- `rurumi` row:
  - Rank: `694`
  - Score: `854.2`
  - Last submission: `2026-07-09 07:06:35 UTC`
- Current score lines from this snapshot:
  - Rank 100: `986.2`
  - Rank 200: `940.9`
  - Rank 300: `918.5`
  - Rank 400: `901.2`
  - Rank 500: `884.8`
  - Rank 700: `853.6`
  - Rank 1000: `815.2`

Loss-shape read for `old947gtguard` on public-top20:

- Source: `analysis_outputs/decision_public_top20_g12_seed1024000_games.csv`
- Candidate losses: `44`
- Main terminal classes:
  - `no_active`: `34`
  - `deckout_or_zero_deck`: `6`
  - `other`: `4`
- Main loss buckets:
  - `ogerpon`: `10`
  - `archaludon`: `9`
  - `great_tusk`: `9`
  - `marnie`: `5`
  - `alakazam`: `5`

Rejected bench-rescue experiments:

- Created `ubbench`:
  - Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_gtguard_ubbench`
  - Change: allow Ultra Ball from Cinderace-only, empty-bench states to search for Duraludon.
  - Public-top20 check: `analysis_outputs/ubbench_public_top20_g10_seed1026000_summary.csv`
  - Result:
    - `old947gtguard`: `0.8776`
    - `ubbench`: `0.8289`
  - Rejected because it improved some Archaludon/Alakazam/Lucario games but sharply worsened Ogerpon and Great Tusk.
- Created `ubtarget`:
  - Directory: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_gtguard_ubtarget`
  - Change: same Ultra Ball rescue, but only when matchup detection is `archaludon`, `alakazam`, or `lucario`.
  - Public-top20 check: `analysis_outputs/ubtarget_public_top20_g10_seed1027000_summary.csv`
  - Result:
    - `old947gtguard`: `0.8289`
    - `ubtarget`: `0.7553`
  - Rejected because even the targeted version increased `no_active` losses and reduced overall score.

Updated submit-window decision:

- Keep `old947gtguard` as the first-choice submit candidate.
- Do not submit `ubbench` or `ubtarget`.
- If the final pre-submit check still shows current score below `900` and no new replay contradicts the live-core loss picture, submit:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_gtguard.tar.gz`

## 2026-07-09 19:20 JST Ogerenergy840 GTGuard Submission

Kaggle status before submitting:

- Latest active `submission_archaludon_gt_deckguard.tar.gz` had fallen to the low/mid `840` range:
  - CLI check before submit: `839.9`.
  - CLI refresh after the new upload showed the old active score at `844.1`.
- This was far below the previous same-family live results (`918.5`, `920.4`, and historical `947.0` for the chandlowdecklillie family), so the active submission was treated as stalled rather than merely noisy.

Candidate promoted:

- Directory:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_ogerenergy840_gtguard`
- Archive:
  - `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_ogerenergy840_gtguard.tar.gz`
- SHA256:
  - `F5C11B73AB16C721112A9D47CF425C74F280FD22CB1D85F98DFC24791D1EAFD8`
- Main change:
  - Start from the `ogerenergy840` branch, then add the Great Tusk deck-preservation guard from `old947gtguard`.
  - Keep the broad Ogerpon/Marnie/Alakazam local gains from `ogerenergy840`, while avoiding the large Great Tusk deckout regression.

Local evidence:

- Weak loss-bucket check:
  - Output: `analysis_outputs/ogerenergy840gt_weak_buckets_g12_seed1029000_summary.csv`
  - `ogerenergy840gt`: `92 / 120` (`0.7667`)
  - `old947gtguard`: `85 / 120` (`0.7083`)
  - `ogerenergy840`: `82 / 120` (`0.6833`)
- Live-core check:
  - Output: `analysis_outputs/ogerenergy840gt_live_core_g12_seed1030000_summary.csv`
  - `ogerenergy840gt`: `109 / 120` (`0.9083`)
  - `old947gtguard`: `109 / 120` (`0.9083`)
  - `alakcapedura`: `107 / 120` (`0.8917`)
  - Known tradeoff: `old947gtguard` was better into `alakazam_noor_live`; watch for this in live losses.
- Ogerpon public variants:
  - Output: `analysis_outputs/ogerenergy840gt_oger_variants_g8_seed1031000_summary.csv`
  - `old947gtguard`: `0.9375`
  - `ogerenergy840gt`: `0.9306`
  - `alakcapedura`: `0.9375`
  - This is a small downside, not enough to override the public-top20 and weak-bucket gains.
- Public-top20 focused check:
  - Output: `analysis_outputs/ogerenergy840gt_public_top20_g20_seed1033000_summary.csv`
  - `ogerenergy840gt`: `0.8434` on `public_sample_2026_07_03_top20`, `0.8700` on equal public buckets.
  - `old947gtguard`: `0.8086` on `public_sample_2026_07_03_top20`, `0.8400` on equal public buckets.
  - Bucket gains were mainly `archaludon`, `ogerpon`, `great_tusk`, `hop`, and `starmie`; `alakazam` favored the old guard.

Package check:

- Archive root contains exactly the expected submission files and API directory:
  - `main.py`
  - `deck.csv`
  - `requirements.txt`
  - `cg/`
- No `__pycache__` entries were present in the archive listing.
- Extracted archive smoke test:
  - Output: `analysis_outputs/ogerenergy840gt_archivecheck_g2_seed1034000_summary.csv`
  - `errors`: `0`

Kaggle submit:

- Command uploaded the archive successfully, but the first CLI call crashed while printing the response because Windows `cp932` could not encode a returned character.
- UTF-8 refresh confirmed that the upload did succeed.
- New submission:
  - Kaggle submission id: `54490333`
  - File: `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie_ogerenergy840_gtguard.tar.gz`
  - Submit time: `2026-07-09 10:19:38.347 UTC` / `2026-07-09 19:19:38 JST`
  - Initial status: `SubmissionStatus.PENDING`
  - Follow-up status check: `SubmissionStatus.COMPLETE`
  - Initial public score after validation: `600.0`

Next monitoring rule:

- Do not churn immediately from the first noisy games.
- Treat validation error, remaining near the initial rating after validation, or sustained loss/stagnation evidence as reasons to prepare and submit the next candidate.
- If this submission loses mainly to Alakazam/Noor-style opponents, compare against `old947gtguard` and the older `gtmidguard` family before making another narrow patch.
- Immediate replay scan:
  - Output: `analysis_outputs/kaggle_live/submission_54490333_probe/scan_85050001_85056000.csv`
  - Checked: `6000`
  - Existing episodes: `0`
  - Hits for submission `54490333`: `0`
  - Downloaded replays: `0`
  - Interpretation: the scanned range was likely still before the new games; retry after the score starts moving.

## 2026-07-09 19:38 JST Early Live Check For 54490333

Latest-submission score movement:

- CLI first showed the latest submission still at `600.0`.
- A later CLI refresh briefly reported `541.7`, but the browser Game History panel had fresher state:
  - Latest submission score: `805.4`
  - Visible score range: `542 - 805`
  - Active older fallback `submission_archaludon_gt_deckguard.tar.gz`: `830.0`
- Current leaderboard snapshot:
  - Downloaded to `analysis_outputs/leaderboard_current_2026_07_09_1938`.
  - CSV: `analysis_outputs/leaderboard_current_2026_07_09_1938/pokemon-tcg-ai-battle-publicleaderboard-2026-07-09T10_37_26.csv`
  - `rurumi`: rank `883`, score `830.0`, last submission `2026-07-09 10:19:38 UTC`.
  - The leaderboard was still using the older active `830.0` submission as the best active score, not the new `805.4` candidate.

Visible Game History for submission `54490333`:

- `episodeId=85003297`: `rurumi` beat `URAD`.
  - `URAD`: rank `412`, score `899.2` in the current snapshot.
- `episodeId=85002819`: `rurumi` beat `シャカパチロボ`.
  - `シャカパチロボ`: rank `2770`, score `620.8`.
- `episodeId=85002327`: `KL` beat `rurumi`.
  - `KL`: rank `1182`, score `793.3`.
- `episodeId=85001761`: `rurumi` beat `rurumi` self/same-team style game.

Replay availability:

- Browser detail pane currently says `Unable to load episode` for the visible IDs.
- Exact-ID internal API probe for the loss:
  - Output: `analysis_outputs/kaggle_live/submission_54490333_probe/scan_85002327.csv`
  - `checked=1`, `existing=0`, `hits=0`, `downloaded_replays=0`
- A broader scan from `84983000` to `84990000` was stopped because it was too slow and the browser had already exposed exact IDs.
- Retry direct exact-ID replay download later for:
  - `85002327` first, then `85003297`, `85002819`, `85001761`.

Alakazam contingency check:

- Output: `analysis_outputs/alakazam_risk_after_ogerenergy840gt_g16_seed1035000_summary.csv`
- Equal Alakazam-family aggregate:
  - `gtmidguard`: `0.8047`
  - `alakcapedura`: `0.7891`
  - `ogerenergy840gt`: `0.7734`
  - `old947gtguard`: `0.7656`
- Specific read:
  - `ogerenergy840gt` is weak against `alakazam_ketchum_alt` (`0.5938`).
  - `gtmidguard` is the best fallback if the new live losses are Ketchum/Alakazam-like.
  - `alakcapedura` is best for `alakazam_noor_live` / `alakazam_tubotu_live`, but poor into `alakazam_ketchum_alt`.

Decision:

- Do not submit another archive now.
- Reason: latest candidate recovered from the early dip to `805.4` with visible `3-1` record, including a win over a higher-rated `URAD`; the only visible loss is to lower-rated `KL`, and the replay is not yet downloadable.
- Next check should retry exact episode downloads and watch whether the latest score climbs past the older active fallback (`830.0`) or remains below it after more games.

## 2026-07-09 19:40 JST Follow-Up For 54490333

Score state:

- CLI score for latest `54490333`: `868.9`.
- Older active fallback `submission_archaludon_gt_deckguard.tar.gz`: `830.0`.
- The new submission is now above the older active fallback, so this is not a stop-loss state.

Refreshed visible Game History:

- Browser panel score: `869`, range `542 - 869`.
- Visible games now show `4-1`:
  - `episodeId=85003780`: `rurumi` beat `Skyyy93`.
    - `Skyyy93`: rank `1470`, score `763.5` in the current snapshot.
  - `episodeId=85003297`: `rurumi` beat `URAD`.
    - `URAD`: rank `412`, score `899.2`.
  - `episodeId=85002819`: `rurumi` beat `シャカパチロボ`.
  - `episodeId=85002327`: `KL` beat `rurumi`.
    - `KL`: rank `1182`, score `793.3`.

Replay availability:

- Exact-ID retry scans for `85002327`, `85003297`, `85002819`, and `85001761` still returned `existing=0`, `hits=0`, `downloaded_replays=0`.
- New exact-ID scan for `85003780` also returned `existing=0`.
- Direct URL check for `https://www.kaggle.com/competitions/episodes/85002327/replay.json` returned `404`.
- Interpretation: visible Game History is ahead of the episode/replay API. Retry later rather than broad-scanning.

Decision:

- Do not submit now.
- Continue observing `54490333`; it has climbed above the older active fallback and has a visible winning early record.
- Next useful action is exact-ID replay retry for `85002327` once Kaggle exposes the replay.

## 2026-07-09 20:00 JST Stop-Loss Probe For 54490333

Score state:

- Latest submission `54490333` fell back below the older active fallback.
  - `19:52 JST`: latest `772.2`, older active fallback `835.8`.
  - `19:57 JST`: latest `742.5`, older active fallback `829.9`.
- Browser refresh for `submissionId=54490333&episodeId=85004260` showed the same downward direction:
  - Visible score `743`.
  - Visible range `542 - 869`.
- This is no longer the earlier "recovering 4-1" state. The latest candidate is below the active fallback and trending down.

Recovered replays:

- `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85001761_replay.json`
- `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85002327_replay.json`
- `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85002819_replay.json`
- `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85003297_replay.json`
- `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85004260_replay.json`

Loss review:

- `85002327`: loss vs `KL`, opponent submission `54452620`, target updated score `541.778`.
  - Metadata: `analysis_outputs/kaggle_live/submission_54490333_probe/scan_85002327_retry3.csv`.
  - Summary: `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85002327_summary.csv`.
  - Opponent is Alakazam-line (`741/742/743`) with a large hand and repeated `743:1072` attacks.
  - Our side reached turn 12 with active `Archaludon ex` and only one benched `Duraludon`; opponent already had one prize left while we still had four.
  - Decision replay inspection showed the current agent and `gtmidguard` make the same tail decisions in this recovered state, so this single replay does not prove a direct `gtmidguard` tactical fix.
- `85004260`: loss vs `Naoshin`, Mega Lucario ex style.
  - Metadata: `analysis_outputs/kaggle_live/submission_54490333_probe/scan_85004260.csv`.
  - Summary: `analysis_outputs/kaggle_live/submission_54490333_probe/episode_85004260_summary.csv`.
  - The suspicious branch was a turn-8 Boss on a one-prize target while active Mega Lucario ex survived, then opponent won the prize race.

Rejected narrow patch:

- Candidate: `tmp_compare_submissions/oger840gt_lucariobossguard`.
- Local Lucario-only result:
  - `analysis_outputs/lucariobossguard_lucario_g24_seed1036000_summary.csv`
  - Improved equal Lucario aggregate from `0.9306` to `0.9583`.
- Broad check:
  - `analysis_outputs/lucariobossguard_public_top20_g12_seed1037000_summary.csv`
  - Regressed public top20 from `0.8827` to `0.8268`.
  - Regressed equal public buckets from `0.8708` to `0.8500`.
- Decision: do not submit this patch. It overfits the Naoshin/Mega Lucario loss and hurts the broader meta proxy.

Fallback candidate check:

- Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
- SHA256: `C8D3D6F810A9293C961A1595DE0DB15D49C28741B1D325AEF8896156DFAFABC7`.
- Archive contents verified: `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
- `py -3.11 -m py_compile` passed for its `main.py`.
- Historical Kaggle evidence: same archive previously scored `918.5`.
- Quick visible-loss bucket comparison:
  - Output: `analysis_outputs/current_vs_gtmid_visibleloss_g8_seed1040000_summary.csv`.
  - Equal selected buckets:
    - current `ogerenergy840gt`: `0.7875`.
    - `gtmidguard`: `0.8375`.
  - `gtmidguard` improves `alakazam_ketchum_alt` (`0.625` -> `0.6875`) and `alakazam_tubotu_live` (`0.625` -> `1.0`), while giving up some Lucario rate.

Decision:

- Do not submit immediately at `19:57 JST`, because a new submission would replace the older active fallback in the latest-two active submissions and temporarily leave the team with `54490333` plus a new uncalibrated `600` submission.
- Use `20:20 JST` as the next stop-loss checkpoint, roughly one hour after the latest submission.
- If `54490333` is still clearly below the active fallback or still trending down, submit the verified historical fallback `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
- If it recovers above the active fallback, keep observing and prioritize newly recovered loss replays over another narrow patch.

## 2026-07-09 20:07 JST Restore gtmidguard Submission

Stop-loss trigger:

- At `20:03 JST`, latest `54490333` had fallen again:
  - `54490333`: `713.7`.
  - Older active fallback `submission_archaludon_gt_deckguard.tar.gz`: `829.9`.
- The full short trend for `54490333` was `868.9 -> 772.2 -> 742.5 -> 713.7`.
- This was judged a clear decline rather than normal early noise, and enough replay evidence had been recovered to avoid blind churn.

Submission:

- Archive submitted:
  - `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`
- Kaggle message:
  - `Restore gtmidguard after ogerenergy840 live decline`
- Kaggle submission id:
  - `54491496`
- Submitted:
  - `2026-07-09 11:03:45 UTC` / `2026-07-09 20:03:45 JST`
- Validation result:
  - `20:07 JST`: `SubmissionStatus.COMPLETE`, public score `600.0`.

Immediate interpretation:

- This intentionally replaces the latest-two active-submission set with the restored `gtmidguard` plus the declining `ogerenergy840gt`.
- The temporary score may look worse while `54491496` is uncalibrated.
- Do not submit again immediately unless `54491496` errors or shows an obvious catastrophic failure.
- Next checks:
  - `20:25-20:35 JST`: smoke check that score is moving and game history starts populating.
  - `21:00-21:30 JST`: meaningful early stop-loss check if it remains far below the declining predecessor.
  - `3-6 hours`: normal confidence window if results are mixed.

## 2026-07-09 20:09 JST Smoke Check For 54491496

Status:

- CLI at `20:08 JST`:
  - `54491496`: `SubmissionStatus.COMPLETE`, public score `600.0`.
  - Prior `54490333`: `740.0`.
  - Older `54485645`: `829.9` in the historical list, but no longer the active leaderboard fallback after the latest-two replacement.
- Browser navigation to `submissionId=54491496` exposed `episodeId=85007056`.

Validation replay:

- Exact-ID scan:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85007056.csv`
  - `checked=1`, `existing=1`, `hits=1`, `downloaded_replays=1`.
- Replay:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85007056_replay.json`
- Summary:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85007056_summary.csv`
- Metadata:
  - Type: `EPISODE_TYPE_VALIDATION`.
  - Team names: `rurumi` vs `rurumi`.
  - Reward: target side `1`, validation opponent side `-1`.
  - Updated score remains `600`.

Interpretation:

- This is only the Kaggle validation self-match, not a public ladder game.
- No public matchup evidence for `54491496` is available yet.
- Do not resubmit from this result.
- Next useful action is to wait for public games to populate, then recover exact episode IDs from browser Game History or narrow scans around the visible IDs.

## 2026-07-09 20:10 JST Public Game Probe For 54491496

Status:

- CLI at `20:10 JST`:
  - `54491496`: `SubmissionStatus.COMPLETE`, public score `600.0`.
  - Prior `54490333`: `740.0`.

Near-ID scan:

- Output: `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85007057_85007800.csv`.
- Range: `85007057-85007800`.
- Result:
  - `checked=744`
  - `existing=15`
  - `hits=0`
  - `downloaded_replays=0`

Interpretation:

- No public ladder game for `54491496` is visible in the immediate post-validation episode range.
- This remains normal formation wait, not a failure signal.
- Do not submit again before public games appear.
- Next check should start from browser Game History if it shows visible game rows; otherwise scan a later narrow range after `20:25 JST`.

## 2026-07-09 20:17 JST Early Score Rise For 54491496

Score state:

- CLI at `20:12 JST`:
  - `54491496`: `715.0`.
  - Prior `54490333`: `763.8`.
- CLI at `20:17 JST`:
  - `54491496`: `810.6`.
  - Prior `54490333`: `783.1`.
- This is a positive early signal: the restored `gtmidguard` candidate is now above the declined predecessor in the current submissions list.

Public replay search:

- Browser refresh still showed stale detail:
  - Visible panel score `715`.
  - Visible range `600 - 715`.
  - Only `Unable to load episode: 85007056` was visible, which is the validation self-match already recovered.
- Near-ID scans:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85007057_85007800.csv`
    - `checked=744`, `existing=15`, `hits=0`.
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85007801_85009000.csv`
    - `checked=1200`, `existing=12`, `hits=0`.
- A broader `85007801-85011500` scan was started but stopped because it was too slow for this smoke check.

Decision:

- Do not submit another archive.
- `54491496` is moving in the desired direction and has not exposed a public loss replay yet.
- Next check should use CLI score first. If the score remains high or rising, keep observing.
- If browser Game History eventually exposes public episode IDs, scan exact IDs first rather than broad ranges.

## 2026-07-09 20:20 JST First Public Episode ID For 54491496

Score state:

- CLI at `20:18 JST`:
  - `54491496`: `810.6`.
  - Prior `54490333`: `783.1`.
- Browser refresh at `20:19 JST` then showed a fresher-looking Game History panel:
  - Visible score `732`.
  - Visible range `600 - 811`.
- CLI at `20:19 JST` confirmed:
  - `54491496`: `731.7`.
  - Prior `54490333`: `762.8`.

Visible episode:

- Navigating to `submissionId=54491496` without an explicit episode caused the browser to select:
  - `episodeId=85008594`.
- Browser text:
  - `Unable to load episode: 85008594`.

Exact-ID scan:

- Output: `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85008594.csv`.
- Result:
  - `checked=1`
  - `existing=0`
  - `hits=0`
  - `downloaded_replays=0`

Interpretation:

- The score likely reflects at least one public ladder game, but the replay API has not exposed `85008594` yet.
- This resembles the earlier `54490333` behavior where browser Game History exposed IDs before `GetEpisode` / `replay.json` became available.
- Do not submit again based on this early volatility. The submission is still under 20 minutes old and has already shown it can climb above the predecessor.
- Next action: retry exact-ID scan for `85008594` first. If it becomes downloadable, analyze the loss/win before considering any new patch.

## 2026-07-09 20:25 JST Rebound Check For 54491496

Score state:

- CLI at `20:21 JST`:
  - `54491496`: `731.7`.
  - Prior `54490333`: `762.8`.
- Browser Game History at `20:22 JST` showed:
  - Visible score `811`.
  - Visible range `600 - 811`.
  - In progress: `rurumi` vs `Kazato Takahashi`.
  - Loss: `datawizardd` beat `rurumi`.
  - Win: `rurumi` beat `にゅーおじ`.
  - Win: `rurumi` beat `Djenk Ivanov`.
- Row-click episode IDs:
  - `datawizardd` loss row: `episodeId=85008594`.
  - `にゅーおじ` win row: `episodeId=85008101`.
- Exact scans:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85008594_retry1.csv`: `existing=0`, `hits=0`.
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85008594_retry2.csv`: `existing=0`, `hits=0`.
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85008101.csv`: `existing=0`, `hits=0`.
- CLI at `20:25 JST`:
  - `54491496`: `820.5`.
  - Prior `54490333`: `778.9`.
  - `gtmidguard_cynthline`: `818.8`.

Decision:

- Do not submit another archive.
- The restored `gtmidguard` candidate rebounded and is now above both the declining predecessor and the prior `cynthline` score in the submissions list.
- Public episode IDs are visible but still not available through `GetEpisode`.
- Next check should retry exact IDs `85008594` and `85008101` before using broader scans.
- If score stays above the predecessor and no replay is downloadable, keep waiting; this candidate has not reached a stop-loss state.

## 2026-07-09 20:35 JST Replay Recovery And LineUB Test For 54491496

Current score:

- CLI at `20:28 JST`:
  - `54491496`: `827.7`.
  - Prior `54490333`: `724.6`.
- CLI at `20:35 JST`:
  - `54491496`: `900.8`.
  - Prior `54490333`: `740.2`.

Recovered public replays:

- Loss vs `datawizardd`:
  - Episode: `85008594`.
  - Scan: `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85008594_retry3.csv`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85008594_replay.json`.
  - Summary: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85008594_summary.csv`.
  - Decision scores: `analysis_outputs/kaggle_live/submission_54491496_probe/decision_85008594_gtmidguard_tail30.json`.
- Win vs `にゅーおじ`:
  - Episode: `85008101`.
  - Scan: `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85008101_retry1.csv`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85008101_replay.json`.
  - Summary: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85008101_summary.csv`.

`85008594` loss read:

- Opponent was a high-rated Alakazam-line player (`datawizardd`, visible leaderboard score `925.2` in the episode metadata).
- Their active `743` used attack `1072` repeatedly.
- Our board collapsed by turn 7:
  - step `40`: active `666`, bench `169 x1`.
  - step `41`: opponent `743:1072` KOs the active `666`.
  - step `54`: after recovery, board is active `169`, bench `169 x1`.
  - step `67`: opponent KOs the active `169`, leaving only one benched `169`.
  - step `79`: opponent KOs the final active `169`; no bench remains.
- Decision inspection shows the concrete thin-board sequence:
  - step `15`: Explorer originally took `Metal Energy` + `Full Metal Lab`; `Ultra Ball` was available but scored as discard fodder.
  - step `48-52`: after the first KO, the agent used `Pokegear` before `Ultra Ball`, then discarded both draw supporters to take a single backup `Duraludon`.
  - This creates a two-Duraludon recovery line, but no third body or evolved tank before Alakazam reaches enough hand size.

Candidate test:

- Created comparison candidate:
  - `tmp_compare_submissions/gtmidguard_alak_cinder_lineub`.
- Change:
  - Versus visible Alakazam, if active is `Cinderace` and only one `Duraludon` / `Archaludon ex` line is in play, Explorer prioritizes `Ultra Ball`.
  - In the same state, `Ultra Ball` is played immediately to build the second line.
- Replay decision check:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/decision_85008594_alak_cinder_lineub_tail80.json`.
  - On the actual loss observation at step `15`, `Ultra Ball` becomes the top Explorer pick at score `26000`.

Local comparison:

- Output:
  - `analysis_outputs/lineub_live_focus_g10_seed1041000_summary.csv`.
  - `analysis_outputs/lineub_live_focus_g10_seed1041000_games.csv`.
- Equal live-focus buckets:
  - `gtmid`: `0.8583`.
  - `lineub`: `0.8833`.
- But target bucket got worse:
  - `gtmid` vs `alakazam_noor_live`: `0.75`.
  - `lineub` vs `alakazam_noor_live`: `0.65`.
- `lineub` improved Great Tusk, Lucario, and Dragapult in this seed, but it did not solve the Alakazam loss pattern it was designed for.

Decision:

- Do not submit `lineub`.
- Do not submit anything at this checkpoint: live score has climbed to `900.8`, so `54491496` is not stalled or failing.
- Keep observing `54491496` for several hours unless it drops sharply or multiple recovered public losses show the same fixable pattern.
- If Alakazam remains the dominant live loss bucket, the next safer direction is not empty-board Ultra Ball rescue; it should focus on preserving draw after the first KO or evolving/tanking earlier without sacrificing the Alakazam bucket in local tests.

## 2026-07-09 20:45 JST New Visible Games For 54491496

Score state:

- CLI at `20:39 JST` briefly showed `842.4`.
- Browser Game History after refresh showed visible score around `890`, range `600 - 901`.
- CLI recheck then showed:
  - `54491496`: `890.0`.
  - Prior `54490333`: `774.7`.
- Episode metadata explains the swing:
  - `85010062`: win vs `PALTCG`, `878.2 -> 900.8`.
  - `85010064`: win vs `kuma_jp`, `827.8 -> 878.2`.
  - `85010538`: loss vs `ひげだるま(inovie株式会社)`, `900.8 -> 842.5`.
  - `85011029`: win vs `Soulemane ISSIFOU`, `842.5 -> 890.1`.

Recovered files:

- `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85010062_85010064.csv`.
- `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85010538.csv`.
- `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85011029.csv`.
- Replays:
  - `episode_85010062_replay.json`
  - `episode_85010064_replay.json`
  - `episode_85010538_replay.json`
  - `episode_85011029_replay.json`
- Summaries:
  - `episode_85010062_summary.csv`
  - `episode_85010064_summary.csv`
  - `episode_85010538_summary.csv`
  - `episode_85011029_summary.csv`
- Decision inspection:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/decision_85010538_gtmidguard_tail70.json`.

`85010538` loss read:

- Opponent was another Alakazam-line deck (`741/742/743`) with Dunsparce/Dudunsparce-style draw support.
- This was not the same no-bench collapse as `85008594`.
- Our board reached a strong state:
  - Around step `149`: active `Archaludon ex (190)` at `300 HP`, bench `Duraludon`.
  - Step `150`: evolved the bench `Duraludon` into a second `Archaludon ex`.
  - Step `155-156`: active `Archaludon ex` used `Metal Defender (253)` to KO opponent active `743`.
  - Our prizes went to `1`, but opponent also had `1` prize remaining.
- Opponent then rebuilt:
  - promoted/evolved into another `743`;
  - used `Night Stretcher (1097)`, benched `741`, drew up to roughly `18-22` hand;
  - attacked with `743:1072` and KO'd the `300 HP` active `Archaludon ex`.
- We still had a benched `Archaludon ex`, but the opponent took the final prize, so the game ended.

Decision read:

- The agent held multiple `Boss's Orders (1182)`, but the active `743` was already KO-able.
- Bossing a benched one-prize support target would not finish the game; it would still leave opponent at one prize with an Alakazam line available.
- The useful countermeasure is therefore not a simple Boss priority patch.
- The missing tool is either:
  - consistently finding `Hero's Cape` / a 400 HP active before the final Alakazam swing, or
  - adding/using hand disruption, which is a deck-level change rather than a tiny rule patch in the current list.

Decision:

- Do not submit now.
- `54491496` is still recovering after losses and has visible wins against higher-rated or comparable opponents.
- Two recovered losses are both Alakazam, so Alakazam remains the next research bucket, but immediate narrow patches are not yet proven:
  - `lineub` worsened the local Alakazam bucket.
  - Existing `alakcapedura` helps some broad/top20 and Noor-style rows, but it is known to lose Great Tusk / some live-focus coverage and its Cape rule targets active Duraludon more than this late Archaludon-ex prize-race loss.
- Continue observing. Submit only if the score drifts below the older active fallback or if another tested candidate improves Alakazam without giving back Great Tusk/Marnie coverage.

## 2026-07-09 20:46 JST Rank Check And Iono Win For 54491496

Score and rank:

- CLI at `20:44 JST`:
  - `54491496`: `920.8`.
  - Prior `54490333`: `787.9`.
- Downloaded current public leaderboard:
  - Directory: `analysis_outputs/leaderboard_current_2026_07_09_2045`.
  - CSV: `analysis_outputs/leaderboard_current_2026_07_09_2045/pokemon-tcg-ai-battle-publicleaderboard-2026-07-09T11_46_02.csv`.
- Leaderboard position:
  - `rurumi`: rank `292 / 4630`, score `920.8`.
  - Rank `250` score: `929.5`.
  - Rank `500` score: `884.0`.
  - Rank `100` score: `983.4`.
- Interpretation:
  - The current submission is above the rank-500 band and close to rank-250, but not near the top-100 / likely gold-pressure band.

New visible Game History row:

- Browser-visible panel at refresh:
  - Score `921`, range `600 - 921`.
  - New top row: `rurumi` beat `ghostiee11`.
- Row click:
  - `episodeId=85011510`.
- Scan/replay:
  - `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85011510.csv`.
  - `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85011510_replay.json`.
  - `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85011510_summary.csv`.
- Metadata:
  - Opponent: `ghostiee11`.
  - Opponent score in metadata: `856.8`.
  - Reward: win.
  - Score change: `890.0785 -> 920.8659`.
- Archetype read:
  - Opponent board included `269/270`, matching the Iono/Bellibolt line.
  - Our active `Archaludon ex` with support bench took the final KO with `190:253`.

Alakazam loss follow-up:

- Additional inspection of `85010538` showed `Hero's Cape (1159)` was not merely missed:
  - Step `60`: `p0:1159->190`, active `Archaludon ex` reached `400 HP`.
  - Later the active was down to `300 HP` before the final Alakazam swing.
- Therefore the immediate fix is not simply "prioritize Hero's Cape earlier".
- The harder Alakazam issue is surviving or ending the game after the opponent rebuilds a late `743` with a very large hand.

Decision:

- No submit.
- `54491496` is still climbing and now sits at rank `292`.
- Keep current candidate active for longer sampling.
- Next useful patch research remains Alakazam-specific, but should avoid repeating already rejected Ultra Ball/Cape-priority changes. Candidate directions to test later:
  - lower opponent hand / deck rebuild through deck-level tech if a suitable card exists;
  - prize-race logic around when to KO active `743` versus forcing a different final prize map;
  - late healing/Ice Cream availability checks only if replay evidence shows a missed healing route.

## 2026-07-09 21:00 JST Comfey/Yveltal Control Loss From 54491496

Live state:

- CLI at `20:52 JST`: latest submission `54491496` showed `927.5`.
- Downloaded leaderboard snapshot:
  - Directory: `analysis_outputs/leaderboard_current_2026_07_09_2055`.
  - CSV: `analysis_outputs/leaderboard_current_2026_07_09_2055/pokemon-tcg-ai-battle-publicleaderboard-2026-07-09T11_52_39.csv`.
- Rank state from the snapshot:
  - `rurumi`: rank `259 / 4631`, score `927.4`.
  - Rank `250`: `929.5`.
  - Rank `100`: `985.5`.
  - Rank `50`: `1022.0`.

New recovered games:

- `85012186`: win vs `halup`, Dragapult.
  - Scan: `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85012186.csv`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85012186_replay.json`.
  - Deck extraction: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85012186_decks`.
  - Score change: `920.8659 -> 948.0602`.
  - Opponent deck was Dragapult ex (`119/120/121`) with Comfey/Budew/Meowth ex support.
  - Endgame: our `Archaludon ex` survived a `Dragapult ex` KO cycle, then Bossed `Fezandipiti ex (140)` and took the final 2 prizes with `Metal Defender`.
- `85012465`: loss vs `koga_poke`, opponent score about `1031`.
  - Scan: `analysis_outputs/kaggle_live/submission_54491496_probe/scan_85012465.csv`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85012465_replay.json`.
  - Trace: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85012465_trace.csv`.
  - Deck extraction: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85012465_decks`.
  - Score change: `948.0602 -> 927.4560`.

`85012465` loss read:

- Opponent deck was a Comfey/Yveltal control shell:
  - `Comfey (164) x4`, `Yveltal (689) x2`, `Shaymin (343) x1`.
  - `Xerosic's Machinations (1197) x4`, `Acerola's Mischief (1228) x4`, `Colress's Tenacity (1194) x4`.
  - `Neutralization Zone (1247) x1`, `Handheld Fan (1161) x2`, disruption/search shell.
- This was not a KO race loss. Our final visible board still had:
  - active `Archaludon ex (190)` at `400 HP`;
  - benched `Archaludon ex` and `Duraludon`;
  - opponent had not taken prizes normally.
- Actual loss pattern:
  - Opponent repeatedly used Comfey `Flower Shower (215)`, which makes both players draw 3.
  - We used normal draw/search sequencing into that matchup:
    - Turn 6: `Explorer's Guidance` at deck `26`, then `Poke Pad` at deck `20/19`.
    - Turn 8: `Pokegear` / `Explorer` lines while the opponent continued forcing draws.
  - By turn 10, our deck was at `3`.
  - Final opponent action was another Comfey `Flower Shower`; this exhausted our remaining deck and ended the game despite our HP/prize position.

Patch candidate:

- Created comparison candidate:
  - Directory: `tmp_compare_submissions/gtmidguard_comfeycontrol_deckguard`.
  - Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_comfeycontrol_deckguard.tar.gz`.
  - SHA256: `42316CA394C9A09080974945D86596363063DB6CBF2F1456B3473BAF0B3F2C29`.
- Changes:
  - Detect `Comfey + Yveltal/Shaymin` as `comfey_control`, separate from normal Chandelure.
  - Against `comfey_control`, skip `Explorer` when deck is at or below `40` and hand is already at least `8`.
  - Against `comfey_control`, skip `Poke Pad` at low/mid deck with a large hand.
  - Preserve `Pokegear -> Lillie` as a recovery route.
  - Give `Lillie's Determination` high priority in `comfey_control` when it can refill a low/mid deck from a large hand.
- Decision inspection:
  - Base at step `38` chose `Explorer`.
  - Patched candidate at step `38` attaches/attacks instead, preserving deck.
  - Base at step `50` chose `Pokegear` and then still allowed later draw lines.
  - Patched candidate preserves `Pokegear -> Lillie`, then prioritizes `Lillie` at step `52/53` as deck refill.

Local validation:

- Existing live-focus comparison, two seeds, each `games=12`, buckets:
  - `chandelure`, `chandelure_dick`, `marnie_kei_live`, `alakazam_noor_live`, `great_tusk`, `lucario_live`, `lucario_aib4_live`, `dragapult`.
  - Outputs:
    - `analysis_outputs/comfeyguard_v2_live_focus_g12_seed1051000_summary.csv`.
    - `analysis_outputs/comfeyguard_v2_live_focus_g12_seed1052000_summary.csv`.
- Two-seed aggregate over those buckets:
  - `gtmid`: `343 / 384`, win rate `0.8932`.
  - `comfeyguard`: `343 / 384`, win rate `0.8932`.
  - Interpretation: broad live-focus performance is neutral, not a clear all-purpose upgrade.
- Added a local simplified koga-style opponent:
  - `meta_agents/comfey_yveltal_koga_live_85012465_simple`.
  - Registered as `comfey_yveltal_koga_live` in `tools/run_meta_suite.py`.
  - Deck comes from `85012465` extraction.
- Smoke comparison vs this new local opponent:
  - Output: `analysis_outputs/comfeyguard_v2_koga_live_g8_seed1053000_summary.csv`.
  - `gtmid`: `9 / 16`, win rate `0.5625`.
  - `comfeyguard`: `11 / 16`, win rate `0.6875`.

Decision:

- Do not submit immediately.
- Current live submission remains rank `259`, just below rank `250`, and is not collapsing.
- `comfeyguard` is now a ready fallback if live history shows additional Comfey/Yveltal/Flower Shower deck-out losses.
- Because broad validation is neutral rather than clearly positive, only submit this archive if:
  - another recovered live loss matches the `85012465` Flower Shower deck-out pattern, or
  - the active score drifts well below the prior stable band and no stronger candidate is available.

### 2026-07-09 21:32 JST - `54491496` Decline And `lucariobev` Submission

Live state:

- Active submission before replacement:
  - ID: `54491496`.
  - Archive: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
  - Submitted: `2026-07-09 11:03:45 UTC`.
  - Score path observed: peak around `951.95`, then `927.58`, `906.21`, `888.46`, and CLI at `2026-07-09 21:31 JST` showed `861.1`.
- This crossed below the prior stable band and below the current rank-500 neighborhood, so a replacement became justified.

Recovered recent games:

- `85013429`: loss vs `Gyoukou`, score `951.9510 -> 927.5835`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85013429_replay.json`.
  - Deck extraction: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85013429_decks`.
  - Opponent deck: Mega Lucario (`678`) with Riolu/Solrock/Lunatone/Makuhita/Hariyama, `Premium Power Pro`, `Fighting Gong`, `Gravity Mountain`, 13 Fighting Energy.
  - Loss pattern: our active `Duraludon` was at low HP with a benched `Duraludon`; the agent evolved the low-HP active into `Archaludon ex`, then Lucario removed it and the remaining board collapsed.
- `85013912`: loss vs `ezreal77`, score `927.5835 -> 906.2075`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85013912_replay.json`.
  - Deck extraction: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85013912_decks`.
  - Opponent deck: Archaludon mirror with `13` Metal Energy, `4` Night Stretcher, `4` Full Metal Lab, `2` Xerosic's Machinations, `1` Crushing Hammer, no Relicanth.
  - Loss pattern: mirror resource race; opponent maintained thicker Archaludon board.
- `85014881`: loss vs `OzanM.`, score `904.4603 -> 888.4633`.
  - Replay: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85014881_replay.json`.
  - Deck extraction: `analysis_outputs/kaggle_live/submission_54491496_probe/episode_85014881_decks`.
  - Opponent deck: Archaludon mirror with Relicanth, `4` Jumbo Ice Cream, `4` Full Metal Lab, `3` Boss, `1` Judge.
  - Loss pattern: mirror resource race; opponent kept multiple Archaludon ex plus Relicanth access.
- `85014339`: visible UI loss vs `Murat Kolic`, but still unavailable from Episode API as of this checkpoint.
- `85014394`: visible UI win vs `K.Hirotsune`, replay became available.

New local opponent buckets:

- Added `archaludon_ezreal77_live`:
  - Directory: `meta_agents/archaludon_ezreal77_live_85013912_simple`.
  - Deck from `85013912`.
- Added `archaludon_ozanm_live`:
  - Directory: `meta_agents/archaludon_ozanm_live_85014881_simple`.
  - Deck from `85014881`.
- Kept `lucario_live` for Gyoukou-style Lucario. Its deck matches the recovered `85013429` list closely.

Rejected candidates:

- `gtmidguard_comfeycontrol_deckguard`:
  - Good targeted idea for `85012465`, but not supported by the newer loss cluster.
  - New comparison on `archaludon_ezreal77`, `archaludon`, and `comfey_yveltal_koga_live` showed no broad improvement.
- `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard_benchguard`:
  - Raised all bench-empty Ultra Ball plays to `26000`.
  - Helped some Lucario-like positions, but direct replay inspection of `85013912` showed harmful mirror changes:
    - Turn 2: chose Ultra Ball over Poke Pad / playing existing Duraludon.
    - Turn 12: chose Ultra Ball over Lillie/attack sequencing.
  - Local live-target comparison worsened `archaludon_ezreal77_live` heavily.
- `tmp_compare_submissions/gtmidguard_lucario_benchub`:
  - Limited the bench-empty Ultra Ball raise to Lucario.
  - Direct replay inspection showed no action changes in `85013429`, `85013912`, or `85014881`, so it did not address the actual losses.

Submitted candidate:

- Directory: `tmp_compare_submissions/gtmidguard_lucario_benchevolve`.
- Archive: `submission_archaludon_gtmidguard_lucariobev.tar.gz`.
- SHA256: `E86AC1FA7173395EFE280FBE1C554CD5222FAC1BF9261BCEA0ECC880225A2D44`.
- Kaggle submit time: `2026-07-09 12:32:05 UTC`, status initially `PENDING`.
- Change:
  - In Lucario matchup only, if active `Duraludon` has `HP <= 70` and a benched `Duraludon` exists, lower active `Archaludon ex` evolution priority so the bench Duraludon evolves instead.
  - This targets the exact `85013429` failure without changing mirror decisions.
- Direct replay inspection:
  - `85013429`: action changed at step `37`, turn `4`.
    - Base: evolve active low-HP `Duraludon`.
    - Candidate: evolve benched `Duraludon`.
  - `85013912`: no action differences.
  - `85014881`: no action differences.
- Local validation:
  - Output: `analysis_outputs/lucariobev_live_losses_targets_g20_seed1080000_summary.csv`.
  - Buckets: `archaludon_ezreal77_live`, `archaludon_ozanm_live`, `lucario_live`, `archaludon`, `alakazam_noor_live`, `comfey_yveltal_koga_live`.
  - Aggregate over these live-loss-focused buckets:
    - `gtmid`: `123 / 240`, win rate `0.5125`.
    - `lucariobev`: `141 / 240`, win rate `0.5875`.
  - Main gains:
    - `lucario_live`: `35 / 40 -> 39 / 40`.
    - `comfey_yveltal_koga_live`: `14 / 40 -> 23 / 40`.
    - `archaludon_ozanm_live`: `13 / 40 -> 17 / 40`.
  - Small regression:
    - `archaludon_ezreal77_live`: `13 / 40 -> 12 / 40`.

Decision:

- Submitted `lucariobev` because:
  - active score had fallen to `861.1`;
  - it fixed one confirmed live losing decision exactly;
  - mirror decisions in the two recovered mirror losses were unchanged by direct replay inspection;
  - live-loss-focused local aggregate improved materially.
- Next monitoring:
  - Wait for validation / early public score.
  - If it errors, fall back to the previous complete submission only if needed.
  - If it starts around `600`, wait for non-validation games before judging.
  - If it recovers above `900`, let it run for several hours before further changes.
### 2026-07-09 22:05 JST - `54493893` Early Live Episodes And Alakazam Non-Ex Test

Latest active submission:
- ID: `54493893`.
- Archive: `submission_archaludon_gtmidguard_lucariobev.tar.gz`.
- Description: `Archaludon lucariobev: preserve low-HP active Duraludon vs Lucario, evolve bench`.
- API score check after early games: `894.9`.

Useful tooling:
- Added `tools/list_kaggle_submission_episodes.py`.
- It calls `/api/i/competitions.EpisodeService/ListEpisodes` with `{"submissionId": ...}` and can save matching replay JSONs.
- This avoids broad episode-id scanning when the target submission id is known.

Fetched live episodes:
- Output: `analysis_outputs/kaggle_live/submission_54493893_probe/toolcheck_54493893_episodes.csv`.
- Replays saved under `analysis_outputs/kaggle_live/submission_54493893_probe`.
- Sequence:
  - Validation `85017605`: score initialized to `600`.
  - Four wins to `930.09`: `85018154`, `85018624`, `85019105`, `85019589`.
  - Two Alakazam losses:
    - `85020067` vs `Choruru`, score `930.09 -> 855.65`.
    - `85020158` vs `PyJa`, score `855.65 -> 812.91`.
  - Two recovery wins:
    - `85020555` vs `Iwa Iwa`, score `812.91 -> 867.12`.
    - `85021045` vs `Ryosei Kojima`, score `867.12 -> 894.97`.

Alakazam loss pattern:
- Both losses used the same `alakazam_noor_live`-style 60-card list:
  - `741/742/743` Alakazam line `4/4/4`.
  - `305/66` Dunsparce/Dudunsparce `4/3`.
  - `1079` Rare Candy x4, `1081` Enhanced Hammer x4, `1264` Battle Cage x1.
- `85020158` exposed a local rule issue: at turn 12, active `Duraludon` had `840 Archaludon` available, but the rule returned `hold non-ex Archaludon outside Ogerpon`, choosing a weak `223` attack instead.

Candidate tested:
- Directory: `tmp_compare_submissions/gtmidguard_lucariobev_alaknonex`.
- First version allowed Alakazam non-ex Archaludon broadly.
  - Rejected: changed early turns too much and worsened exact `alakazam_noor_live` from `47/64` to `41/64`.
- Narrow version only allows active Duraludon to evolve into non-ex Archaludon after turn 10.
  - Direct replay delta:
    - `85020067`: no action changes.
    - `85020158`: one action change, turn 12 weak attack -> active non-ex evolution.
  - Local focus output: `analysis_outputs/alaknonex_activeonly_alakazam_focus_g32_seed1091000_summary.csv`.
  - Result:
    - `alakazam_noor_live`: `43/64 -> 43/64` (neutral).
    - `alakazam`: `57/64 -> 54/64` (worse).
    - `alakazam_tubotu_live`: `58/64 -> 51/64` (worse).
- Decision: do not submit `alaknonex`.

Current decision:
- Do not replace `54493893` yet.
- Reason: after the two Alakazam losses it recovered from `812.9` to `894.9`, and the tested narrow Alakazam patch is not locally better.
- Continue monitoring. Submit only if the live score falls below the stable fallback range again and a candidate improves the exact observed loss bucket without giving back other Alakazam/local buckets.
### 2026-07-09 22:28 JST - `54493893` Decline, Crustle Deck-Guard Patch, And `54495224` Submit

Live monitoring:
- `54493893` continued downward after the earlier recovery:
  - `85021537` loss vs `Koba Empire` Archaludon mirror: `894.97 -> 864.04`.
  - `85022019` loss vs Kangaskhan/Crustle deckout: `864.04 -> 837.24`.
  - `85022507` win vs `hatata`: `837.24 -> 864.23`.
  - `85022989` loss vs `Poké Bowl` Archaludon mirror: `864.23 -> 836.77`.
  - `85023525` loss vs `dungeon-master` Mega Lucario: `836.77 -> 811.85`.
- At submit time the API later showed `54493893` had fallen further to `785.2`.

Observed loss patterns:
- `85021537` was a mirror race loss. The agent used Boss to KO a 1-prize bench `Duraludon` while the opponent's active `Archaludon ex` remained live. A `mirrorfront` patch changed that exact decision, but it was noisy by seat and by mirror variant, so it was not promoted.
- `85022019` was a deckout loss against a Kangaskhan/Crustle list, not the existing public Great Tusk list:
  - Opponent deck used `756 Mega Kangaskhan ex` x4, `344/345` Dwebble/Crustle `3/3`, `1219` Team Rocket's Petrel x4, and no `58` Great Tusk.
  - Existing deck-preservation rules were gated on visible `GREAT_TUSK_LINE`, so this deck bypassed the guard.
  - The submitted agent reached `p1_deck=0` while opponent still had about 25 cards.

Rejected probes:
- `tmp_compare_submissions/gtmidguard_lucariobev_mirrorfront`
  - Fixed the exact Boss decision in `85021537`.
  - Local target output: `analysis_outputs/mirrorfront_target_g32_seed1093000_summary.csv`.
  - Mixed result: improved live mirror buckets in one batch, but Koba deck override was seat-dependent and public Archaludon worsened.
- `tmp_compare_submissions/gtmidguard_lucariobev_crustlenonex`
  - Allowed `840 Archaludon` non-ex evolution vs Crustle only when the target `Duraludon` had 3 energy.
  - Rejected because it worsened existing `great_tusk` from `54/64` to `48/64` and did not improve the Kangaskhan/Crustle override overall (`46/64 -> 45/64`).

Promoted patch:
- Directory: `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard`.
- Change:
  - For all `crustle` matchups, not only visible `GREAT_TUSK_LINE`, preserve deck in low-deck/stable-attacker states:
    - skip `Poké Pad` / `Pokégear 3.0` at low deck or once a stable attacker exists;
    - skip `Explorer's Guidance` once deck is low enough;
    - skip `Ultra Ball` at low deck when the line is already established;
    - prefer `Lillie's Determination` as a refill when deck is low and hand is large.
- Direct replay inspection on `85022019` showed the intended actions:
  - skipped late `Pokégear`, `Poké Pad`, and `Explorer` decisions that were drawing toward deckout.

Local validation:
- Kangaskhan/Crustle deck override:
  - Deck file: `analysis_outputs/kaggle_live/submission_54493893_probe/kang_crustle_85022019_deck.csv`.
  - Old `lucariobev`: `46/64`.
  - `crustledeckguard`: `59/64`.
- Smoke meta:
  - Output: `analysis_outputs/crustledeckguard_smoke_g24_seed1099000_summary.csv`.
  - `great_tusk`: `41/48 -> 42/48`.
  - `alakazam_noor_live`: `34/48 -> 39/48`.
  - `archaludon_ezreal77_live`: `22/48 -> 22/48`.
  - `lucario_aib4_live`: `45/48 -> 44/48`.
  - equal selected buckets: `0.7396 -> 0.7656`.

Submission:
- Archive: `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
- Kaggle submission ID: `54495224`.
- CLI printed a Windows `cp932` UnicodeEncodeError after upload, but API confirmed the submission was created.
- Validation episode `85023820`: complete, score initialized at `600`.
- First public episode `85023904`: win vs `Christian Rangel`, score `600 -> 713.60`.

Next monitoring:
- Let `54495224` collect more public games before replacing again.
- If it loses mirror clusters, revisit a narrower mirror Boss patch, but do not use the current broad `mirrorfront` patch without stronger seat-stable evidence.
- If it loses Lucario donk games like `85023525`, inspect setup/bench policy; that loss had active `Cinderace`, no bench, and a turn-3 Mega Lucario KO.
### 2026-07-09 22:40 JST - `54495224` Early Public Recovery And Mirror Backup Probe

Current live state:
- Latest active submission remains `54495224`.
- API score: `879.8`.
- Public sequence after validation:
  - `85023904`: win vs `Christian Rangel`, score `600 -> 713.60`, opponent classified `marnie_grimmsnarl`.
  - `85024381`: win vs low-rated unknown, score `713.60 -> 739.81`.
  - `85024878`: win vs `dacho`, score `739.81 -> 807.30`, opponent classified `great_tusk_crustle`.
  - `85025368`: win vs `Fahim Faisal`, score `807.30 -> 879.82`, opponent classified `mega_lucario`.
- This is a healthy early run. Do not replace while it is climbing and has no public losses.

Additional probes from old `54493893` losses:
- `85023525` Mega Lucario loss:
  - Opening hand had only `Cinderace` as a Basic.
  - `Hero's Cape` would not save it: `Cinderace` HP `160 + 100 = 260`, while `Mega Brave` is `270`.
  - Treat as low-actionability unless repeated with a different avoidable setup.
- `85022989` Archaludon mirror loss:
  - Opponent deck exactly matched `meta_agents/archaludon_public`.
  - Failure point: at turn 15, bench was empty; Ultra Ball chose `Archaludon ex` / non-ex line pieces over `Cinderace`, leaving no backup.
  - Probe directories:
    - `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_mirrorcinderbackup`
    - `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_mirroronlycinderbackup`
  - The global backup version improved mirrors but caused meaningful Alakazam/Great Tusk regressions.
  - The mirror-only version changed the exact losing choice, but local validation was mixed:
    - public `archaludon`: `26/64 -> 29/64`
    - `archaludon_ezreal77_live`: `29/64 -> 24/64`
    - `archaludon_ozanm_live`: `25/64 -> 24/64`
    - equal selected buckets: `0.6276 -> 0.6250`
  - Decision: do not submit a mirror Cinderace-backup patch unless live `54495224` shows a repeated public-Archaludon-style empty-bench loss cluster.

Current decision:
- Keep `54495224` running.
- Next action should be replay analysis only after a new public loss or a meaningful score stall/drop.
### 2026-07-09 22:41 JST - `54495224` No-New-Episode Check And Historical Fallback Comparison

Live check:
- `54495224` remained at `879.8`.
- Episode count remained `5`, so no new public loss was available to analyze.
- Do not submit a replacement while the latest public sequence is still 4-0 and score is climbing/stable.

Historical fallback comparison:
- Compared current `crustledeckguard` against the older high-score `historical_gtmid` directory:
  - Current: `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard`
  - Historical: `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard`
  - Output: `analysis_outputs/current_vs_historical_gtmid_g24_seed1102000_summary.csv`
- Results:
  - `crustledeckguard` equal selected buckets: `0.7604`.
  - `historical_gtmid` equal selected buckets: `0.7361`.
  - Current improved:
    - `alakazam_noor_live`: `33/48 -> 40/48`.
    - `archaludon_ezreal77_live`: `20/48 -> 25/48`.
    - `archaludon`: `27/48 -> 28/48`.
  - Historical remained better on:
    - `great_tusk`: `45/48` vs current `41/48`.
    - `lucario_aib4_live`: `45/48` vs current `44/48`.
    - `marnie_kei_live`: `42/48` vs current `41/48`.
- Decision:
  - Keep current `54495224`.
  - If future live losses cluster specifically into Great Tusk/Lucario/Marnie, the historical branch is a plausible fallback reference.
  - If losses cluster into Alakazam or live-style Archaludon, current `crustledeckguard` remains the better local baseline.
### 2026-07-09 23:05 JST - `54495224` Reached 1000 And Alakazam Live-Agent Expansion

Live state:
- Latest active submission remains `54495224`
  (`submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`).
- API score reached `1000.2`.
- Episode count reached `10` total:
  - validation: `85023820`
  - public wins: `85023904`, `85024381`, `85024878`, `85025368`,
    `85025863`, `85026861`, `85027357`, `85027847`
  - public loss: `85026363`
- Public sequence is now 8-1 after validation, so do not replace the live submission while it is still climbing.

New loss:
- `85026363` loss vs `Kohenyan`, opponent classified `alakazam_psychic`.
- Opponent list was a live-style Alakazam deck with `Abra/Kadabra/Alakazam`,
  `Dunsparce/Dudunsparce`, `Rare Candy`, `Hilda`, `Dawn`, `Battle Cage`,
  and `Telepath Psychic Energy`.
- End state: opponent `Alakazam` used `Powerful Hand` to KO our `Archaludon ex`.
- Replay decision inspection did not show a simple missed Boss lethal. The agent often held Boss because active KO was available, then lost to continued Alakazam pressure.

New local meta agents:
- Added `meta_agents/alakazam_kohenyan_live_85026363_simple`.
  - Logic copied from `alakazam_tubotu_live_84569848_simple`.
  - Deck copied from live episode `85026363`.
  - Registered as `alakazam_kohenyan_live` in `tools/run_meta_suite.py`.
- Added `meta_agents/alakazam_kisamaki_live_85027847_simple`.
  - Logic copied from `alakazam_tubotu_live_84569848_simple`.
  - Deck copied from live episode `85027847`.
  - Registered as `alakazam_kisamaki_live` in `tools/run_meta_suite.py`.

Alakazam non-ex Archaludon probes:
- Built `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex`.
  - This keeps the current Crustle deck guard and allows midgame non-ex `840 Archaludon`
    evolution vs all Alakazam.
  - Focused Alakazam output:
    `analysis_outputs/alakazam_patch_probe_g24_seed1210000_summary.csv`.
  - Selected-meta output:
    `analysis_outputs/alaknonex_patch_selected_g16_seed1220000_summary.csv`.
  - It improved several selected buckets overall but had visible Starmie and some
    Alakazam-variant noise, so it is not a live replacement while `54495224` is climbing.
- Built `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex_liveonly`.
  - This restricts the non-ex Alakazam plan to `live_alakazam_marker_visible(obs)`.
  - Output: `analysis_outputs/alaknonex_liveonly_g24_seed1240000_summary.csv`.
  - Result was not a clear upgrade over current; keep as a reference only.

Current decision:
- Keep `54495224` live.
- If future public losses cluster into Kohenyan/Noor-style live Alakazam, revisit the
  `alaknonex` probes with larger seeds and include `alakazam_kisamaki_live` to avoid
  overfitting one Alakazam subtype.
- If the score falls after reaching 1000 and the loss cluster is not Alakazam, do not
  submit the Alakazam non-ex branch by default; analyze the new loss cluster first.

Follow-up live check:
- API score later reached `1022.4`.
- Episode count reached `11`.
- New public episode `85028336`: win vs `Myckel Uribe`, score `1000.28 -> 1022.41`.
- Opponent classified as `archaludon_metal`; list used a higher-energy Archaludon shell
  with `1087` x2 and `57` x1 instead of our non-ex `840 Archaludon` package.
- This adds evidence for keeping `54495224` live rather than submitting the Alakazam probe.
### 2026-07-09 23:10 JST - Cynthia/Garchomp Local Proxy Added

Motivation:
- Recent top-replay scouting showed a repeated unknown archetype from `nasuo445` /
  `kuromoka`, later identified as Cynthia/Garchomp/Roserade:
  - `341` Cynthia's Roselia x4
  - `342` Cynthia's Roserade x3
  - `379/380/381` Cynthia's Gible/Gabite/Garchomp ex `4/4/3`
  - `387` Cynthia's Spiritomb x2
  - `1142` Fighting Gong x4
  - `1173` Cynthia's Power Weight x3
  - `20` Rock Fighting Energy x4
- This archetype was present in upper-board replays and should be part of local
  meta coverage even if it is not yet a primary threat to the current submission.

Added local agent:
- Directory: `meta_agents/cynthia_garchomp_nasuo445_live_85023194_simple`.
- Deck copied from `nasuo445` episode `85023194`.
- Registered in `tools/run_meta_suite.py` as `cynthia_garchomp_nasuo_live`.
- Initial logic:
  - prioritize `Gible -> Gabite -> Garchomp ex`;
  - use Gabite's `Champion's Call` to fetch Cynthia Pokemon;
  - value Roserade as a +30 damage support Pokemon;
  - use `Draconic Buster` as the main 260-damage attack;
  - use `Cynthia's Power Weight` on the Garchomp line.

Validation:
- Deck summary: `analysis_outputs/cynthia_garchomp_nasuo_deck_summary.csv`.
- Smoke output:
  - `analysis_outputs/cynthia_garchomp_smoke_g8_seed1250000.csv`
  - `analysis_outputs/cynthia_garchomp_smoke_g8_seed1250000_games.csv`
- The proxy runs without engine errors and reaches `Garchomp ex` in traces.
- Short smoke vs current `crustledeckguard`: current won `16/16`.

Decision:
- Treat this as a local meta-coverage expansion, not as a deck-change candidate.
- If future live logs show Cynthia/Garchomp losses, improve this proxy before tuning
  against it; the first version is functional but likely weaker than the best public
  implementations.
### 2026-07-09 23:15 JST - `54495224` Reached 1045 And Evan Great Tusk Proxy Added

Live state:
- API score reached `1045.5`.
- Episode count reached `13`.
- New public wins:
  - `85029139`: win vs `Evan #2`, score `1022.41 -> 1028.22`.
  - `85028839`: win vs `kemurayama`, score `1028.22 -> 1045.58`.
- Public sequence is now 12-1 after validation. Keep `54495224` live.

New opponent observations:
- `85029139` opponent was a Great Tusk/Crustle list with:
  - `58` Great Tusk x4
  - `344/345` Dwebble/Crustle x4/x4
  - `607` Terrakion x1
  - `1123` Switch x4
  - `1197` Xerosic x4
  - `1204` Lisia's Appeal x2
  - `1194` Colress's Tenacity x2
  - `1247` Neutralization Zone x1
  - `20` Rock Fighting Energy x4 and `11` Mist Energy x4
- `85028839` opponent was another Alakazam variant. Since current beat it and we
  already added multiple Alakazam live proxies, no immediate patch was promoted.

Added local agent:
- Directory: `meta_agents/great_tusk_evan2_live_85029139_simple`.
- Logic copied from `meta_agents/great_tusk_crustle_public`.
- Deck copied from live episode `85029139`.
- Registered in `tools/run_meta_suite.py` as `great_tusk_evan2_live`.

Validation:
- Deck summary: `analysis_outputs/great_tusk_evan2_deck_summary.csv`.
- Smoke output:
  - `analysis_outputs/great_tusk_evan2_smoke_g8_seed1260000.csv`
  - `analysis_outputs/great_tusk_evan2_smoke_g8_seed1260000_games.csv`
- Current `crustledeckguard` beat the new proxy `13/16` in the short smoke.

Decision:
- Do not submit a replacement. The live submission is still climbing.
- Keep `great_tusk_evan2_live` in the local suite for future Great Tusk regression checks.
### 2026-07-09 23:30 JST - `54495224` Alakazam Loss Triage And Capbloo Proxy

Live state:
- API score moved from the 1045 peak to about `1033.4`.
- Public episodes reached `16`, with a public record of `13-3`.
- Losses observed so far:
  - `85026363` vs `Kohenyan`, Alakazam.
  - `85029339` vs `Shota Hirao`, Marnie/Grimmsnarl.
  - `85030556` vs `capbloo`, Alakazam.

New opponent observations:
- Added `ebisu_ya` Alakazam from win `85029849`:
  - `305` Dunsparce x3, `66` Dudunsparce x3, `140` Fezandipiti ex x1,
    `343` Shaymin x1, `1197` Xerosic x2, `1264` Battle Cage x3.
- Added `capbloo` Alakazam from loss `85030556`:
  - `245` Alakazam x1, `1079` Rare Candy x4, `1097` Night Stretcher x2,
    `1184` Lana's Aid x2, `1264` Battle Cage x1.
- The `capbloo` loss ended on turn 5 after our side had `190` active and no
  bench; opponent `743` used `Powerful Hand` for the final KO.

Added local agents:
- `meta_agents/alakazam_ebisu_live_85029849_simple`, registered as
  `alakazam_ebisu_live`.
- `meta_agents/alakazam_capbloo_live_85030556_simple`, registered as
  `alakazam_capbloo_live`.

Candidate probes:
- `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alakbenchguard`
  tried two changes: setup-bench Duraludon and play Lillie when Alakazam plus
  empty bench.
- `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_setupdurabench`
  kept only the setup-bench Duraludon change.
- `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaklillieguard`
  kept only the Lillie empty-bench change.

Validation:
- Alakazam focus:
  - `analysis_outputs/post_54495224_alakbenchguard_focus_g8_seed1330000_summary.csv`
  - `analysis_outputs/post_54495224_alak_guard_ablation_g8_seed1340000_summary.csv`
- Broad setup-Duraludon checks:
  - `analysis_outputs/post_54495224_setupdurabench_broad_g8_seed1350000_summary.csv`
  - `analysis_outputs/post_54495224_setupdurabench_broad_g8_seed1360000_summary.csv`
- Results:
  - The combined `alakbenchguard` patch helped `capbloo` in one focus run but
    dropped `ebisu`/`kisamaki`, so it is not a submit candidate.
  - The Lillie-only guard was worse overall in the Alakazam focus set.
  - The setup-Duraludon-only patch beat current on one broad seed (`0.7500` vs
    `0.7243`) but lost on the next (`0.7868` vs `0.8272`), with mirror and
    Kohenyan volatility.

Decision:
- Do not submit a replacement now. `54495224` is not in a confirmed stall or
  loss streak, and the best new patch is not robust across seeds.
- Keep `setupdurabench` as a watch-list candidate if more live losses show
  empty-bench Alakazam endings.
- Continue gathering live losses before spending a daily submission.
### 2026-07-09 23:35 JST - `54495224` Dropped To 990 After Two More Losses

Live state:
- API score dropped to `990.5`.
- Public episodes reached `18`, with a public record of `13-5`.
- New losses:
  - `85030817` vs `tsukammo`, Alakazam.
  - `85031332` vs `Where is my orbit`, Marnie/Grimmsnarl.

New opponent observations:
- `tsukammo` Alakazam adds a different live variant:
  - `140` Fezandipiti ex x1
  - `1079` Rare Candy x2
  - `1081` Enhanced Hammer x2
  - `1137` Tool Scrapper x1
  - `1156` Lucky Helmet x2
  - `1209` Ruffian x1
  - `1264` Battle Cage x3
- The loss ended with opponent `743` using `Powerful Hand`; our side was forced
  into a weak late-board sequence with `840` active and only a fresh `169` on
  bench.
- `Where is my orbit` used the same Marnie/Grimmsnarl list shape as the Shota
  loss (`648` line, `104` Froslass, `112` Munkidori, `1161` Handheld Fan).

Added local agent:
- `meta_agents/alakazam_tsukammo_live_85030817_simple`, registered as
  `alakazam_tsukammo_live`.

Validation:
- Recent-loss focus:
  - `analysis_outputs/post_54495224_recent_loss_focus_g8_seed1370000_summary.csv`
- Compared:
  - `current`
  - `setupdurabench`
  - `alaknonex`
  - `mirroronlycinder`
  - `marniedurabackup`
- Results over the recent-loss focus set (`marnie_kei_live`, `marnie_shota_live`,
  `alakazam_kohenyan_live`, `alakazam_capbloo_live`, `alakazam_tsukammo_live`):
  - `current`: `0.8625`
  - `setupdurabench`: `0.8625`
  - `alaknonex`: `0.8375`
  - `mirroronlycinder`: `0.8250`
  - `marniedurabackup`: `0.7500`

Decision:
- Do not submit yet despite the score drop. The recent losses are real, but the
  best available replacement only ties current on the recent-loss focus and is
  unstable on broader seeds.
- If the live submission keeps falling below the previous stable 918-920 range,
  prioritize a new candidate that improves Alakazam late-board survival without
  sacrificing Marnie and mirror performance.
### 2026-07-09 23:40 JST - Score Rebounded To 1008; Non-ex Wall Probe Rejected

Live state:
- API score rebounded from `990.5` to `1008.2`.
- Public episodes reached `19`, with a public record of `14-5`.
- New episode:
  - `85031857`: win vs `kami`, score `990.52 -> 1008.24`.
- The win was an early Abra-single KO by Cinderace, so it is not a strong tuning
  signal.

Candidate probe:
- `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_nonexwall2only`
  changes `final_prize_nonex_no_backup()` from opponent prize count `<= 2` to
  exactly `== 2`.
- Motivation: when the opponent has only 1 prize remaining, evolving into
  non-ex `840` no longer prevents losing by KO. In `85030817`, this changed the
  replay scoring at the key turn away from the non-ex wall and toward
  `Archaludon ex`.

Validation:
- Recent-loss focus:
  - `analysis_outputs/post_54495224_nonexwall2_recent_focus_g12_seed1380000_summary.csv`
  - Results over Marnie + recent Alakazam live variants:
    - `current`: `0.7833`
    - `nonexwall2only`: `0.8167`
    - `setupdurabench`: `0.8250`
    - `alaknonex`: `0.8667`
- Broad check:
  - `analysis_outputs/post_54495224_nonexwall2_broad_g8_seed1390000_summary.csv`
  - Results over 18 local meta buckets:
    - `current`: `0.8264`
    - `nonexwall2only`: `0.7604`
    - `alaknonex`: `0.7569`

Decision:
- Do not submit `nonexwall2only` or `alaknonex`.
- Both can improve a recent-loss slice, but broad meta coverage drops too much
  versus current, especially across Alakazam variants, Ogerpon, Starmie, and
  some mirror buckets.
- Keep monitoring `54495224`; the latest live result is a rebound, not a
  confirmed stall.
### 2026-07-09 23:45 JST - `54495224` Reached 1021 And 5.5 Alakazam Proxy Added

Live state:
- API score reached `1021.5`.
- Public episodes reached `20`, with a public record of `15-5`.
- New episode:
  - `85032356`: win vs `5.5`, score `1008.24 -> 1021.59`.
- This is another Alakazam-family opponent, but the current agent won with a
  stable late-board state (`190` active, backup `190/169/666` available).

New local agent:
- `meta_agents/alakazam_55_live_85032356_simple`, registered as
  `alakazam_55_live`.
- It uses the `65` Dunsparce Alakazam line:
  - `65` Dunsparce x4, `66` Dudunsparce x3
  - `741/742/743` Abra/Kadabra/Alakazam `4/4/4`
  - `1079` Rare Candy x4, `1081` Enhanced Hammer x4
  - `1097` Night Stretcher x3
  - no stadium

Validation:
- Smoke:
  - `analysis_outputs/alakazam_55_smoke_g4_seed1400000_summary.csv`
- Current beat the proxy `7/8` in the short smoke.

Decision:
- Do not submit a replacement. The live submission has rebounded from the
  temporary loss cluster, and the current candidate remains the strongest broad
  local option.
### 2026-07-09 23:45 JST - Sota Marnie Loss Added; Replacement Still Rejected

Live state:
- API score was around `1019.9`.
- Public episodes reached `22`, with a public record of `16-6`.
- New episodes:
  - `85033057`: loss vs `Sota Uchiyama`, score `1021.59 -> 1005.33`.
  - `85032856`: win vs `junlee789`, score `1005.33 -> 1019.90`.

New opponent observations:
- `Sota Uchiyama` uses a different Marnie/Grimmsnarl variant:
  - `1079` Rare Candy x4
  - `1097` Night Stretcher x2
  - `1182` Boss's Orders x3
  - `1197` Xerosic x2
  - `1202` Drayton x1
  - `1227` Lillie x3
  - no `1161` Handheld Fan
- `junlee789` is another Marnie/Grimmsnarl variant with `1161` Handheld Fan x2
  and `1206` Larry's Skill x1; current beat it.

Added local agent:
- `meta_agents/marnie_sota_live_85033057_simple`, registered as
  `marnie_sota_live`.
- Initial smoke:
  - `analysis_outputs/marnie_sota_smoke_g4_seed1410000_summary.csv`
  - Current beat the proxy `5/8`.

Validation:
- Marnie focus:
  - `analysis_outputs/post_54495224_marnie_sota_focus_g12_seed1420000_summary.csv`
  - `nonexwall2only` looked strong on the Marnie-only slice (`0.9167` vs current
    `0.8056`).
- New-live broad check:
  - `analysis_outputs/post_54495224_newlive_broad_g6_seed1430000_summary.csv`
  - `nonexwall2only` also won this smaller broad seed (`0.8167` vs current
    `0.7875`).
- Confirm broad check:
  - `analysis_outputs/post_54495224_nonexwall2_confirm_broad_g8_seed1440000_summary.csv`
  - Current won the larger confirmation (`0.8281` vs `nonexwall2only` `0.8125`).

Decision:
- Do not submit `nonexwall2only`.
- It is a plausible watch-list candidate for Marnie-heavy runs, but confirmation
  still shows current ahead overall, and current is not in a confirmed loss
  streak.
### 2026-07-09 23:50 JST - Submission Maturation Timing

Live state:
- API score for `54495224` recovered to `1030.3`.
- Public episodes reached `23`, with a public record of `17-6`.
- Latest new episode:
  - `85033356`: win vs `Big Deck Energy`, score `1019.90 -> 1030.39`.

Timing interpretation:
- The first 30 minutes are too noisy for this competition unless validation
  fails or the score immediately collapses with several clear repeated losses.
- Around 60 minutes is enough to detect obviously bad submissions, but not enough
  to judge a candidate that is fluctuating in the 900-1050 range.
- Around 90-120 minutes is a better first real checkpoint because public
  episodes usually include more meaningful opponent variety.
- Six hours is a good default hold period for a submission that is not clearly
  bad, especially if it reaches or revisits the 1000+ range.

Decision:
- Keep `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
  live.
- Do not resubmit after only one hour unless the run has a repeated-loss pattern
  and a replacement wins broad local confirmation, not only a narrow matchup
  slice.
### 2026-07-10 00:05 JST - Lucario And Marnie Loss Proxies Added

Live state:
- API score for `54495224` was around `1017.5`.
- Public episodes reached `26`, with a public record of `18-8`.
- New public results:
  - `85034364`: win vs `ShumingFang`, score `1016.89 -> 1026.52`.
  - `85034863`: loss vs `gonsaku-yonekichi`, score `1026.52 -> 1017.55`.
  - `85033862`: loss vs `fujiborozoukin`, score `1030.39 -> 1016.89`.

New opponent proxies:
- `meta_agents/mega_lucario_fujiborozoukin_live_85033862_simple`, registered as
  `lucario_fujiborozoukin_live`.
  - Deck: Mega Lucario ex with Lunatone/Solrock, Wally x4, Premium Power Pro x4,
    Dusk Ball x4, Fighting Gong x4, 11 basic Fighting and 4 Rock Fighting.
- `meta_agents/marnie_gonsaku_live_85034863_simple`, registered as
  `marnie_gonsaku_live`.
  - Deck: Marnie's Grimmsnarl ex with Munkidori, Marnie's Morpeko, Dawn x4,
    Basic Dark Energy x15, Energy Recycler x1, and Spikemuth Gym x2.

Replay observations:
- `85033862` lost with no bench after the last `Archaludon ex` was KO'd by
  `Mega Lucario ex`.
- `85034863` also lost with no bench; turn 10 Explorer chose Energy plus
  `Archaludon ex` while leaving a backup `Duraludon` behind.

Validation:
- Lucario fujiborozoukin focus:
  - `analysis_outputs/post_54495224_lucario_fujiborozoukin_focus_g12_seed1450000_summary.csv`
  - `setupdurabench` and `alaknonex` beat current on that narrow slice.
- Recent live broad with the new Lucario:
  - `analysis_outputs/post_54495224_recentlive_plus_lucario_broad_g8_seed1460000_summary.csv`
  - `alaknonex` was best on that seed, but this did not remain stable.
- Full all-meta confirmation:
  - `analysis_outputs/post_54495224_allmeta_confirm_g4_seed1470000_summary.csv`
  - `analysis_outputs/post_54495224_allmeta_confirm_g4_seed1480000_summary.csv`
  - `alaknonex`/`setupdurabench` were ahead of current on both small all-meta
    seeds, but the margin was not decisive.
- Recent live confirmation with a different seed:
  - `analysis_outputs/post_54495224_setup_alaknonex_recent_g8_seed1500000_summary.csv`
  - Current won this seed (`0.9236`) over `setup_alaknonex` (`0.8681`),
    `alaknonex` (`0.8542`), and `setupdurabench` (`0.8056`).
- Marnie-focused check:
  - `analysis_outputs/post_54495224_marnieexplorerbackup_marnie_focus_g12_seed1510000_summary.csv`
  - `setupdurabench` (`0.9167`) and `nonexwall2only` (`0.9063`) beat current
    (`0.8229`), but the targeted Explorer backup candidate underperformed
    (`0.8125`) and is rejected.

Decision:
- Do not submit a replacement yet.
- Current is not collapsing on Kaggle, and local replacement rankings are still
  seed-sensitive.
- Watch-list candidates:
  - `setupdurabench`: best against the new Marnie proxy and often helps no-bench
    losses.
  - `nonexwall2only`: best on some Marnie-heavy slices and older public samples.
  - `alaknonex`: strongest on one recent-live seed and useful into Alakazam.
- Re-submit only if the live run drops into a clear repeated-loss pattern or one
  of these candidates wins another broad confirmation with the newest proxies.
### 2026-07-10 00:20 JST - Replacement Prepared, Submit Blocked By Daily Limit

Live state:
- API score for `54495224` dropped to `996.9`.
- Public episodes reached `32`, with a public record of `20-12`.
- New public sequence:
  - `85036033`: loss vs `capbloo`, Alakazam variant.
  - `85036339`: loss vs `Abhyuday`, Alakazam variant.
  - `85035844`: loss vs `OSELCOUN`, Alakazam variant.
  - `85036527`: win vs `Benarg`.
  - `85036843`: loss vs `me-keh-dev`, Mega Lucario variant.

New opponent proxies:
- `meta_agents/alakazam_capbloo2_live_85036033_simple`, registered as
  `alakazam_capbloo2_live`.
- `meta_agents/alakazam_oselcoun_live_85035844_simple`, registered as
  `alakazam_oselcoun_live`.
- `meta_agents/alakazam_abhyuday_live_85036339_simple`, registered as
  `alakazam_abhyuday_live`.
- `meta_agents/mega_lucario_mekeh_live_85036843_simple`, registered as
  `lucario_mekeh_live`.

Candidate built:
- `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex_explorerbackup`
- Archive:
  - `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_explorerbackup.tar.gz`
- Rule deltas:
  - Keep the existing `alaknonex` midgame non-ex Archaludon rule.
  - Add an Alakazam-specific Explorer rule that keeps backup `Duraludon` when
    the Archaludon line count is thin.

Validation:
- Alakazam focus:
  - `analysis_outputs/post_54495224_alaknonex_explorerbackup_alak_focus_g8_seed1530000_summary.csv`
  - `alaknonex_explorerbackup` was best (`0.8304`).
- Recent live broad:
  - `analysis_outputs/post_54495224_alaknonex_explorerbackup_recent_broad_g8_seed1540000_summary.csv`
  - `nonexwall2only` was best (`0.8894`), but `alaknonex_explorerbackup`
    still beat current (`0.8558` vs `0.8317`).
- All-meta confirmation with new proxies:
  - `analysis_outputs/post_54495224_allmeta_newproxies_g4_seed1550000_summary.csv`
  - `alaknonex_explorerbackup` was best (`0.8639` vs current `0.8417`).
- New three-loss focus:
  - `analysis_outputs/post_54495224_newloss3_focus_g12_seed1560000_summary.csv`
  - `alaknonex_explorerbackup` was best (`0.8750` vs current `0.8333`).

Submit attempt:
- Attempted to submit
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_explorerbackup.tar.gz`.
- Kaggle rejected it with HTTP 400:
  - daily submission allowance used (`5`)
  - next submission allowed in about `8.7` hours from 2026-07-10 00:19 JST

Decision:
- Submit is blocked by the daily Kaggle allowance, not by local validation.
- Keep the archive as the first queued candidate for the next UTC allowance reset.
- Continue monitoring if possible; if the current submission rebounds strongly
  before reset, re-run the latest broad check before spending the next slot.
- Follow-up API check showed the current live score dropping further to `976.3`,
  increasing the priority of submitting the queued replacement after the
  allowance resets.
### 2026-07-10 00:30 JST - Latest Marnie Losses Added; Queue Updated

Live state:
- API score for `54495224` dropped further to `959.3`.
- Public episodes reached `34`, with a public record of `20-14`.
- New losses:
  - `85037325`: loss vs `SRmeg7`, Marnie/Froslass/Munkidori.
  - `85037813`: loss vs `Shardul Gharat`, Marnie/Froslass/Munkidori.

New opponent proxies:
- `meta_agents/marnie_srmeg_live_85037325_simple`, registered as
  `marnie_srmeg_live`.
- `meta_agents/marnie_shardul_live_85037813_simple`, registered as
  `marnie_shardul_live`.

Additional candidate archives:
- `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
- `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
- Both were packaged and `py_compile` passed.

Validation after adding the latest Marnie proxies:
- Marnie focus:
  - `analysis_outputs/post_54495224_new_marnie_focus_g12_seed1570000_summary.csv`
  - `setupdurabench` won this seed, but a later Marnie seed favored `alaknonex`.
- Setup + queued test:
  - `analysis_outputs/post_54495224_setup_queued_marnie_focus_g12_seed1580000_summary.csv`
  - `setup_queued` did not improve reliably and is not a primary candidate.
- Latest live broad:
  - `analysis_outputs/post_54495224_latestlive_broad_g8_seed1590000_summary.csv`
  - `alaknonex` was best (`0.8708`), followed by queued
    `alaknonex_explorerbackup` (`0.8500`), current (`0.8417`).
- All-meta with latest Marnie proxies:
  - `analysis_outputs/post_54495224_allmeta_newmarnie_g4_seed1600000_summary.csv`
  - `nonexwall2only` was best (`0.8650`), then `alaknonex` (`0.8250`),
    queued `alaknonex_explorerbackup` (`0.8175`), current (`0.8075`).

Current queue interpretation:
- The live environment has shifted heavily toward Alakazam and Marnie variants.
- If submitting immediately after reset without another check, prefer
  `alaknonex` because it won the latest-live broad set and recent Marnie focus.
- If the pre-reset all-meta check is prioritized over latest-live weighting,
  `nonexwall2only` is the alternate queue candidate.
- Re-run a quick latest-live broad check after the UTC allowance reset before
  spending the slot, unless the current score continues to collapse.
### 2026-07-10 00:35 JST - Garchomp/Dragapult Added; Submit Still Waiting

Live state:
- API score for `54495224` stayed low, around `959-967`.
- Public episodes reached `36`, with a public record of `20-16`.
- New losses:
  - `85038290`: loss vs `Topdecking is All You Need`, Cynthia/Garchomp ex.
  - `85038765`: loss vs `LumenLiquidity`, Dragapult ex.

New opponent proxies:
- `meta_agents/cynthia_garchomp_topdecking_live_85038290_simple`, registered as
  `cynthia_garchomp_topdecking_live`.
- `meta_agents/dragapult_lumen_live_85038765_simple`, registered as
  `dragapult_lumen_live`.

Validation:
- New Garchomp/Dragapult focus:
  - `analysis_outputs/post_54495224_garchomp_dragapult_focus_g12_seed1610000_summary.csv`
  - `alaknonex` was best (`0.9792`), followed by queued
    `alaknonex_explorerbackup` (`0.9583`).
- Latest-live broad with Garchomp/Dragapult added:
  - `analysis_outputs/post_54495224_latestlive_plus_garchomp_dragapult_g6_seed1620000_summary.csv`
  - queued `alaknonex_explorerbackup` was best (`0.8889`), followed by
    `alaknonex` (`0.8556`), current (`0.8500`), and `nonexwall2only`
    (`0.8500`).

Queue interpretation:
- Current submission is in a confirmed collapse pattern: roughly one win across
  the most recent loss cluster and a public score below 1000.
- The top queue is now split by validation slice:
  - Latest-live broad: `alaknonex_explorerbackup`
  - Recent Marnie/Garchomp/Dragapult focus: often `alaknonex`
  - All-meta: often `nonexwall2only`
- Because the live environment is moving quickly, re-run a short latest-live
  broad check immediately after the daily allowance resets. If it still favors
  queued `alaknonex_explorerbackup`, submit:
  - `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_explorerbackup.tar.gz`
  Otherwise use the latest-live winner among `alaknonex` and `nonexwall2only`.
### 2026-07-10 00:35 JST - One Win Added; Queue Unchanged

Live state:
- API score recovered slightly to `966.8`.
- Public episodes reached `37`, with a public record of `21-16`.
- New episode:
  - `85039262`: win vs `katsudon 421`, score `959.39 -> 966.89`.

Decision:
- No new loss was added after the Garchomp/Dragapult proxy update.
- The current submission is still below 1000 and recently unstable, so the next
  submission slot should still be spent.
- Keep the queue unchanged:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_explorerbackup.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
- Re-run the latest-live broad check immediately after the UTC allowance reset,
  then submit the winner.

### 2026-07-10 00:45 JST - Lossset Recheck; Queue Moves To nonexwall2only

Live state:
- API score for `54495224` is `974.9`.
- Public episodes remain at `38`, with a public record of `22-16`.
- No new public episode was added between
  `monitor_54495224_20260710_003807_episodes.csv` and
  `monitor_54495224_20260710_003859_episodes.csv`.

Replay read:
- Recent losses mostly show a thin-board failure mode: active Archaludon ex,
  Duraludon, or Cinderace is KO'd while the bench is empty or too weak to keep
  the game alive.
- This showed up in the latest Dragapult, Garchomp, Marnie, Lucario, and
  Alakazam losses, so the main suspect is not a single matchup rule but the
  risk of over-committing to one attacker.

Validation:
- Latest lossset, 8 opponents, 8 games per seat:
  - `analysis_outputs/post_54495224_live_lossset_g8_seed1640000_summary.csv`
  - current and `nonexwall2only` tied at `0.9062`; `alaknonex` and queued
    `alaknonex_explorerbackup` were worse.
- Combined `nonexwall2only + alaknonex` test:
  - `analysis_outputs/post_54495224_nonexwall2_alaknonex_live_lossset_g10_seed1650000_summary.csv`
  - current was best (`0.9187`), `nonexwall2only` was second (`0.8750`), and
    the combined candidate fell to `0.8375`; do not submit this hybrid.
- Setup-bench recheck:
  - `analysis_outputs/post_54495224_setup_live_lossset_g10_seed1660000_summary.csv`
  - `nonexwall2only` was best (`0.8625`), current second (`0.8187`), and
    `setupdurabench` worse (`0.7875`); simple setup Duraludon benching is not
    reliable enough to submit.

Queue interpretation:
- The previous queue leader `alaknonex_explorerbackup` is no longer supported
  by the latest lossset validation.
- Since current is already live and still below 1000, the best distinct next
  candidate is now:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_explorerbackup.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
- Submit `nonexwall2only` after the daily allowance reset if the current live
  score remains stalled below silver-stable range or falls again.

### 2026-07-10 00:55 JST - Two More Alakazam Losses; Queue Moves To alaknonex

Live state:
- API score for `54495224` fell to `960.6`.
- Public episodes reached `40`, with a public record of `22-18`.
- New losses:
  - `85040235`: loss vs `Kohenyan`, Alakazam with Battle Cage /
    Neutralization Zone style.
  - `85040738`: loss vs `5.5`, Alakazam with Xerosic, Night Stretcher, and
    4-4-4 Alakazam line.

Proxy status:
- `Kohenyan` matches the already-registered
  `alakazam_kohenyan_live_85026363_simple` closely enough.
- `5.5` matches the already-registered `alakazam_55_live_85032356_simple`.
- No new proxy directory was needed.

Validation:
- Latest lossset plus `Kohenyan` and `5.5`:
  - `analysis_outputs/post_54495224_latest_lossset_plus_kohenyan55_g8_seed1670000_summary.csv`
  - `alaknonex` was best (`0.8562`), current second (`0.8500`),
    `nonexwall2only` fell to `0.8187`.
- Tested a conditional Alakazam non-ex variant that skips the non-ex
  Archaludon evolve when opponent-visible cards include Neutralization Zone
  (`1247`) or Battle Cage (`1264`):
  - Directory:
    `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage`
  - Archive:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
  - Single latest-lossset test:
    `analysis_outputs/post_54495224_alaknonex_nozonecage_latest_lossset_g10_seed1680000_summary.csv`
    put current first (`0.8750`), nozonecage second (`0.8450`),
    `alaknonex` third (`0.8400`).
- Repeated native-shuffle test:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_g4r3_seed1690000_summary.csv`
  - `alaknonex` was best on the selected buckets (`0.8875`),
    `alaknonex_nozonecage` second (`0.8792`), current third (`0.8500`),
    and `nonexwall2only` fourth (`0.8125`).

Queue interpretation:
- The current live submission is now clearly continuing to slide.
- The previous `nonexwall2only` queue leader is no longer supported after
  adding the latest Alakazam losses.
- Current submit queue after the allowance reset:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
- Submit `alaknonex` after reset unless a newer live lossset changes the
  ranking again.

### 2026-07-10 00:58 JST - Shishio Marnie Added; Queue Moves Back To nonexwall2only

Live state:
- API score for `54495224` fell again to `957.8`.
- Public episodes reached `42`, with a public record of `23-19`.
- New episodes:
  - `85041238`: win vs `Testuo&Ryuji`, Iono/Bellibolt style.
  - `85041778`: loss vs `Shishio Makoto`, Marnie/Grimmsnarl ex with
    Cornerstone Mask Ogerpon ex.

New opponent proxy:
- Added `meta_agents/marnie_shishio_live_85041778_simple`.
- Registered it as `marnie_shishio_live` in `tools/run_meta_suite.py`.
- The proxy starts from the existing Marnie rules, uses Shishio's extracted
  60-card deck, and adds Cornerstone Mask Ogerpon ex (`117`) as a cautious
  Archaludon-facing basic.

Validation:
- Latest lossset plus Shishio:
  - `analysis_outputs/post_54495224_latest_lossset_plus_shishio_g8_seed1700000_summary.csv`
  - current was best (`0.8352`), `alaknonex` second (`0.8068`),
    `nonexwall2only` fourth (`0.7670`).
- Tested `alaknonex_marniebackup2`, which adds Marnie detection and Explorer
  backup priority for active Duraludon / Archaludon ex with no line on bench:
  - `analysis_outputs/post_54495224_alaknonex_marniebackup2_latest_lossset_g8_seed1710000_summary.csv`
  - It was worse (`0.8295`) than `alaknonex` (`0.8750`) and current (`0.8466`);
    do not submit this variant.
- Repeated native-shuffle test with Shishio:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_shishio_g4r3_seed1720000_summary.csv`
  - current and `nonexwall2only` tied on the selected buckets (`0.8485`),
    while `alaknonex` fell to `0.8144` and `alaknonex_nozonecage` to `0.8068`.

Queue interpretation:
- The live current submission is still collapsing, so replacing it after reset
  remains reasonable even if local proxies rate current highly.
- After adding the Shishio Marnie loss, the strongest distinct queue candidate
  is again:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
- Do one final quick live fetch after the daily allowance reset before spending
  the slot. If no newer lossset overturns this, submit `nonexwall2only`.

### 2026-07-10 01:05 JST - Ebi Alakazam Added; nonexwall2only Confirmed

Live state:
- API score for `54495224` recovered slightly to `963.3`.
- Public episodes reached `45`, with a public record of `25-20`.
- New episodes:
  - `85042306`: loss vs `Ebi`, Battle Cage Alakazam with Dunsparce (`305`).
  - `85042091`: win vs `Hikaru Umeda`, Archaludon mirror with Xerosic.
  - `85042839`: win vs `fishing_kiyogon`, Archaludon mirror.

New opponent proxy:
- Added `meta_agents/alakazam_ebi_live_85042306_simple`.
- Registered it as `alakazam_ebi_live` in `tools/run_meta_suite.py`.
- It starts from the existing Alakazam proxy but uses Ebi's extracted 60-card
  deck and sets `DUNSPARCE = 305`.

Validation:
- Latest lossset plus Shishio and Ebi:
  - `analysis_outputs/post_54495224_latest_lossset_plus_shishio_ebi_g8_seed1730000_summary.csv`
  - `nonexwall2only` was best (`0.8698`), followed by `alaknonex` (`0.8490`),
    `alaknonex_nozonecage` (`0.8177`), and current (`0.7969`).
- Repeated native-shuffle check:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_shishio_ebi_g3r3_seed1740000_summary.csv`
  - `nonexwall2only` remained best (`0.8148`), followed by current (`0.8009`),
    `alaknonex` (`0.7963`), and `alaknonex_nozonecage` (`0.7546`).

Queue interpretation:
- The current live submission is still below 1000 and is not silver-stable.
- `nonexwall2only` now has both the latest single-run and repeated-run support
  after adding the newest Ebi Alakazam loss.
- Submit queue after reset:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`

### 2026-07-10 01:10 JST - Two Wins Added; Hold Queue

Live state:
- API score for `54495224` recovered to `975.5`.
- Public episodes reached `47`, with a public record of `27-20`.
- New episodes:
  - `85043365`: win vs `ZETADIVISION`, Dragapult-style deck.
  - `85043896`: win vs `Moegi`, low-board / Relicanth start.

Decision:
- No new loss was added after the Ebi proxy update.
- Current is still below 1000, but the newest run is now four wins and one loss
  across the most recent five public games.
- Keep the submit queue unchanged, but do not treat replacement as urgent until
  after the allowance reset and one more live fetch:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`

### 2026-07-10 01:10 JST - No New Public Episodes

Live state:
- API score for `54495224` is unchanged at `975.5`.
- Public episodes remain at `47`, with a public record of `27-20`.
- No new public episode was added between
  `monitor_54495224_20260710_010848_episodes.csv` and
  `monitor_54495224_20260710_011008_episodes.csv`.

Decision:
- No new lossset update is needed.
- Keep the same reset-after-fetch queue:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`

### 2026-07-10 01:11 JST - Still No New Public Episodes

Live state:
- API score for `54495224` is still `975.5`.
- Public episodes remain at `47`, with a public record of `27-20`.
- No new public episode was added between
  `monitor_54495224_20260710_011008_episodes.csv` and
  `monitor_54495224_20260710_011118_episodes.csv`.

Decision:
- No new analysis is needed.
- Keep the queue unchanged and wait for either the allowance reset or a new
  loss pattern:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`

### 2026-07-10 01:12 JST - New Kusui Alakazam Loss

Live state:
- API score for `54495224` fell to `968.9`.
- Public episodes reached `48`, with a public record of `27-21`.
- New episode:
  - `85044440`: loss vs `kusui26`, Alakazam / Dunsparce / Battle Cage
    style. The loss again ended with our Archaludon line effectively becoming a
    single attacker into Alakazam's bench-safe damage plan.

New opponent proxy:
- Added `meta_agents/alakazam_kusui_live_85044440_simple`.
- Registered it as `alakazam_kusui_live` in `tools/run_meta_suite.py`.

Validation:
- Latest lossset plus Kusui:
  - `analysis_outputs/post_54495224_latest_lossset_plus_kusui_g6_seed1750000_summary.csv`
  - `alaknonex_nozonecage` was best (`0.8205`), followed by
    `nonexwall2only` (`0.8077`), `alaknonex` (`0.7949`), and current
    (`0.7885`).
- Repeated native-shuffle check:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_kusui_g3r2_seed1760000_summary.csv`
  - `alaknonex_nozonecage` remained best (`0.8141`), followed by current
    (`0.7885`), `nonexwall2only` (`0.7692`), and `alaknonex` (`0.7692`).

Decision:
- The submit queue moved toward `alaknonex_nozonecage`, but no submit was
  possible before the allowance reset.

### 2026-07-10 01:17 JST - Two More Losses; Early-Cut Signal

Live state:
- API score for `54495224` fell further to `955.1`.
- Public episodes reached `50`, with a public record of `27-23`.
- New episodes:
  - `85044984`: loss vs `victorvv`, Archaludon mirror. Opponent kept a wider
    board while our side ran out first.
  - `85044679`: loss vs `Ant`, Alakazam / Dunsparce / Nighttime Mine variant.
    The final pattern was again single-attacker Archaludon into Alakazam.

New opponent proxies:
- Added `meta_agents/alakazam_ant_live_85044679_simple`.
- Added `meta_agents/archaludon_victorvv_live_85044984_simple`.
- Registered them as `alakazam_ant_live` and `archaludon_victorvv_live` in
  `tools/run_meta_suite.py`.

Validation:
- Latest lossset plus Ant and victorvv:
  - `analysis_outputs/post_54495224_latest_lossset_plus_ant_victor_g5_seed1770000_summary.csv`
  - `alaknonex` led the single-run check (`0.8467`), followed by
    `nonexwall2only` and `alaknonex_nozonecage` (`0.8333`), then current
    (`0.8000`).
- Repeated native-shuffle check:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_ant_victor_g3r2_seed1780000_summary.csv`
  - `alaknonex_nozonecage` led (`0.8278`), followed closely by
    `nonexwall2only` (`0.8222`), then `alaknonex` (`0.7667`) and current
    (`0.7389`).

Queue interpretation:
- The live submission now has enough negative signal to replace after reset:
  score below `1000`, a `27-23` public record, and three fresh losses after the
  temporary recovery.
- Current submit queue:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`

### 2026-07-10 01:23 JST - One Win Added; Mirror Deck Tweaks Rejected

Live state:
- API score for `54495224` recovered slightly to `957.9`.
- Public episodes reached `51`, with a public record of `28-23`.
- New episode:
  - `85045502`: win vs `Inlon Kou`.

Mirror-deck experiment:
- `victorvv` showed a stronger Archaludon mirror list:
  Relicanth x1, Full Metal Lab x4, Jumbo Ice Cream x4, Boss x3, Judge x1,
  Energy x11, and no non-ex Archaludon.
- Created local deck-only variants from `alaknonex_nozonecage`:
  - `..._relicfml4_cutenergyboss`
  - `..._relicfmlice4_nonex1`
  - `..._victorvvdeck`
  - `..._relic_cutenergy`
  - `..._fml4_cutenergy`
  - `..._relicfml4_cutenergygear`
  - `..._relicfml4_cutenergyexplorer`

Validation:
- Heavy mirror-inspired variants:
  - `analysis_outputs/mirror_deck_variants_g6_seed1790000_summary.csv`
  - They improved `archaludon_victorvv_live` locally, but lost too much into
    Alakazam and Marnie buckets. `nozone` remained best overall (`0.7619`).
- Light variants:
  - `analysis_outputs/mirror_light_deck_variants_g6_seed1800000_summary.csv`
  - `nozone` again remained best overall (`0.7857`). The light changes were
    not stable enough to replace the existing candidate.

Decision:
- Reject the mirror deck tweaks for now.
- Keep the submit queue unchanged:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex.tar.gz`

### 2026-07-10 01:39 JST - Pompom Alakazam Added; Benchguard Rejected

Live state:
- API score for `54495224` is `959.9`.
- Public episodes reached `54`, with a public record of `30-24`.
- New episode window:
  - `85046024`: loss vs `pompom555`, Battle Cage Alakazam.
  - `85046938`: win vs `Naoki Osako`.
  - `85047453`: win vs `Marcha Watanabe`.

Loss pattern:
- `pompom555` was another Alakazam game where our board collapsed into a
  single Archaludon ex attacker and lost after the active was KOed.
- The extracted deck is a clean Battle Cage Alakazam list:
  Abra/Kadabra/Alakazam 4-4-4, Dunsparce/Dudunsparce 4-3, Rare Candy 4,
  Enhanced Hammer 4, Buddy-Buddy Poffin 4, Hilda 4, Dawn 4, Night Stretcher 3,
  Boss 3, Telepath Psychic Energy 4, Psychic Energy 3, Battle Cage 1.

New opponent proxy:
- Added `meta_agents/alakazam_pompom_live_85046024_simple`.
- Registered it as `alakazam_pompom_live` in `tools/run_meta_suite.py`.

Benchguard experiment:
- Created two narrow rule variants:
  - `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alakbenchguard`
  - `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_nozone_alakbenchguard`
- The rule only tried to avoid attacking with no bench backup versus Alakazam
  when Duraludon could be benched or recovered via Night Stretcher.

Validation:
- Latest lossset plus Pompom:
  - `analysis_outputs/post_54495224_latest_lossset_plus_pompom_g5_seed1810000_summary.csv`
  - `current` and `nozone` tied (`0.8313`), ahead of `nonexwall2only`
    (`0.7625`) and `alaknonex` (`0.7313`).
- Repeated check before benchguard:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_pompom_g3r2_seed1820000_summary.csv`
  - `current` was slightly ahead (`0.8229`) of `nozone` (`0.8177`), but the
    margin was very small.
- Benchguard single-run:
  - `analysis_outputs/post_54495224_benchguard_pompom_g5_seed1830000_summary.csv`
  - `benchguard` led once (`0.7875`), but had unstable Alakazam bucket results.
- Benchguard repeated check:
  - `analysis_outputs/post_54495224_repeated_benchguard_pompom_g3r2_seed1840000_summary.csv`
  - `nozone` led (`0.8125`), ahead of `nozone_benchguard` (`0.7917`),
    `benchguard` (`0.7760`), and current (`0.7656`).

Decision:
- Reject benchguard for now; it is too seed-sensitive.
- Keep the next submit candidate as:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`.
- Because live score is still below `1000`, submit after allowance reset unless
  the current live submission recovers strongly before reset.

### 2026-07-10 01:40 JST - Toru59er Mirror Loss Added

Live state:
- API score for `54495224` is `953.5`.
- Public episodes reached `55`, with a public record of `30-25`.
- New episode:
  - `85048021`: loss vs `Toru59er`.

Loss pattern:
- `Toru59er` is another Archaludon mirror using the Relicanth / Judge /
  Full Metal Lab x4 shape, matching the same broad list as `victorvv`.
- The game was lost through Boss and attacker exchange in the mirror:
  opponent preserved a wider Archaludon board with Relicanth access, while our
  side was forced into weaker promotions.

New opponent proxy:
- Added `meta_agents/archaludon_toru_live_85048021_simple`.
- Registered it as `archaludon_toru_live` in `tools/run_meta_suite.py`.

Validation:
- Latest lossset plus Toru:
  - `analysis_outputs/post_54495224_latest_lossset_plus_toru_g5_seed1850000_summary.csv`
  - Single-run result had `benchguard` first (`0.7706`), then current
    (`0.7588`), `nozone` (`0.7529`), `nonexwall2only` (`0.7353`), and
    `alaknonex` (`0.7176`), but this conflicted with prior repeated checks.
- Repeated check with Toru:
  - `analysis_outputs/post_54495224_repeated_latest_lossset_toru_g3r2_seed1860000_summary.csv`
  - `nozone` and `alaknonex` tied overall (`0.7843`), followed by
    `nonexwall2only` (`0.7745`), `benchguard` (`0.7549`), and current
    (`0.6961`).
  - `nozone` was much better on the newest real-loss buckets:
    `archaludon_toru_live` (`0.6667`), `archaludon_victorvv_live` (`0.5833`),
    and `alakazam_pompom_live` (`0.9167`).

Decision:
- Keep `benchguard` rejected; repeated checks do not support it.
- Keep next submit candidate as:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`.
- Current score remains below `1000`, but it is still before the UTC-day
  allowance reset. Submit after reset unless live score recovers strongly.

### 2026-07-10 01:46 JST - No New Public Episodes

Live state:
- API score for `54495224` is unchanged at `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added between
  `monitor_54495224_20260710_014025_episodes.csv` and
  `monitor_54495224_20260710_014605_episodes.csv`.

Decision:
- No new proxy or candidate change is needed.
- Keep the reset-after-fetch submit candidate:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`.

### 2026-07-10 01:53 JST - Relicanth Mirror Deck Candidate Promoted

Live state:
- API score for `54495224` is still `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added after `monitor_54495224_20260710_014605_episodes.csv`.

Deck-copy recheck:
- Re-tested the Relicanth / Judge / Full Metal Lab x4 mirror-shape deck now
  that both `victorvv` and `Toru59er` are in the live-loss proxy set.
- Candidates:
  - `nozone`: current reset-after-fetch candidate.
  - `victorvvdeck`: nozone rules with the copied Relicanth/Judge/FML4 deck.
  - `relicfml4`, `relicfmlice4`, and `alaknonex`.

Validation:
- Focused latest-lossset check:
  - `analysis_outputs/post_54495224_deckcopy_toru_g5_seed1870000_summary.csv`
  - `victorvvdeck` led (`0.8000`), ahead of `relicfml4` (`0.7636`),
    `relicfmlice4` (`0.7273`), `nozone` (`0.6818`), and `alaknonex`
    (`0.6636`).
- Focused repeated check:
  - `analysis_outputs/post_54495224_repeated_deckcopy_toru_g3r2_seed1880000_summary.csv`
  - `relicfmlice4` led (`0.7576`), with `victorvvdeck` second (`0.7424`)
    and `nozone` lower (`0.7121`).
- Broad latest-lossset check:
  - `analysis_outputs/post_54495224_broad_deckcopy_toru_g4_seed1890000_summary.csv`
  - `victorvvdeck` led (`0.7868`), ahead of `nozone` (`0.7794`),
    current (`0.7500`), `relicfmlice4` (`0.7426`), and `alaknonex`
    (`0.7353`).
- Broad repeated check:
  - `analysis_outputs/post_54495224_repeated_broad_deckcopy_toru_g3r2_seed1900000_summary.csv`
  - `victorvvdeck` led (`0.8186`), followed by current (`0.7941`),
    `relicfmlice4` (`0.7696`), and `nozone` (`0.7353`).

Package:
- Created and verified:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`.
- Package check:
  - `main.py` compiles.
  - `deck.csv` has 60 lines.
  - Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.

Decision:
- Promote `victorvvdeck` as the next reset-after-fetch submit candidate.
- New submit queue:
  1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
  3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 01:54 JST - Still No New Public Episodes

Live state:
- API score for `54495224` is unchanged at `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added between
  `monitor_54495224_20260710_014656_episodes.csv` and
  `monitor_54495224_20260710_015442_episodes.csv`.

Decision:
- No new analysis is needed.
- Keep the submit queue unchanged, with `nozone_victorvvdeck` first.

### 2026-07-10 01:55 JST - Submit Queue Confirmed

Live state:
- API score for `54495224` is still `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added between
  `monitor_54495224_20260710_015442_episodes.csv` and
  `monitor_54495224_20260710_015540_episodes.csv`.

Additional validation:
- Ran a smaller repeated submit-queue check:
  - `analysis_outputs/post_54495224_repeated_submitqueue_g2r2_seed1910000_summary.csv`
  - `victorvvdeck` remained best (`0.7941`), followed by current (`0.7353`)
    and `nozone` (`0.7132`).

Decision:
- Keep `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the next submit candidate.
- Still before reset, so no submit was attempted.

### 2026-07-10 01:57 JST - No New Public Episodes

Live state:
- API score for `54495224` is unchanged at `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added between
  `monitor_54495224_20260710_015540_episodes.csv` and
  `monitor_54495224_20260710_015748_episodes.csv`.

Decision:
- No new analysis is needed.
- Keep `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

### 2026-07-10 01:58 JST - Still Waiting For Reset

Live state:
- API score for `54495224` is unchanged at `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added between
  `monitor_54495224_20260710_015748_episodes.csv` and
  `monitor_54495224_20260710_015855_episodes.csv`.

Decision:
- Still before the allowance reset; no submit attempted.
- Keep `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  first in the submit queue.

### 2026-07-10 02:00 JST - No New Public Episodes

Live state:
- API score for `54495224` is unchanged at `953.5`.
- Public episodes remain at `55`, with a public record of `30-25`.
- No new public episode was added between
  `monitor_54495224_20260710_015855_episodes.csv` and
  `monitor_54495224_20260710_020002_episodes.csv`.

Decision:
- Still before the allowance reset; no submit attempted.
- Keep `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  first in the submit queue.

### 2026-07-10 02:10 JST - ysakuragi Marnie Loss Added, Hybrid Candidate Promoted

Live state:
- API score for `54495224` is now `947.4`.
- Public episode count is `57`, with a public record of `31-26`.
- One new public loss appeared after `02:00 JST`:
  - Episode `85050361`, opponent `ysakuragi`, reward `-1`.
  - Score moved from `953.5853474161098` to `947.4072533026882`.

Replay read:
- The loss was not an Alakazam or Archaludon mirror loss. It was a
  Marnie/Grimmsnarl ex deck.
- Extracted opponent deck included:
  - `4` Marnie's Impidimp, `2` Marnie's Morgrem, `4` Marnie's Grimmsnarl ex.
  - `3` Munkidori, `3` Dunsparce, `3` Dudunsparce.
  - `4` Rare Candy, `4` Buddy-Buddy Poffin, `4` Poke Pad.
  - `4` Lillie's Determination, `3` Dawn, `3` Spikemuth Gym.
  - `2` Boss's Orders, `1` Budew, `1` Yveltal, `1` Tool Scrapper,
    `1` Fezandipiti ex, `1` Hero's Cape, `1` Xerosic's Machinations,
    `1` Risky Ruins, `10` basic Dark Energy.

Local proxy update:
- Added `meta_agents/marnie_ysakuragi_live_85050361_simple`.
- Registered it as `marnie_ysakuragi_live` in `tools/run_meta_suite.py`.
- Verified:
  - `deck.csv` has `60` lines.
  - `main.py` and `tools/run_meta_suite.py` compile.

Candidate work:
- Created a new hybrid candidate:
  - Directory:
    `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_victorvvdeck_nonexwall2`
  - Package:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
- It combines:
  - the `victorvvdeck` mirror-oriented deck swap,
  - the Alakazam no-zone/no-cage non-ex Archaludon hold rule,
  - the `nonexwall2only` one-line guard that only builds the final non-ex wall
    when the opponent has exactly `2` prizes remaining.

Validation:
- Broad latest-loss bucket set, 18 opponents, 4 games per side:
  - `analysis_outputs/post_54495224_hybrid_latest_lossset_g4_seed1950000_summary.csv`
  - `victorvv_nonexwall2`: `120/144` (`0.8333`)
  - `current`: `113/144` (`0.7847`)
  - `victorvvdeck`: `109/144` (`0.7569`)
  - `nonexwall2only`: `109/144` (`0.7569`)
- Focus set, Archaludon mirror + Marnie + Alakazam, 8 games per side:
  - `analysis_outputs/post_54495224_hybrid_focus_mirror_marnie_g8_seed1960000_summary.csv`
  - `victorvv_nonexwall2`: `80/96` (`0.8333`)
  - `current`: `70/96` (`0.7292`)
  - `victorvvdeck`: `63/96` (`0.6562`)
  - `nonexwall2only`: `55/96` (`0.5729`)
- Focus mirror-only slice:
  - `victorvv_nonexwall2`: `24/32` (`0.7500`)
  - `current`: `18/32` (`0.5625`)
  - `victorvvdeck`: `15/32` (`0.4688`)
  - `nonexwall2only`: `15/32` (`0.4688`)

Decision:
- Promote
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
  to the first submit candidate after the allowance reset.
- Do not submit now. It is still before the expected daily allowance reset
  around `09:00 JST`, and the current UTC day already used the submit slots.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:12 JST - Extra Repeated Check Demotes Hybrid Candidate

Live state:
- API score for `54495224` remains `947.4`.
- Public episode count remains `57`, with a public record of `31-26`.
- No new public episode was added between
  `monitor_54495224_20260710_021000_episodes.csv` and
  `monitor_54495224_20260710_021200_episodes.csv`.

Additional validation:
- Re-ran a separate no-trace repeated latest-loss bucket check:
  - `analysis_outputs/post_54495224_hybrid_repeated_lossset_g2r2_seed1970000_summary.csv`
  - `victorvvdeck`: `121/144` (`0.8403`)
  - `victorvv_nonexwall2`: `115/144` (`0.7986`)
  - `current`: `113/144` (`0.7847`)
- Re-ran a focused repeated check on Archaludon mirror, Marnie, and Alakazam:
  - `analysis_outputs/post_54495224_hybrid_repeated_focus_g3r3_seed1980000_summary.csv`
  - `victorvvdeck`: `79/108` (`0.7315`)
  - `current`: `77/108` (`0.7130`)
  - `victorvv_nonexwall2`: `76/108` (`0.7037`)

Interpretation:
- The hybrid candidate looked strong in one focused seed block, but the
  repeated checks show it is less stable than the original `victorvvdeck`.
- Its mirror slice remains playable, but it loses too much reliability against
  some Marnie/Alakazam buckets, especially compared with `victorvvdeck`.

Decision:
- Demote
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
  to an alternate.
- Restore
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after the allowance reset.
- Still before the expected `09:00 JST` allowance reset, so no submit was
  attempted.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:46 JST - Submit Wait-Time Rule

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_024400_episodes.csv` and
  `monitor_54495224_20260710_0246_episodes.csv`.

Observed score path for this submission:
- 30 minutes: `8` public episodes, `7-1`, score `936.6`.
- 60 minutes: `18` public episodes, `14-4`, score `1009.1`.
- 90 minutes: `26` public episodes, `19-7`, score `1026.5`.
- 120 minutes: `36` public episodes, `21-15`, score `968.0`.
- 180 minutes: `53` public episodes, `29-24`, score `950.9`.
- 240 minutes: `58` public episodes, `32-26`, score `951.8`.

Decision:
- A 1-hour early stop/re-submit decision is too noisy for this environment:
  the same submission looked like a 1000+ score candidate at 60-90 minutes,
  then regressed after harder/later public matches.
- Use `2-3 hours` or roughly `30+` public episodes as the normal minimum
  before judging a candidate.
- Exception: if a candidate is clearly broken, for example repeated early
  losses, packaging/runtime errors, or a score below roughly `800` after
  enough public matches, then a faster re-submit can be justified.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.

### 2026-07-10 02:20 JST - No New Episodes, Nozone Deck Variants Screened

Live state:
- API score for `54495224` remains `947.4`.
- Public episode count remains `57`, with a public record of `31-26`.
- No new public episode was added between
  `monitor_54495224_20260710_021200_episodes.csv` and
  `monitor_54495224_20260710_021600_episodes.csv`.

Variant screen:
- Checked existing `nozonecage` deck variants before the reset submit:
  - `fml4_cutenergy`
  - `relic_cutenergy`
  - `relicfml4_cutenergyboss`
  - `relicfml4_cutenergyexplorer`
  - `relicfml4_cutenergygear`
  - `relicfmlice4_nonex1`
  - `victorvvdeck_nonexwall2`
- All candidate `deck.csv` files had `60` lines and all candidate `main.py`
  files compiled.

Light repeated screen:
- `analysis_outputs/post_54495224_nozone_variants_repeated_lossset_g1r2_seed1990000_summary.csv`
- Top result was a tie:
  - `victorvvdeck`: `58/72` (`0.8056`)
  - `relicgear`: `58/72` (`0.8056`)
  - `current`: `58/72` (`0.8056`)
- `relicgear` looked interesting because it had a better Alakazam slice, but
  its Marnie slice was lower than `current` and `victorvvdeck`.

Thicker top-variant check:
- `analysis_outputs/post_54495224_top_nozone_variants_repeated_lossset_g2r3_seed2000000_summary.csv`
- Latest-loss bucket aggregate:
  - `victorvvdeck`: `172/216` (`0.7963`)
  - `current`: `171/216` (`0.7917`)
  - `relicice`: `162/216` (`0.7500`)
  - `relicgear`: `162/216` (`0.7500`)
- Mirror slice:
  - `relicgear`: `11/24` (`0.4583`)
  - `victorvvdeck`: `8/24` (`0.3333`)
  - `current`: `8/24` (`0.3333`)
- Marnie slice:
  - `current`: `43/48` (`0.8958`)
  - `victorvvdeck`: `41/48` (`0.8542`)
  - `relicice`: `34/48` (`0.7083`)
  - `relicgear`: `33/48` (`0.6875`)
- Alakazam slice:
  - `victorvvdeck`: `88/108` (`0.8148`)
  - `current`: `86/108` (`0.7963`)
  - `relicice`: `85/108` (`0.7870`)
  - `relicgear`: `83/108` (`0.7685`)

Decision:
- Do not promote `relicgear` or `relicice`. Their mirror improvement is not
  enough to offset the Marnie/Alakazam drop in the thicker check.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after the allowance reset.
- Still before the expected `09:00 JST` reset, so no submit was attempted.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:21 JST - No New Public Episodes

Live state:
- API score for `54495224` remains `947.4`.
- Public episode count remains `57`, with a public record of `31-26`.
- No new public episode was added between
  `monitor_54495224_20260710_021600_episodes.csv` and
  `monitor_54495224_20260710_022100_episodes.csv`.

Decision:
- No new loss is available for replay analysis.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:23 JST - Still No New Public Episodes

Live state:
- API score for `54495224` remains `947.4`.
- Public episode count remains `57`, with a public record of `31-26`.
- No new public episode was added between
  `monitor_54495224_20260710_022100_episodes.csv` and
  `monitor_54495224_20260710_022300_episodes.csv`.

Decision:
- No replay analysis was needed because no new public loss appeared.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:25 JST - New Public Win, Marnie Proxy Added

Live state:
- API score for `54495224` improved from `947.4` to `951.7`.
- Public episode count increased from `57` to `58`.
- Public record is now `32-26`.
- New public episode:
  - Episode `85053222`, opponent `Ars Noveau`, reward `1`.
  - Score moved from `947.4072533026882` to `951.7724491061891`.

Replay read:
- The opponent was another Marnie/Grimmsnarl ex deck, but with a different
  mix from `ysakuragi`:
  - `3` Marnie's Grimmsnarl ex, `3` Marnie's Morgrem, `4` Marnie's Impidimp.
  - `2` Froslass, `2` Snorunt, `4` Munkidori.
  - `4` Buddy-Buddy Poffin, `4` Poke Pad, `3` Rare Candy, `3` Night Stretcher.
  - `4` Lillie's Determination, `4` Team Rocket's Petrel, `2` Boss's Orders.
  - `2` Handheld Fan, `4` Spikemuth Gym, `1` Unfair Stamp, `1` Dawn,
    `10` basic Dark Energy.
- We won the late game by clearing the opponent's Grimmsnarl board.

Local proxy update:
- Added `meta_agents/marnie_arsnoveau_live_85053222_simple`.
- Registered it as `marnie_arsnoveau_live` in `tools/run_meta_suite.py`.
- Verified:
  - `deck.csv` has `60` lines.
  - `main.py` and `tools/run_meta_suite.py` compile.

Quick Marnie regression check:
- `analysis_outputs/post_54495224_marnie_arsnoveau_check_g4_seed2010000_summary.csv`
- Marnie slice aggregate:
  - `current`: `19/24` (`0.7917`)
  - `victorvvdeck`: `19/24` (`0.7917`)
  - `hybrid`: `18/24` (`0.7500`)
- Against the new `marnie_arsnoveau_live` proxy:
  - `current`: `8/8` (`1.0000`)
  - `hybrid`: `7/8` (`0.8750`)
  - `victorvvdeck`: `6/8` (`0.7500`)
- `victorvvdeck` remains acceptable because it gains against other Marnie
  variants and still has the broader latest-loss-bucket lead from prior checks.

Decision:
- No new loss is available for replay-driven fixes.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:28 JST - No New Episodes, Ars Noveau Proxy Recheck

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_022500_episodes.csv` and
  `monitor_54495224_20260710_022800_episodes.csv`.

Additional validation:
- Ran a focused repeated check after adding `marnie_arsnoveau_live`:
  - `analysis_outputs/post_54495224_top_candidates_arsnoveau_focus_g2r2_seed2020000_summary.csv`
- Aggregate over `marnie_arsnoveau_live`, `marnie_ysakuragi_live`,
  `marnie_shishio_live`, recent Archaludon mirrors, and recent Alakazam
  proxies:
  - `victorvvdeck`: `52/64` (`0.8125`)
  - `current`: `47/64` (`0.7344`)
  - `hybrid`: `43/64` (`0.6719`)
- Slice results:
  - Marnie: `victorvvdeck` `23/24` (`0.9583`), `current` `21/24`
    (`0.8750`), `hybrid` `20/24` (`0.8333`).
  - Archaludon mirror: `hybrid` `10/16` (`0.6250`), `victorvvdeck`
    `9/16` (`0.5625`), `current` `5/16` (`0.3125`).
  - Alakazam: `current` `21/24` (`0.8750`), `victorvvdeck` `20/24`
    (`0.8333`), `hybrid` `13/24` (`0.5417`).

Decision:
- `victorvvdeck` remains the best overall reset candidate after adding the
  `Ars Noveau` Marnie proxy.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:30 JST - Score Stable, No New Public Episodes

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_022800_episodes.csv` and
  `monitor_54495224_20260710_023000_episodes.csv`.

Decision:
- No new loss is available for replay analysis.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:32 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023000_episodes.csv` and
  `monitor_54495224_20260710_023200_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:33 JST - Still No New Public Episodes

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023200_episodes.csv` and
  `monitor_54495224_20260710_023300_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:34 JST - Stable, No New Public Episodes

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023300_episodes.csv` and
  `monitor_54495224_20260710_023400_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:36 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023400_episodes.csv` and
  `monitor_54495224_20260710_023600_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:37 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023600_episodes.csv` and
  `monitor_54495224_20260710_023700_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:38 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023700_episodes.csv` and
  `monitor_54495224_20260710_023800_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:40 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_023800_episodes.csv` and
  `monitor_54495224_20260710_024000_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:41 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_024000_episodes.csv` and
  `monitor_54495224_20260710_024100_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:43 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_024100_episodes.csv` and
  `monitor_54495224_20260710_024300_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:44 JST - Still Stable

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_024300_episodes.csv` and
  `monitor_54495224_20260710_024400_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Still before the expected `09:00 JST` submit allowance reset, so no submit
  was attempted.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
  as the first submit candidate after reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nonexwall2only.tar.gz`

### 2026-07-10 02:48 JST - Candidate Queue Recheck

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_0246_episodes.csv` and
  `monitor_54495224_20260710_0248_episodes.csv`.

Focused local recheck:
- Output:
  `analysis_outputs/post_54495224_focus_0248_summary.csv`.
- Opponents: recent Marnie, Archaludon, Alakazam, Cynthia, and Lucario
  live proxies.
- Results:
  - `current`: `187/240`, win rate `0.7792`.
  - `victorvvdeck`: `183/240`, win rate `0.7625`.
  - `victorvv_nonexwall2`: `192/240`, win rate `0.8000`.

Broad thin screen:
- Output:
  `analysis_outputs/post_54495224_broad_thin_0248_summary.csv`.
- One game per seat, two repeats, all registered meta buckets. This is only
  a regression screen, not a final strength estimate.
- Equal bucket result:
  - `current`: win rate `0.8238`.
  - `victorvvdeck`: win rate `0.8402`.
  - `victorvv_nonexwall2`: win rate `0.8443`.
- Weighted public sample checks:
  - `public_sample_2026_07_03_top20`: `current` `0.8816`,
    `victorvvdeck` `0.8421`, `victorvv_nonexwall2` `0.7434`.
  - `public_sample_2026_07_02_top20`: `current` `0.8313`,
    `victorvvdeck` `0.8875`, `victorvv_nonexwall2` `0.6625`.
  - `discussion_ogerpon_toolbox_2026_07_04`: `current` `0.8654`,
    `victorvvdeck` `0.7885`, `victorvv_nonexwall2` `0.6731`.

Decision:
- Do not submit now; still before the expected `09:00 JST` allowance reset.
- Keep `victorvvdeck` as the first post-reset candidate because it is the
  better compromise across broad/top20 checks.
- Keep `victorvv_nonexwall2` second: it targets the recent Archaludon/Marnie
  pain points better, but the Ogerpon-weighted and top20 screens show enough
  regression risk that it should not jump ahead without more live evidence.

### 2026-07-10 02:52 JST - Relic FML Boss Candidate Promoted

Live state:
- API score for `54495224` remains `951.7`.
- Public episode count remains `58`, with a public record of `32-26`.
- No new public episode was added between
  `monitor_54495224_20260710_0248_episodes.csv` and
  `monitor_54495224_20260710_0252_episodes.csv`.

Candidate finding:
- `victorvvdeck` and `victorvv_nonexwall2` gained some mirror/live-proxy
  points, but their deck cuts removed the two non-ex `Archaludon` cards and
  made the Ogerpon bucket much worse.
- The existing
  `gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss`
  variant keeps the two non-ex `Archaludon`, adds `Relicanth`, raises
  `Full Metal Lab` to 4, cuts one Metal Energy and one Boss.

Local evidence:
- Core meta screen:
  `analysis_outputs/post_54495224_relic_coremeta_0252_summary.csv`.
  - `relic_fml_boss` equal buckets: `0.8889` vs current `0.8611`.
  - `public_sample_2026_07_03_top20`: `0.8860` vs current `0.8355`.
  - `public_sample_2026_07_02_top20`: `0.8667` vs current `0.7771`.
  - Ogerpon toolbox weight: `0.8333` vs current `0.8269`.
- Recent live-proxy focus:
  `analysis_outputs/post_54495224_relic_fml_boss_focus_0252_summary.csv`.
  - Equal buckets: `0.7531` vs current `0.7500`.
  - Better into `archaludon_victorvv_live`, `archaludon_toru_live`,
    `lucario_mekeh_live`, and `marnie_ysakuragi_live`.
  - Worse into `cynthia_garchomp_topdecking_live`,
    `marnie_arsnoveau_live`, and `alakazam_pompom_live`.

Package:
- Created and verified:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`.
- Package root contains `main.py`, `deck.csv`, `requirements.txt`, and
  `cg/`.
- Extracted `deck.csv` has `60` cards and extracted `main.py` compiles.
- Smoke output:
  `analysis_outputs/package_smoke_relic_fml_boss_summary.csv`.

Decision:
- Promote this package to first candidate after the next allowance reset.
- Do not submit now; still before the expected `09:00 JST` reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage.tar.gz`

### 2026-07-10 03:10 JST - Two New Losses, Cubchoo Guard Candidate

Live state:
- API score for `54495224` fell from `951.7` to `943.5`.
- Public episode count increased from `58` to `60`, with a public record of
  `32-28`.
- New losses:
  - `85056873` vs `matsurih`, score `951.7724 -> 948.1939`.
  - `85057952` vs `senkin13`, score `948.1939 -> 943.5999`.

Replay/deck analysis:
- `85056873`: Battle Cage Alakazam. Opponent deck was extracted to
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/episode_85056873_decks`.
- `85057952`: Cubchoo disruption with `Enhanced Hammer`, `Crushing Hammer`,
  `Eri`, `Xerosic`, `Neutralization Zone`, and `Nighttime Mine`. Opponent
  deck was extracted to
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/episode_85057952_decks`.
- The Cubchoo loss showed the agent repeatedly ending turns while active
  `Archaludon ex` was attack-locked by Cubchoo's `Snotted Up`; retreat was
  available but scored as `don't retreat HP400 tank`.

New local proxies:
- Added `meta_agents/alakazam_matsurih_live_85056873_simple`.
- Added `meta_agents/cubchoo_senkin13_live_85057952_simple`.
- Registered both in `tools/run_meta_suite.py`.
- Smoke output:
  `analysis_outputs/new_live_proxy_smoke_0301_summary.csv`.

Candidate:
- Created `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooguard`.
- Change: add Cubchoo matchup detection and, only when active `Archaludon ex`
  has no attack option against Cubchoo, score retreat highly to clear the
  attack lock.
- Replay decision inspection confirms retreat becomes the top option in the
  same locked positions:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/episode_85057952_replay.json`.

Local evidence:
- New-loss proxy screen:
  `analysis_outputs/post_54495224_cubchooguard_newloss_0301_summary.csv`.
  - `cubchoo_senkin13_live`: `cubchooguard` `0.7167` vs current `0.2333`.
  - `alakazam_matsurih_live`: `cubchooguard` `0.6500` vs current `0.7833`
    in that run, but this appears noisy because the Cubchoo patch is gated
    to Cubchoo detection.
- Core plus new-loss screen:
  `analysis_outputs/post_54495224_cubchooguard_core_newloss_0301_summary.csv`.
  - Equal buckets: `cubchooguard` `0.8492` vs current `0.7817`.
  - `public_sample_2026_07_03_top20`: `0.8173` vs current `0.7792`.
  - `public_sample_2026_07_02_top20`: `0.7806` vs current `0.7556`.
  - Ogerpon toolbox weight: `0.8077` vs current `0.7564`.
  - `cubchoo_senkin13_live`: `0.7222` vs current `0.3333`.
  - `alakazam_matsurih_live`: `0.8333` vs current `0.7778`.

Package:
- Created and verified:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`.
- Package root contains `main.py`, `deck.csv`, `requirements.txt`, and
  `cg/`.
- Extracted `deck.csv` has `60` cards and extracted `main.py` compiles.
- Smoke output:
  `analysis_outputs/package_smoke_cubchooguard_summary.csv`.

Decision:
- Promote `cubchooguard` to the first candidate after the next allowance
  reset.
- Do not submit now; current time is `03:10 JST`, still before the expected
  `09:00 JST` reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`

### 2026-07-10 03:26 JST - Cubchoo Active Guard Promoted

Live state:
- API score for `54495224` remains `943.5`.
- Public episode count remains `60`, with a public record of `32-28`.
- No new public episode was added through
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0323_episodes.csv`.
- Do not submit now; current time is `03:26 JST`, still before the expected
  `09:00 JST` allowance reset.

Patch:
- Created
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard`.
- This keeps the Cubchoo matchup detection and damage estimate, but narrows
  the emergency retreat rule to the exact observed lock shape: opponent active
  is `Cubchoo` (`506`), our active is `Archaludon ex`, and no attack option is
  currently available.
- Replay inspection on live loss `85057952` confirmed the agent now selects
  `Cubchoo: retreat to clear attack lock` in the repeated locked positions.

Validation:
- Broad fair-seed check:
  `analysis_outputs/post_54495224_activeguard_fair_core_0323_summary.csv`.
  - Equal public buckets: `activeguard` `0.8125`, `cubchooguard` `0.8036`,
    current `0.7768`.
  - `cubchoo_senkin13_live`: `0.7500`, `0.8750`, `0.2500`.
  - `public_sample_2026_07_03_top20`: `0.8388`, `0.7796`, `0.7862`.
- Focused fair-seed recheck:
  `analysis_outputs/post_54495224_activeguard_focus_0325_summary.csv`.
  - Equal public buckets: `activeguard` `0.8167`, `cubchooguard` `0.7417`,
    current `0.6833`.
  - `cubchoo_senkin13_live`: `0.7500`, `0.5833`, `0.2083`.
  - `archaludon`: `0.6250`, `0.5000`, `0.5417`.
  - `starmie`: `1.0000`, `0.8750`, `0.9583`.
  - `public_sample_2026_07_03_top20`: `0.8125`, `0.6875`, `0.7500`.
- Packaged and verified:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`.
  Archive root contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/`;
  extracted `main.py` compiles, `deck.csv` has 60 lines, and package smoke
  output is
  `analysis_outputs/package_smoke_cubchooactiveguard_summary.csv`.

Decision:
- Promote `cubchooactiveguard` over `cubchooguard` as the next submit
  candidate. It keeps the target Cubchoo fix while reducing broad retreat
  misfire risk and showed better focused fair-seed results.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 03:35 JST - Two More Losses, Fast Backup Rejected

Live state:
- CLI score for `54495224` fell to `933.6`.
- Public episode count increased from `60` to `62`, with a public record of
  `32-30`.
- New monitor output:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0327_episodes.csv`.
- New public losses:
  - `85060465` vs `Hamu.py`: Mega Lucario. Replay ends with our side on a
    single `Archaludon ex` line and no bench; Mega Lucario takes the final KO.
  - `85060632` vs `Rojiomote`: Dragapult. Replay also ends with a single
    `Archaludon ex` line and no bench.

Local proxy additions:
- Added `meta_agents/mega_lucario_hamu_live_85060465_simple` by copying the
  Lucario proxy logic and replacing the deck with Hamu.py's extracted list.
- Added `meta_agents/dragapult_rojiomote_live_85060632_simple` by copying the
  Dragapult proxy logic and replacing the deck with Rojiomote's extracted list.
- Registered both in `tools/run_meta_suite.py` as:
  - `lucario_hamu_live`
  - `dragapult_rojiomote_live`
- Both proxy decks have 60 cards and their `main.py` files compile.

Candidate probe:
- Created
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard_fastbackup`.
- Idea: when Lucario or Dragapult is visible and our Duraludon/Archaludon line
  count is `<= 1`, Explorer should keep `Ultra Ball` / backup `Duraludon`, and
  empty-bench `Ultra Ball` should be playable to search a backup body.
- Replay decision inspection confirmed the intended local decision changed:
  the agent keeps `Ultra Ball` in both new loss replays.

Validation:
- New-loss proxy comparison:
  `analysis_outputs/post_54495224_newloss_proxy_compare_0329_summary.csv`.
  - Equal selected buckets: `activeguard` `0.8437`, `cubchooguard` `0.8021`,
    current `0.7188`.
  - `activeguard` remained the best selected-bucket candidate, helped by the
    Cubchoo fix and strong Dragapult/Rojiomote proxy result.
- Fast-backup broad focus:
  `analysis_outputs/post_54495224_fastbackup_compare_0332_summary.csv`.
  - Equal selected buckets: `activeguard` `0.8712`, `fastbackup` `0.8712`,
    current `0.7576`.
  - `fastbackup` looked plausible but had worse Dragapult/Starmie slices.
- Fast-backup focused recheck:
  `analysis_outputs/post_54495224_fastbackup_focus_0334_summary.csv`.
  - Equal selected buckets: `activeguard` `0.8490`, `fastbackup` `0.8229`,
    current `0.7865`.
  - `lucario_hamu_live`: `activeguard` `0.9583`, `fastbackup` `0.8750`,
    current `1.0000`.
  - `dragapult_rojiomote_live`: `activeguard` `0.9583`, `fastbackup` `0.9583`,
    current `1.0000`.
  - `starmie`: `activeguard` `0.8750`, `fastbackup` `0.7500`.
  - Public sample checks were also worse for `fastbackup`.

Decision:
- Reject `fastbackup` for now. The replay-specific decision is attractive, but
  the local game results do not justify adding the extra rule before the next
  submission.
- Keep `cubchooactiveguard` as the next submission candidate after the daily
  allowance reset. It targets the clear Cubchoo lock bug and stays strongest
  on the selected live-loss/equal-bucket comparison.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 03:42 JST - Victorvv Nonexwall Cubchoo Hybrid Rejected

Live state:
- CLI score for `54495224` remains `933.6`.
- Public episode count remains `62`, with a public record of `32-30`.
- No new public episode was added through
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0335_episodes.csv`.

Observed loss mix:
- Re-extracted all public replay decks to
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/all_62_decks_0335`.
- Current public losses are concentrated in:
  - `alakazam_psychic`: `5-13`.
  - `marnie_grimmsnarl`: `4-8`.
  - `mega_lucario`: `2-3`.
  - `archaludon_metal`: `8-2`.
  - `dragapult`: `0-2` plus one win.
- A loss-mix screen over the live-loss proxies briefly favored
  `victorvv_nonexwall2`, so a Cubchoo-safe hybrid was tested.

Hybrid:
- Created
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_victorvvdeck_nonexwall2_cubchooactiveguard`.
- Change: add only the Cubchoo matchup detection, `opp_max_damage == 10`, and
  the active-Cubchoo attack-lock retreat rule to `victorvv_nonexwall2`.
- Replay decision inspection on `85057952` confirmed it now chooses
  `Cubchoo: retreat to clear attack lock`.

Validation:
- Loss-mix confirmation:
  `analysis_outputs/post_54495224_victorvv_cubchoo_lossmix_confirm_0340_summary.csv`.
  - `victorvv_nonexwall2_cubchoo`: `0.8170`.
  - `activeguard`: `0.8080`.
  - current: `0.7723`.
- Broad/current-meta confirmation:
  `analysis_outputs/post_54495224_victorvv_cubchoo_broad_confirm_0342_summary.csv`.
  - Equal buckets: `activeguard` `0.8594`,
    `victorvv_nonexwall2_cubchoo` `0.8359`, current `0.8125`.
  - `public_sample_2026_07_03_top20`: `activeguard` `0.8717`,
    `victorvv_nonexwall2_cubchoo` `0.7632`, current `0.7993`.
  - Ogerpon toolbox: `activeguard` `0.8173`,
    `victorvv_nonexwall2_cubchoo` `0.7019`, current `0.7692`.
  - Cubchoo proxy: both `activeguard` and the hybrid are `0.7500`.

Decision:
- Reject `victorvv_nonexwall2_cubchoo` for the next submission. It is slightly
  better on the narrow loss-mix confirmation but loses too much on broad
  Ogerpon / July top20 checks.
- Keep `cubchooactiveguard` as the next submission candidate.
- Do not submit now; current time is `03:42 JST`, still before the expected
  `09:00 JST` allowance reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`

### 2026-07-10 04:48 JST - New Public Episodes and Genki Lucario Import

Kaggle update:
- Latest submission `54495224` moved from `938.3` to `942.4`.
- Public episodes increased from `63` to `66`.
- Latest episode CSV:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replays_54495224_20260710_0442_episodes.csv`.
- New public games:
  - `85069764`: win vs `Jack`, Okidogi/Barbaracle-style fighting toolbox.
  - `85069777`: loss vs `genki toyama`, Mega Lucario ex.
  - `85070690`: win vs `kisamaki0815`, Alakazam.

Loss triage:
- Updated deck extraction:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/all_66_decks_0444_v2`.
- Updated loss endstates:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_endstates_54495224_20260710_0444_v2.csv`.
- Loss buckets now:
  - Alakazam: `13`.
  - Marnie: `8`.
  - Mega Lucario: `4`.
  - Archaludon: `2`.
  - Dragapult: `2`.
- New loss `85069777` ended as:
  `empty_bench;thin_archaludon_line;opp_wide_board`.
  Our side had a single Archaludon ex, no bench, 3 prizes left.
  Opponent had Mega Lucario ex active, 4 bench, 1 prize left.

Tooling fix:
- `tools/extract_episode_decks.py` now resolves archetype marker ties by marker
  definition order instead of reverse name order.
- This prevents Mega Lucario decks that also contain Solrock/Lunatone from being
  mislabeled as `okidogi_barbaracle`.

New local meta agent:
- Added:
  `meta_agents/mega_lucario_genki_live_85069777_simple`.
- Registered as `lucario_genki_live` in `tools/run_meta_suite.py`.
- Added scenario `live_genki_lucario_2026_07_10`.
- Added the same scenario/bucket to `tools/aggregate_meta_summaries.py`.

Genki Lucario local check:
- Output:
  `analysis_outputs/post_54495224_genki_lucario_candidate_check_20260710_0445_summary.csv`.
- Results, 48 games:
  - `current`: `0.9583`.
  - `activeguard`: `0.9375`.
  - `strict`: `0.9167`.
  - `greattusk`: `0.7917`.

Decision:
- Do not submit immediately. Current score is improving and current already tests
  well into the imported Genki Lucario mimic.
- Keep strict Cubchoo-control retreat package as the first replacement candidate
  if the current submission later stalls or resumes losing, but do not force a
  post-reset submit while the public score is still climbing.

### 2026-07-10 04:52 JST - Lucario Line3 Probe Rejected

Motivation:
- Loss `85069777` ended with a single Archaludon ex and no bench.
- Replay decision inspection showed that Ultra Ball was available earlier, but
  the current agent skipped it because the hand did not meet the safe-discard
  threshold.

Probe:
- Created:
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_lucarioline3`.
- Change:
  - Against `lucario`, raise the Duraludon/Archaludon ex line target from `2`
    to `3`.
  - Add a Lucario-only Ultra Ball override to search the third line when a
    discard pair is available.
- Replay inspection confirmed the intended branch:
  `Lucario: search 3rd line` became the top Ultra Ball score around step 105 of
  replay `85069777`.

Local evidence:
- Lucario focus:
  `analysis_outputs/post_54495224_lucarioline3_lucario_focus_20260710_0447_summary.csv`.
  - `current`: equal buckets `0.9219`.
  - `lucarioline3`: equal buckets `0.9271`.
  - Improved Genki/Fujiborozoukin/AIB4, but hurt Hamu.
- Recent live broad:
  `analysis_outputs/post_54495224_lucarioline3_recent_live_g8_20260710_0448_summary.csv`.
  - `current`: equal buckets `0.7448`.
  - `lucarioline3`: equal buckets `0.6979`.
  - Regressions appeared into Archaludon mirror, Cubchoo, Iono, Dragapult, and
    the new Genki Lucario bucket.

Decision:
- Reject `lucarioline3`.
- The replay explanation is useful, but forcing Ultra Ball for the third line is
  too disruptive across the live mix.
- Keep current public submission running while score is increasing.

### 2026-07-10 04:58 JST - Akira Lucario Imported and Queue Rechecked

External state:
- Time check: still before reset (`04:49-04:50 JST`).
- Latest Kaggle submission `54495224` remains `942.4` with `66` public episodes.
- No new public episodes after
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0450_episodes.csv`.
- Current leaderboard top 20 lower bound is around `1063`, so `942.4` is not
  gold-range.

Episode data refresh:
- Refreshed the official episode manifest into
  `data/episodes_index/manifest_refresh.csv`.
- Latest official daily episode dataset available is still `2026-07-08`.
- Re-downloaded the available 2026-07-08 sample into
  `data/episodes_refresh_20260710_0451/2026-07-08-sample`.
- The Kaggle dataset API returned 20 files for that day.

Classification fix impact:
- Re-extracted with tie-aware archetype classification:
  `analysis_outputs/episode_decks_2026_07_08_sample20_0451_v3`.
- 2026-07-08 sample archetypes now include:
  - Alakazam `10`.
  - Great Tusk `8`.
  - Marnie `6`.
  - Chandelure `3`.
  - Starmie `3`.
  - Okidogi/Barbaracle `3`.
  - Mega Lucario `2`.

New local meta agent:
- Added:
  `meta_agents/mega_lucario_akira_84743057_simple`.
- Source deck: Akira-Ninth from public episodes `84743057`/`84743065`.
- Deck shape:
  pure Mega Lucario with Riolu/Lucario, Solrock/Lunatone, Premium Power Pro,
  Fighting Gong, Carmine, Xerosic, 10 Fighting Energy, 3 Rock Fighting Energy.
- Registered in:
  - `tools/run_meta_suite.py` as `lucario_akira_2026_07_08`.
  - `tools/aggregate_meta_summaries.py`.
- Added scenario:
  `public_akira_lucario_2026_07_08`.

Akira-only check:
- Output:
  `analysis_outputs/post_54495224_akira_lucario_candidate_check_20260710_0453_summary.csv`.
- 48 games:
  - `activeguard`: `0.9583`.
  - `strict`: `0.9375`.
  - `current`: `0.8958`.
  - `greattusk`: `0.8750`.

Recent-live plus Akira mixed check:
- Output:
  `analysis_outputs/post_54495224_active_strict_akira_recent_live_g8_20260710_0454_summary.csv`.
- Equal buckets, 208 games:
  - `strict`: `0.8221`.
  - `activeguard`: `0.7981`.
  - `current`: `0.7692`.
- `activeguard` remains best into Cubchoo and Akira Lucario but drops harder into
  Archaludon mirror and Genki/Hamu Lucario.
- `strict` is the best compromise in this mixed set.

Decision:
- Keep current Kaggle submission running because score is still rising and reset
  has not happened.
- If current later stalls or drops after reset, submit the strict package first:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchoocontrolretreat.tar.gz`.
- Do not submit `activeguard` first despite its Cubchoo/Akira strength, because
  its broader Cubchoo damage-detection side effect is still riskier.

### 2026-07-10 03:18 JST - Package Ready, No New Episodes

Live state:
- API score for `54495224` remains `943.5`.
- Public episode count remains `60`, with a public record of `32-28`.
- No new public episode was added between
  `monitor_54495224_20260710_0315_episodes.csv` and
  `monitor_54495224_20260710_0318_episodes.csv`.

Package check:
- Re-extracted
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
  to `analysis_outputs/package_verify_cubchooguard_latest`.
- Package root contains `main.py`, `deck.csv`, `requirements.txt`, and
  `cg/`.
- Extracted `deck.csv` has `60` cards.
- Extracted `main.py` compiles.
- Extracted `main.py` contains the Cubchoo-specific matchup detection and
  `Cubchoo: retreat to clear attack lock` rule.
- Diff check against
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooguard/main.py`
  showed no content difference.

Decision:
- Keep `cubchooguard` as the first submit candidate.
- Do not submit now; current time is `03:18 JST`, still before the expected
  `09:00 JST` allowance reset.

### 2026-07-10 03:19 JST - Still No New Episodes

Live state:
- API score for `54495224` remains `943.5`.
- Public episode count remains `60`, with a public record of `32-28`.
- No new public episode was added between
  `monitor_54495224_20260710_0318_episodes.csv` and
  `monitor_54495224_20260710_0319_episodes.csv`.

Decision:
- No new replay analysis is needed.
- Keep
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
  as the first submit candidate after reset.
- Do not submit now; current time is `03:19 JST`, still before the expected
  `09:00 JST` allowance reset.

### 2026-07-10 03:11 JST - Relic Cubchoo Hybrid Rejected

Live state:
- API score for `54495224` remains `943.5`.
- Public episode count remains `60`, with a public record of `32-28`.
- No new public episode was added between
  `monitor_54495224_20260710_0301_episodes.csv` and
  `monitor_54495224_20260710_0311_episodes.csv`.

Hybrid test:
- Created
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_relicfmlboss_cubchooguard`
  by applying the Cubchoo retreat guard to the `relic_fml_boss` deck.
- Replay decision inspection confirmed the hybrid also retreats from the
  Cubchoo attack-lock position.
- Output:
  `analysis_outputs/post_54495224_relic_cubchoo_core_newloss_0311_summary.csv`.

Result:
- `relic_cubchoo` improves `cubchoo_senkin13_live` and Archaludon mirror
  relative to current, but loses too much against `alakazam_matsurih_live`,
  Ogerpon Cornerstone, and weighted public sample checks.
- `cubchooguard` keeps the original deck and changes only Cubchoo-detected
  retreat behavior. Non-Cubchoo differences in local runs should mostly be
  treated as native-engine shuffle variance.

Decision:
- Keep `cubchooguard` as the first submit candidate.
- Do not promote `relic_cubchoo`.
- Do not submit now; current time is `03:11 JST`, still before the expected
  `09:00 JST` allowance reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`

### 2026-07-10 03:15 JST - Cubchoo Guard Fair-Seed Recheck

Live state:
- API score for `54495224` remains `943.5`.
- Public episode count remains `60`, with a public record of `32-28`.
- No new public episode was added between
  `monitor_54495224_20260710_0311_episodes.csv` and
  `monitor_54495224_20260710_0315_episodes.csv`.

Broad screen:
- Output:
  `analysis_outputs/post_54495224_cubchooguard_broad_all_0315_summary.csv`.
- A very thin all-bucket repeated run showed noisy drops for `cubchooguard`;
  since non-Cubchoo code paths are unchanged, this looked like native-engine
  shuffle/order variance rather than a clear regression.

Fair-seed core recheck:
- Output:
  `analysis_outputs/post_54495224_cubchooguard_fair_core_0315_summary.csv`.
- Same game-id schedule was used for `current` and `cubchooguard` on core
  meta plus the two new live-loss proxies.
- Result:
  - Equal buckets: `cubchooguard` `0.8839` vs current `0.7411`.
  - `public_sample_2026_07_03_top20`: `0.8289` vs current `0.7467`.
  - `public_sample_2026_07_02_top20`: `0.8344` vs current `0.7031`.
  - Ogerpon toolbox weight: `0.8846` vs current `0.6827`.
  - `cubchoo_senkin13_live`: `0.8750` vs current `0.0000`.

Decision:
- Keep `cubchooguard` as the first submit candidate.
- Do not submit now; current time is `03:15 JST`, still before the expected
  `09:00 JST` allowance reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
### 2026-07-10 03:46 JST - No New Episodes, Activeguard Still First

Live state:
- CLI submission list still shows latest submission `54495224`
  (`submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`)
  as `COMPLETE` with public score `933.6`.
- Public episode refresh wrote
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0346_episodes.csv`.
- Public episode count remains `62`, so no new loss replay is available after
  the `Hamu.py` Lucario and `Rojiomote` Dragapult losses.
- Current local time is `03:46 JST`, still before the expected `09:00 JST`
  Kaggle daily allowance reset. Do not submit before reset.

Tooling:
- Fixed `tools/aggregate_meta_summaries.py` to skip directories whose names end
  in `*_summary.csv`. A saved replay-summary directory had that suffix and
  blocked aggregate scans with `PermissionError`.

Candidate recheck:
- Re-read the older `relic_fml_boss` and `relic_cubchoo` notes. The relic deck
  candidate was once strong, but the Cubchoo-safe relic hybrid regressed on
  Alakazam/Ogerpon-style checks. It should stay behind the safer narrow patch.
- The latest broad confirmation still favors `activeguard` over the tested
  `victorvv_nonexwall2_cubchoo` hybrid:
  - Equal buckets: `activeguard` `0.8594`, hybrid `0.8359`, current `0.8125`.
  - `public_sample_2026_07_03_top20`: `activeguard` `0.8717`, hybrid `0.7632`,
    current `0.7993`.
  - Ogerpon toolbox: `activeguard` `0.8173`, hybrid `0.7019`, current `0.7692`.

Package recheck:
- `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
  contains `main.py`, `deck.csv`, `requirements.txt`, and `cg/` at archive root.
- Extracted `main.py` compiles, extracted `deck.csv` has `60` lines, and the
  Cubchoo lock rule is present:
  - `CUBCHOO_LINE = {506}`
  - `opp_active.id == 506`
  - `Cubchoo: retreat to clear attack lock`
- SHA256:
  `3E1306941A25017D501D8ED3EAC748A3272D07BEC1F1EA9F5A106666CA42F4D7`.

Decision:
- Keep `cubchooactiveguard` as the next submission candidate after allowance
  reset.
- Submit only after rechecking the current score and quota. If the current
  submission has not recovered toward the previous 1000+ peak, use the
  activeguard package first.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 04:22 JST - Current Queue Pointer

- Latest submission `54495224` is still `933.6` with `62` public episodes.
- Current time was `04:15 JST`, so no post-reset submission was made.
- New loss end-state tool:
  `tools/summarize_kaggle_loss_endstates.py`.
- Latest loss end-state output:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_endstates_54495224_20260710_0416.csv`.
- Rejected after local evidence:
  - `marniebackup`.
  - `alakbenchfirst`.
  - `alakthinlillie`.
- First post-reset submission candidate remains:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`.

### 2026-07-10 05:16 JST - Current Queue Pointer

- Latest submission `54495224` has dropped to public score `932.8` with `68`
  public episodes.
- It is still before the expected `09:00 JST` submission allowance reset, so no
  new submission was made.
- Latest imported live opponent:
  `meta_agents/cynthia_garchomp_jason_live_85074031_simple`, registered as
  `cynthia_garchomp_jason_live`.
- Rejected after local evidence:
  - `tmp_compare_submissions/greattusk_ionobenchguard`.
  - `tmp_compare_submissions/greattusk_ionotargetguard`.
- First post-reset submission candidate is now:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:22 JST - Mykhailo Marnie Loss Added

Live state:
- Current time: `05:17 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submitted file `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
  dropped again to public score `929.8`.
- Public episodes increased from `68` to `69`.

New live loss:
- Episode `85075581`: loss vs `Mykhailo Kalus`, opponent submission
  `54412817`, opponent initial score `1030.35`.
- Opponent deck classified as `marnie_grimmsnarl`.
- End state:
  - Our active: `169:Duraludon`, bench count `0`.
  - Opponent active: `648:Marnie's Grimmsnarl ex`.
  - Opponent bench: two `112:Munkidori`, two `648:Marnie's Grimmsnarl ex`,
    one `305:Dunsparce`.
  - Pattern: `empty_bench;thin_archaludon_line;opp_wide_board`.

Updated live loss mix:
- `alakazam_psychic`: `14`.
- `marnie_grimmsnarl`: `9`.
- `mega_lucario`: `4`.
- `archaludon_metal`: `2`.
- `dragapult`: `2`.
- `cynthia_garchomp`: `2`.
- `unknown`: `1`.

New local agent:
- Added `meta_agents/marnie_mykhailo_live_85075581_simple`.
- Registered as `marnie_mykhailo_live`.
- Added scenario `live_mykhailo_marnie_2026_07_10`.
- Deck summary:
  `analysis_outputs/deck_marnie_mykhailo_live_85075581_summary.csv`.

Mykhailo Marnie candidate check:
- Output:
  `analysis_outputs/post_54495224_mykhailo_marnie_candidate_check_20260710_0520_summary.csv`.
- 48 games:
  - current: `0.9167`.
  - activeguard: `0.8750`.
  - Great Tusk: `0.8542`.
  - strict: `0.8125`.
- This bucket is locally favorable for all candidates, but the live submission
  still lost a low-bench game. Treat this as one more signal that the current
  Archaludon branch is unstable in late live sampling.

Updated loss-weighted check:
- Using the previous 14-bucket `g12` run plus Jason Cynthia and Mykhailo
  Marnie:
  - Great Tusk: `0.8309`.
  - activeguard: `0.7938`.
  - current: `0.7788`.
  - strict: `0.7776`.

Decision:
- Keep the first post-reset candidate as:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.
- Do not submit before reset.

### 2026-07-10 05:16 JST - Current Queue Pointer

- Latest submission `54495224` has dropped to public score `932.8` with `68`
  public episodes.
- It is still before the expected `09:00 JST` submission allowance reset, so no
  new submission was made.
- Latest imported live opponent:
  `meta_agents/cynthia_garchomp_jason_live_85074031_simple`, registered as
  `cynthia_garchomp_jason_live`.
- Rejected after local evidence:
  - `tmp_compare_submissions/greattusk_ionobenchguard`.
  - `tmp_compare_submissions/greattusk_ionotargetguard`.
- First post-reset submission candidate is now:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:22 JST - Current Queue Pointer

- Latest submission `54495224` is `929.8` with `69` public episodes.
- Current time was `05:17 JST`, so no post-reset submission was made.
- Latest imported live opponent:
  `meta_agents/marnie_mykhailo_live_85075581_simple`, registered as
  `marnie_mykhailo_live`.
- First post-reset submission candidate remains:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:12 JST - Great Tusk Queue Candidate After Ketchum Loss

Live state:
- Latest submitted file:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
  on submission `54495224`.
- Current public score: `939.1`.
- Latest refresh at `05:02 JST` still returned `67` episodes, so there was no
  new replay after episode `85072862`.
- It is still before the expected `09:00 JST` submission allowance reset, so no
  new submission was made.

New live loss:
- Episode `85072862`: loss vs `Ketchum Alt`, opponent submission `54500939`,
  opponent initial score `1020.31`.
- Opponent deck extracted as `alakazam_psychic`.
- End state was not the usual empty-bench loss: our active was
  `190:Archaludon ex`, bench count `2`, opponent active was `743:Alakazam`.
- Pattern output:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_endstates_54495224_20260710_0502_v2.csv`.

Updated loss mix:
- `alakazam_psychic`: `14` losses.
- `marnie_grimmsnarl`: `8` losses.
- `mega_lucario`: `4` losses.
- `archaludon_metal`: `2` losses.
- `dragapult`: `2` losses.
- `cynthia_garchomp`: `1` loss.
- `unknown`: `1` loss.

New local agent:
- Added `meta_agents/alakazam_ketchum_alt_live_85072862_simple`.
- Registered as `alakazam_ketchum_alt_live` in
  `tools/run_meta_suite.py` and `tools/aggregate_meta_summaries.py`.

Focused Ketchum Alt check:
- Output:
  `analysis_outputs/post_54495224_ketchum_alt_live_candidate_check_20260710_0458_summary.csv`.
- 48 games:
  - Great Tusk: `0.9375`.
  - current: `0.7500`.
  - strict: `0.6250`.
  - activeguard: `0.5833`.

Expanded recent-live check:
- Output:
  `analysis_outputs/post_54495224_ketchum_expanded_mix_g12_20260710_0507_summary.csv`.
- 14 recent/public-loss buckets, 12 games per seat:
  - Great Tusk: `0.8036`.
  - activeguard: `0.7917`.
  - strict: `0.7708`.
  - current: `0.7500`.
- Loss-weighted by the current submitted agent's loss mix, with Iono weight
  `0`: Great Tusk `0.8514`, activeguard `0.7645`, strict `0.7491`,
  current `0.7310`.
- Same weighting with Iono guard weight `4`: Great Tusk `0.8017`,
  activeguard `0.7867`, strict `0.7730`, current `0.7617`.

Rejected side experiment:
- Created `tmp_compare_submissions/greattusk_ionobenchguard`.
- Goal was to patch Great Tusk's Iono/Bellibolt weakness by recognizing Iono,
  preserving bench, and avoiding Boss/Lisia into powered `269:Bellibolt ex`.
- Focused Iono check worsened from Great Tusk `0.5833` to `0.4375`, so this
  branch is rejected.

Prepared package:
- New queued package:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.
- Package verification:
  root entries are `main.py`, `deck.csv`, `requirements.txt`, `cg/`;
  `deck.csv` has `60` lines; extracted `main.py` compiles.
- Smoke run against `alakazam_ketchum_alt_live` completed with
  `action_errors=0`.

Decision:
- First post-reset candidate is now the queued Great Tusk package above.
- Main risk: Great Tusk is weak into `iono_bellibolt_alghital_live`
  (`0.417` to `0.583` depending seed set), while Archaludon candidates are
  almost perfect into that bucket.
- Rationale: current real losses are dominated by Alakazam and Marnie, and
  Great Tusk is the only tested candidate that clearly improves Ketchum Alt,
  Marnie, and the Victorvv-style Archaludon bucket together.

Submit queue:
1. `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchoocontrolretreat.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`

### 2026-07-10 05:18 JST - Jason Cynthia Loss Added

Live state:
- Current time: `05:12 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submitted file `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
  dropped to public score `932.8`.
- Public episodes increased from `67` to `68`.
- Current leaderboard top-20 cutoff is around `1065.7`, so the current
  submission remains well below gold range.

New live loss:
- Episode `85074031`: loss vs `Jason Lau`, opponent submission `54500711`,
  opponent initial score `836.84`.
- Opponent deck classified as `cynthia_garchomp`.
- End state:
  - Our active: `169:Duraludon`, bench count `1`.
  - Opponent active: `381:Cynthia's Garchomp ex`, one energy attached.
  - Opponent bench: three `342:Cynthia's Roserade`, one `381:Garchomp ex`,
    one `380:Gabite`.
  - Pattern: `opp_wide_board`.
- Updated live loss mix:
  - `alakazam_psychic`: `14`.
  - `marnie_grimmsnarl`: `8`.
  - `mega_lucario`: `4`.
  - `archaludon_metal`: `2`.
  - `cynthia_garchomp`: `2`.
  - `dragapult`: `2`.
  - `unknown`: `1`.

New local agent:
- Added `meta_agents/cynthia_garchomp_jason_live_85074031_simple`.
- Registered as `cynthia_garchomp_jason_live`.
- Added scenario `live_jason_cynthia_2026_07_10`.
- Deck summary:
  `analysis_outputs/deck_cynthia_garchomp_jason_live_85074031_summary.csv`.

Jason Cynthia candidate check:
- Output:
  `analysis_outputs/post_54495224_jason_cynthia_candidate_check_20260710_0514_summary.csv`.
- 48 games:
  - current: `0.9583`.
  - activeguard: `0.9583`.
  - Great Tusk: `0.9583`.
  - strict: `0.9375`.
- This loss does not change the first queue candidate because all major
  candidates are locally strong into this bucket.

Updated loss-weighted check:
- Using the previous 14-bucket `g12` run plus Jason Cynthia weight `2` and
  Iono weight `2`:
  - Great Tusk: `0.8326`.
  - activeguard: `0.7867`.
  - strict: `0.7718`.
  - current: `0.7594`.

Rejected Iono experiment:
- Created `tmp_compare_submissions/greattusk_ionotargetguard`.
- This only penalized Boss/Lisia target selection into `269:Iono's Bellibolt ex`
  and rewarded low-energy Iono basics; it did not change setup or bench rules.
- Focused Iono output:
  `analysis_outputs/post_54495224_gt_ionotarget_iono_g24_20260710_0515_summary.csv`.
- Result:
  - Original Great Tusk: `0.5208`.
  - `gt_ionotarget`: `0.4792`.
  - activeguard: `1.0000`.
- Reject `gt_ionotarget`. Both Iono-specific Great Tusk patches tested so far
  worsened the matchup.

Decision:
- Keep the first post-reset candidate as:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.
- Do not submit before reset.
- After `09:00 JST`, submit this package if the current submission has not
  recovered materially or if the user explicitly asks to submit immediately.

### 2026-07-10 04:45 JST - Cubchoo Control Retreat Candidate

Current Kaggle state:
- Latest submission `54495224` is still `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
- Score check at `04:31 JST`: public score `938.3`, public episodes `63`.
- No new episode after
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0431_episodes.csv`.
- It is still before the expected Kaggle UTC reset (`09:00 JST`), so no new submission was made.

Problem found in the earlier post-reset candidate:
- `cubchooactiveguard` changed matchup detection so any visible Cubchoo could make
  `opp_max_damage` return `10`.
- That is too broad: a mixed deck with Cubchoo could make the agent under-defend.

New candidate:
- Directory:
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchoocontrolretreat`.
- Package:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchoocontrolretreat.tar.gz`.
- SHA256:
  `97E6B1C1CFD9F3F5549D106F12C08AF1FF49C602D0EFD58A832B220FBC15439C`.
- Package root verified: `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
- Extracted package verified: `main.py` compiles and `deck.csv` has 60 lines.

Implementation:
- Keep the current submitted agent as the base.
- Do not add Cubchoo to `detect_matchup`.
- Do not change opponent max damage.
- Add a narrow retreat rule only when:
  - opponent active is Cubchoo,
  - our active is Archaludon ex,
  - we cannot attack now,
  - and Cubchoo-control evidence is visible:
    multiple Cubchoo, Dunsparce/Dudunsparce, Enhanced Hammer, Crushing Hammer,
    Gravity Gemstone, Xerosic, or Nighttime Mine.

Local evidence:
- Recent live focus:
  `analysis_outputs/post_54495224_cubchoostrict_recent_live_g12_20260710_0438_summary.csv`.
  - `current`: equal buckets `0.7273`.
  - `retreatonly`: equal buckets `0.7386`.
  - `strict`: equal buckets `0.7614`.
  - Cubchoo Senkin13 bucket: current `0.3333`, strict `0.7083`.
  - Iono Alghital bucket: current `1.0000`, strict `1.0000`.
  - Hamu Lucario bucket: current `0.8333`, strict `1.0000`.
  - Rojiomote Dragapult bucket: current `1.0000`, strict `0.9167`.
- Broad 2026-07-08 top sample:
  `analysis_outputs/post_54495224_cubchoostrict_public0708_g8_20260710_0439_summary.csv`.
  - `current`: public sample `0.8594`.
  - `strict`: public sample `0.8156`.
  - The broad sample has no Cubchoo in the inspected Starmie/Ogerpon decks, so
    this difference is treated as local battle variance rather than a causal
    branch effect. The strict branch should only fire on visible Cubchoo-control
    boards.

Decision:
- Replace the first post-reset queue item with the strict Cubchoo-control retreat
  package. It keeps the Cubchoo fix without the broad `opp_max_damage` side
  effect from `cubchooactiveguard`.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchoocontrolretreat.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
3. `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`

### 2026-07-10 04:28 JST - Current Score and Old 947 Check

Live state:
- Current time was `04:22 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submission `54495224` is `938.3`.
- Public episodes remain `63`; the only new episode since the 62-episode
  snapshot was the `85067649` win vs Alghital Iono/Bellibolt.
- Current top 20 leaderboard score range is roughly `1059.4` to `1307.3`, so
  the current submission is still outside the target gold range.

Public dataset check:
- Refreshed `kaggle/pokemon-tcg-ai-battle-episodes-index`.
- The latest public daily episode dataset is still `2026-07-08`; no
  `2026-07-09` manifest entry is available yet.

Old public-best comparison:
- Rechecked the old `947.0` public-score package:
  `submission_archaludon_ogerboss_nonex2_cut1fml1relicanth_mirrorstretcher_energy12_cutice_archbossrelic_safe_alakline3_chandlillie7_deck25_ogerexactive_cornerdetect_chandlowdecklillie`.
- Output:
  `analysis_outputs/post_54495224_activeguard_vs_old947_20260710_0424_summary.csv`.
- Recent live + 2026-07-08 Alakazam/Marnie focus, 4 games per seat:
  - `activeguard`: equal buckets `0.8359`.
  - `old947`: equal buckets `0.7344`.
  - 2026-07-08 top20 subset: `activeguard` `0.8393`, `old947` `0.7857`.
  - Cubchoo/Senkin: `activeguard` `0.875`, `old947` `0.375`.
- The old public-best candidate is better on a few isolated buckets, but is
  worse on the current Cubchoo and several Alakazam buckets.

Decision:
- Keep `cubchooactiveguard` first in the post-reset queue.

### 2026-07-10 04:32 JST - Great Tusk Alternate Deck Probe

Candidate:
- Directory:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr`.
- This is a representative late Great Tusk/Crustle/Starmie-rush branch.
- It compiles and has a 60-card deck.

Recent live + Alakazam/Marnie/Iono focus:
- Output:
  `analysis_outputs/post_54495224_activeguard_vs_gtstarmie_20260710_0427_summary.csv`.
- Result:
  - `activeguard`: equal buckets `0.8281`.
  - `greattusk_starmierush`: equal buckets `0.8438`.
- Great Tusk looked stronger into Alakazam/Marnie, but much weaker into
  Alghital Iono (`0.25`) and Rojiomote Dragapult (`0.50`).

Full 2026-07-08 top sample:
- Output:
  `analysis_outputs/post_54495224_activeguard_vs_gtstarmie_public0708_full_20260710_0429_summary.csv`.
- Result:
  - `activeguard`: `public_sample_2026_07_08_top20` `0.8562`,
    equal buckets `0.8750`.
  - `greattusk_starmierush`: `public_sample_2026_07_08_top20` `0.8438`,
    equal buckets `0.8333`.
- Great Tusk was better into Alakazam/Chandelure/Ogerpon but worse into
  Starmie, Great Tusk mirrors, some Marnie, and Dragapult.

Decision:
- Keep the Great Tusk branch as a future alternate-deck track, not the next
  post-reset submission.
- `cubchooactiveguard` remains first because it is more balanced on the full
  2026-07-08 top sample and current live Iono/Dragapult checks.

### 2026-07-10 04:35 JST - Marnie Alternate Deck Probe Rejected

Candidate:
- Directory:
  `submission_marnie_variant_kazuki_boss2_xerosic1_rules`.
- It compiles and has a 60-card deck.

Local evidence:
- Output:
  `analysis_outputs/post_54495224_activeguard_vs_marniexerosic_20260710_0430_summary.csv`.
- Recent/current meta focus, 4 games per seat:
  - `activeguard`: equal buckets `0.7917`.
  - `marnie_xerosic`: equal buckets `0.4792`.
  - 2026-07-08 top20 subset: `activeguard` `0.8409`,
    `marnie_xerosic` `0.3864`.
- `marnie_xerosic` was competitive into some Alakazam and strong into
  Rojiomote Dragapult, but failed badly into:
  - `archaludon_victorvv_live`: `0/8`.
  - `great_tusk_liamk_2026_07_08`: `0/8`.
  - `great_tusk_bono_junlee_2026_07_08`: `0/8`.
  - `ogerpon_btk15049_2026_07_08`: `0/8`.

Decision:
- Reject Marnie as a near-term alternate submission deck.
- Continue treating Great Tusk as the more plausible future alternate deck
  track, while keeping `cubchooactiveguard` as the immediate post-reset
  submission candidate.

### 2026-07-10 04:25 JST - One New Win and Iono Meta Import

Live state:
- Current time was `04:19 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submission `54495224` rose slightly from `933.6` to `938.3`.
- Public episodes increased from `62` to `63`.

New public episode:
- Episode `85067649`, public win vs `Alghital`.
- Opponent initial score: `925.8`.
- Opponent deck from replay:
  - Iono's Voltorb/Tadbulb/Bellibolt ex/Wattrel/Kilowattrel.
  - 22 Lightning Energy.
  - Canari, Levincia, Lillie, Ultra Ball, Poke Pad, Night Stretcher.
- Endgame: Archaludon ex used Boss and Metal Defender to close the game.

Meta updates:
- Added `iono_bellibolt` archetype marker to
  `tools/extract_episode_decks.py`.
- Re-extracting `85067649` now classifies Alghital as `iono_bellibolt`
  instead of `unknown`.
- Added local opponent:
  `meta_agents/iono_bellibolt_alghital_live_85067649_simple`.
- Registered it in `tools/run_meta_suite.py` as
  `iono_bellibolt_alghital_live` and scenario
  `live_alghital_iono_2026_07_10`.
- Synced `tools/aggregate_meta_summaries.py` with the recent live buckets and
  the new Iono bucket.

Verification:
- `tools/extract_episode_decks.py`, `tools/run_meta_suite.py`,
  `tools/aggregate_meta_summaries.py`, and
  `tools/summarize_kaggle_loss_endstates.py` compile.
- New Iono deck has 60 cards.
- Smoke local suite:
  `analysis_outputs/post_54495224_iono_alghital_smoke_20260710_0421_summary.csv`.
- `activeguard` vs `iono_bellibolt_alghital_live`: `4/4`.

Decision:
- This new episode is a useful meta addition but not a reason to change the
  next submission candidate.
- Keep `cubchooactiveguard` first in the post-reset queue.

### 2026-07-10 04:20 JST - Kaggle Loss End-State Triage Added

Live state:
- Current time is `04:15 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submission `54495224` remains `COMPLETE` with public score `933.6`.
- Public episode refresh still returned `62` episodes.

Tooling:
- Added `tools/summarize_kaggle_loss_endstates.py`.
- It joins a Kaggle submission episode CSV, extracted replay deck archetypes,
  and replay JSON files, then writes one row per public loss with final board
  state, active/bench line count, opponent board width, last select context,
  and simple loss-pattern tags.
- Latest output:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_endstates_54495224_20260710_0416.csv`.

End-state evidence from 30 public losses:
- By archetype:
  - `alakazam_psychic`: `13` losses; `8` with empty bench, `8` with thin
    Archaludon line, `11` vs wide opponent board.
  - `marnie_grimmsnarl`: `8` losses; `4` with empty bench, `5` with thin
    Archaludon line, `6` vs wide opponent board.
  - `okidogi_barbaracle`: `3` losses; all three ended with empty bench and
    thin line.
  - `dragapult`: `2` losses; both ended with empty bench and thin line.
- Common patterns:
  - `empty_bench;thin_archaludon_line;opp_wide_board`: `11` losses.
  - `empty_bench;thin_archaludon_line`: `6` losses.
  - `low_hp_line_active;opp_wide_board`: `4` losses.
- Alakazam/Marnie losses usually ended without Hero's Cape on the active:
  - Alakazam: `11/13` losses had active tools `0`.
  - Marnie: `6/8` losses had active tools `0`.

Rejected probe: `alakthinlillie`
- Directory:
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard_alakthinlillie`.
- Change:
  - Only vs Alakazam, if the board is thin and hand is small, play Lillie
    before attacking to dig for Hero's Cape or a backup line.
- Replay inspection:
  - On `85046024`, the candidate changed the late decision from attacking
    immediately to `Alakazam: Lillie for Cape/backup`, so the intended branch
    fires.
- Output:
  `analysis_outputs/post_54495224_alakthinlillie_focus_20260710_0418_summary.csv`.
- Result on Alakazam-heavy/recent-loss focus, 4 games per seat:
  - `activeguard`: equal buckets `0.7708`.
  - `alakthinlillie`: equal buckets `0.7396`.
  - 2026-07-08 top20 subset: `activeguard` `0.950`,
    `alakthinlillie` `0.550`.
  - `cubchoo_senkin13_live`: `activeguard` `0.625`,
    `alakthinlillie` `0.250`.
- Rejected. The idea helps some old live Alakazam/Marnie buckets but breaks
  too much of the newer top-sample Alakazam/Cubchoo mix.

Decision:
- Keep `cubchooactiveguard` as the first post-reset submission candidate.
- Current evidence says the next successful Alakazam/Marnie improvement must
  be more specific than generic backup/Cape digging. The broad pattern is real,
  but direct draw/bench-priority fixes overfit and regress.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 04:17 JST - Backup Bench Probes Rejected

Live state:
- Current time is `04:10 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submission `54495224` remains `COMPLETE` with public score `933.6`.
- Public episode refresh still returned `62` episodes.

Rejected probe: `marniebackup`
- Directory:
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard_marniebackup`.
- Changes:
  - Added Marnie line detection `{646, 647, 648}`.
  - Raised Marnie expected damage and Ice Cream threshold.
  - Raised Duraludon bench priority when board depth is low vs Alakazam/Marnie.
- Output:
  `analysis_outputs/post_54495224_marniebackup_focus_20260710_0412_summary.csv`.
- Result on 12 recent-loss/live buckets, 4 games per seat:
  - `activeguard`: equal buckets `0.8542`.
  - `marniebackup`: equal buckets `0.8021`.
- Rejected because Marnie Kei/Ysakuragi, Cubchoo, Dragapult and multiple
  Alakazam buckets regressed. The Marnie-specific detection changed too much
  for too little gain.

Rejected probe: `alakbenchfirst`
- Directory:
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard_alakbenchfirst`.
- Change:
  - Only vs Alakazam, play Duraludon before generic item play when bench depth
    is low.
- Output:
  `analysis_outputs/post_54495224_alakbenchfirst_focus_20260710_0415_summary.csv`.
- Result on Alakazam-heavy/recent-loss focus, 4 games per seat:
  - `activeguard`: equal buckets `0.7917`.
  - `alakbenchfirst`: equal buckets `0.7396`.
  - `public_sample_2026_07_08_top20` subset: `activeguard` `0.775`,
    `alakbenchfirst` `0.700`.
- Rejected because the earlier Duraludon bench sequencing worsened more
  buckets than it helped, including Cubchoo.

Decision:
- Keep `cubchooactiveguard` as the first post-reset submission candidate.
- The next meaningful Alakazam/Marnie work should inspect decision traces from
  losses before changing generic board-depth rules. Blindly increasing backup
  priority is not supported by local evidence.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 04:10 JST - Activeguard Still First After Live-Loss Focus

Live state:
- Current time is `04:07 JST`, still before the expected `09:00 JST`
  submission allowance reset.
- Latest submission `54495224` remains `COMPLETE` with public score `933.6`.
- Public episode refresh still returned `62` episodes; no new public replay was
  available after the `Hamu.py` and `Rojiomote` losses.

Replay/deck triage:
- Saved replays for the latest submission under
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard`.
- Extracted deck archetypes to
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/all_replay_decks_20260710_0408`.
- Public loss distribution by opponent archetype:
  - `alakazam_psychic`: `13L / 5W`, average opponent score `996.9`.
  - `marnie_grimmsnarl`: `8L / 4W`, average opponent score `987.2`.
  - `okidogi_barbaracle`: `3L / 2W`, average opponent score `945.1`.
  - `dragapult`: `2L / 1W`, average opponent score `963.9`.
  - `archaludon_metal`: `2L / 8W`.
- The late score decline is mainly from stronger Alakazam/Marnie opponents,
  plus the Cubchoo/Senkin lock replay.
- Decision inspection examples:
  - `85056873` vs matsurih Alakazam: late board was active non-ex
    Archaludon with no bench until turn 8; Duraludon was fetched and benched
    only at the end, then Alakazam closed the game. This points to backup
    bench timing, not a Cubchoo-specific issue.
  - `85050361` vs ysakuragi Marnie: active Archaludon ex took the active KO
    while saving Boss (`save Boss: can KO Active`), but the board was still
    thin and lost on the reply. This points to board depth and Boss timing as
    the next Marnie-side analysis target.

Candidate checks:
- `ogerbenchdura` was created to prefer Duraludon over non-ex Archaludon when
  Cornerstone Ogerpon is visible and our bench is empty.
- It improved one Ogerpon-focused weak run, but regressed on the wider
  2026-07-08 public top sample:
  `activeguard` `0.8625` vs `ogerbenchdura` `0.7750`.
- Reject `ogerbenchdura`; do not package or submit it.

Focused local evidence:
- Output:
  `analysis_outputs/post_54495224_activeguard_live_losses_focus_20260710_0409_summary.csv`.
- Recent-loss focus, 12 live buckets, 4 games per seat:
  - `activeguard`: equal buckets `0.7917`.
  - current latest submission: equal buckets `0.6875`.
- Important bucket deltas:
  - `cubchoo_senkin13_live`: current `0.125`, `activeguard` `0.750`.
  - `alakazam_kusui_live`: current `0.375`, `activeguard` `0.750`.
  - `alakazam_ant_live`: current `0.500`, `activeguard` `0.625`.
  - `marnie_shishio_live`: current `0.500`, `activeguard` `0.625`.

Decision:
- Keep `cubchooactiveguard` as the first post-reset submission candidate.
- Do not submit before `09:00 JST`. Recheck the latest score/episodes/quota
  after reset; if the current public score has not recovered materially,
  submit `cubchooactiveguard`.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 04:00 JST - 2026-07-08 Public Top Sample Added

Live state:
- Current time is still before the expected `09:00 JST` submission allowance
  reset.
- Latest submission `54495224` remains `COMPLETE` with public score `933.6`.
- Public episode refresh still returned `62` episodes.

Public data refresh:
- Downloaded the latest Kaggle daily top episode sample with
  `tools/download_episode_samples.py`.
- The manifest now reaches `2026-07-08`; downloaded 20 replay JSON files from
  `pokemon-tcg-ai-battle-episodes-2026-07-08` into
  `data/episodes_refresh_20260710_0355/2026-07-08-sample`.
- Extracted decks to:
  - `analysis_outputs/episode_decks_2026_07_08_sample20`
  - `analysis_outputs/episode_decks_2026_07_08_sample20_v2`
- Added marker support in `tools/extract_episode_decks.py` for:
  - `okidogi_barbaracle`
  - `cynthia_garchomp`

Updated 2026-07-08 archetype snapshot after marker refresh:
- `alakazam_psychic`: `10` decks.
- `great_tusk_crustle`: `8` decks.
- `marnie_grimmsnarl`: `6` decks.
- `okidogi_barbaracle`: `5` decks.
- `chandelure_psychic_control`: `3` decks.
- `starmie_froslass`: `3` decks.
- Singletons: `dragapult`, `archaludon_metal`,
  `rocket_mewtwo_spidops`, `cynthia_garchomp`, `ogerpon_toolbox`.

New local meta agents:
- Added 15 deck-swapped simple agents under `meta_agents/` from winning
  `2026-07-08` public top episodes:
  - `alakazam_majkel1337_84743025_simple`
  - `alakazam_third_ptcg_84743063_simple`
  - `alakazam_55_84743065_simple`
  - `great_tusk_liamk_84743031_simple`
  - `great_tusk_bono_junlee_84743036_simple`
  - `marnie_yushin_84743048_simple`
  - `marnie_gonsaku_84743055_simple`
  - `starmie_windecks_84743054_simple`
  - `starmie_yushin_84743057_simple`
  - `dragapult_bigbug_84743038_simple`
  - `ogerpon_btk15049_84743052_simple`
  - `ogerpon_zoroark190_84743095_simple`
  - `okidogi_majkel1337_84743042_simple`
  - `chandelure_koga_84743037_simple`
  - `chandelure_starmine_84743078_simple`
- Registered them in `tools/run_meta_suite.py`.
- Added `public_sample_2026_07_08_top20` weighted scenario:
  - Majkel/Matsurih/Rmy style Alakazam: weight `3`.
  - Third PTCG Alakazam: `1`.
  - 5.5 Alakazam: `1`.
  - LiamK Great Tusk/Crustle: `1`.
  - bono/junlee Great Tusk/Crustle: `3`.
  - Yushin Marnie: `1`.
  - Gonsaku Marnie: `1`.
  - koga Chandelure: `1`.
  - Star-mine Chandelure: `1`.
  - Majkel Okidogi/Barbaracle: `2`.
  - BigBugginnings Dragapult: `1`.
  - btk15049 Ogerpon: `1`.
  - zoroark190 Ogerpon: `1`.
  - WinDecks Starmie: `1`.
  - Yushin Starmie: `1`.

Verification:
- `tools/run_meta_suite.py`, `tools/aggregate_meta_summaries.py`, and
  `tools/extract_episode_decks.py` compile.
- All 15 new local agents compile and have 60-card `deck.csv` files.

Local evidence on the new 2026-07-08 scenario:
- Output:
  `analysis_outputs/post_54495224_public0708_g2_20260710_0359_summary.csv`.
- `public_sample_2026_07_08_top20`:
  - `activeguard`: `0.9000`.
  - current: `0.8500`.
  - `relic_fml_boss`: `0.8250`.
  - `victorvv_cubchooactiveguard`: `0.7750`.
- Equal over the 15 new buckets:
  - current and `activeguard`: `0.8667`.
  - `relic_fml_boss`: `0.8000`.
  - `victorvv_cubchooactiveguard`: `0.7667`.

Decision:
- The latest public top sample supports keeping `cubchooactiveguard` as the
  first post-reset submission candidate.
- Do not submit yet; current time is `04:00 JST`, still before the expected
  reset.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 03:54 JST - Victorvv Cubchoo Hybrid Rejected

Live state:
- Current time is still before the expected `09:00 JST` submission allowance
  reset.
- Latest submission `54495224` remains `COMPLETE` with public score `933.6`.
- Public episode refresh still returned `62` episodes, so there is no new
  replay after the `Hamu.py` Lucario and `Rojiomote` Dragapult losses.

Experiment:
- Created
  `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_victorvvdeck_cubchooactiveguard`.
- This applies the narrow Cubchoo active-lock retreat rule to the `victorvv`
  deck/rules branch, without the `nonexwall2` deck edits.
- Initial replay inspection surfaced a migration bug:
  `active_pokemon(obs, 1)` and `legal_options(obs)` do not exist in this branch.
  Fixed the branch to use `opp_active_pokemon(obs)` and
  `obs.select.option`.
- Replay inspection on `85057952` now shows `Cubchoo: retreat to clear attack
  lock` in the locked positions.

Focused local evidence:
- Output:
  `analysis_outputs/post_54495224_victorvv_activeguard_focus_20260710_0352_summary.csv`.
- Recent-loss focus, 12 buckets, 4 games per seat:
  - `victorvv_cubchooactiveguard`: equal buckets `0.7812`.
  - `activeguard`: equal buckets `0.7708`.
  - `victorvv`: equal buckets `0.7292`.
  - `current`: equal buckets `0.6875`.
- The hybrid improved the focused mirror/Cubchoo mix, but showed an Ogerpon
  warning: `ogerpon` bucket `0.125` vs `activeguard` `0.750`.

Broad regression check:
- Output:
  `analysis_outputs/post_54495224_victorvv_cubchoo_broad_20260710_0353_summary.csv`.
- All registered meta buckets, 2 games per seat:
  - Equal buckets: `activeguard` `0.8808`, hybrid `0.8269`.
  - `public_sample_2026_07_03_top20`: `activeguard` `0.9079`, hybrid `0.7500`.
  - `public_sample_2026_07_02_top20`: `activeguard` `0.9187`, hybrid `0.7375`.
  - Ogerpon toolbox: `activeguard` `0.9038`, hybrid `0.6923`.
  - Cubchoo live bucket: `activeguard` `1.0000`, hybrid `0.5000`.

Decision:
- Reject `victorvv_cubchooactiveguard` for now. The focused live-loss result
  is interesting, but the broad/top20/Ogerpon regression is too large.
- Keep `cubchooactiveguard` as the first post-reset submission candidate.

Submit queue:
1. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`
2. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_alaknonex_nozonecage_relicfml4_cutenergyboss.tar.gz`
3. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck_nonexwall2.tar.gz`
4. `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_nozone_victorvvdeck.tar.gz`

### 2026-07-10 04:22 JST - Current Queue Pointer

- Latest submission `54495224` is still `933.6` with `62` public episodes.
- Current time was `04:15 JST`, so no post-reset submission was made.
- New loss end-state tool:
  `tools/summarize_kaggle_loss_endstates.py`.
- Latest loss end-state output:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_endstates_54495224_20260710_0416.csv`.
- Rejected after local evidence:
  - `marniebackup`.
  - `alakbenchfirst`.
  - `alakthinlillie`.
- First post-reset submission candidate remains:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_cubchooactiveguard.tar.gz`.

### 2026-07-10 05:22 JST - Mykhailo Marnie Loss Added

- Latest submission `54495224` has dropped to public score `929.8` with `69`
  public episodes.
- New loss episode `85075581` was vs `Mykhailo Kalus`, a
  `marnie_grimmsnarl` deck, opponent initial score `1030.35`.
- End state was another low-board loss:
  `169:Duraludon` active, bench count `0`, against
  `648:Marnie's Grimmsnarl ex`.
- Added `meta_agents/marnie_mykhailo_live_85075581_simple`, registered as
  `marnie_mykhailo_live` with scenario
  `live_mykhailo_marnie_2026_07_10`.
- Focused 48-game check vs Mykhailo Marnie:
  current `0.9167`, activeguard `0.8750`, Great Tusk `0.8542`,
  strict `0.8125`.
- Updated loss-weighted check including Jason Cynthia and Mykhailo Marnie:
  Great Tusk `0.8309`, activeguard `0.7938`, current `0.7788`,
  strict `0.7776`.
- First post-reset submission candidate remains:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:16 JST - Current Queue Pointer

- Latest submission `54495224` has dropped to public score `932.8` with `68`
  public episodes.
- It is still before the expected `09:00 JST` submission allowance reset, so no
  new submission was made.
- Latest imported live opponent:
  `meta_agents/cynthia_garchomp_jason_live_85074031_simple`, registered as
  `cynthia_garchomp_jason_live`.
- Rejected after local evidence:
  - `tmp_compare_submissions/greattusk_ionobenchguard`.
  - `tmp_compare_submissions/greattusk_ionotargetguard`.
- First post-reset submission candidate is now:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:26 JST - Iono No-Wall Great Tusk Probe

- Current time remained before the `09:00 JST` reset; no submission was made.
- Created `tmp_compare_submissions/greattusk_iononowall`.
- Change: recognize `iono_bellibolt` and disable Great Tusk's Crustle wall
  mode only for that matchup.
- Focused Iono check:
  `analysis_outputs/post_54495224_gt_iononowall_iono_g24_20260710_0523_summary.csv`.
  - Original Great Tusk: `0.5625`.
  - `gt_iononowall`: `0.6875`.
  - activeguard: `1.0000`.
- Recent broad mix:
  `analysis_outputs/post_54495224_gt_iononowall_recent_mix_g6_20260710_0523_summary.csv`.
  - Original Great Tusk: `0.8646` equal buckets.
  - `gt_iononowall`: `0.8542` equal buckets.
  - activeguard: `0.8021` equal buckets.
- Loss-weighted on the current live-loss mix:
  - Original Great Tusk: `0.8755`.
  - `gt_iononowall`: `0.8707`.
  - activeguard: `0.7951`.
- Decision: do not replace the first queue candidate. Keep original Great Tusk
  first because it remains slightly stronger overall. Keep no-wall as a backup
  if live Great Tusk later loses specifically to Iono/Bellibolt.
- Backup package prepared and verified:
  `submission_great_tusk_crustle_iononowall_20260710_backup.tar.gz`.
- First post-reset submission candidate remains:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:31 JST - First Queue Switched To Iono No-Wall

- Still before the `09:00 JST` reset; no Kaggle submission was made.
- Ran a thicker 16-bucket check:
  `analysis_outputs/post_54495224_gt_iononowall_recent_mix_g12_20260710_0526_summary.csv`.
- Equal buckets:
  - Original Great Tusk: `0.8177`.
  - Iono no-wall: `0.8151`.
  - activeguard: `0.7500`.
- Current live-loss weighted score:
  - Iono no-wall: `0.8346`.
  - Original Great Tusk: `0.8320`.
  - activeguard: `0.7358`.
- Key tradeoff:
  - Iono/Bellibolt improves from `0.5833` to `0.7500`.
  - The broad average is almost unchanged.
  - Since the post-reset submission is intended to handle live uncertainty, the
    Iono hedge is worth the tiny broad-average cost.
- Package smoke checks:
  - Root entries are `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
  - `deck.csv` has `60` cards.
  - Extracted `main.py` compiles.
  - Smoke games vs `alakazam_ketchum_alt_live` and
    `iono_bellibolt_alghital_live` completed with `action_errors=0`.
- New first post-reset submission candidate:
  `submission_great_tusk_crustle_iononowall_20260710_queue.tar.gz`.
- Previous first candidate is now second:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:34 JST - Iono No-Wall Broad Regression Check

- Current time was `05:30 JST`; still before reset, so no Kaggle submission was
  made.
- Kaggle state stayed unchanged: submission `54495224`, score `929.8`,
  `69` public episodes.
- All-registered-meta light check:
  `analysis_outputs/post_54495224_gt_iononowall_allmeta_g2_20260710_0531_summary.csv`.
  - Equal buckets: Iono no-wall `0.7907`, original Great Tusk `0.7529`.
  - `public_sample_2026_07_08_top20`: Iono no-wall `0.8625`, original Great
    Tusk `0.7875`.
  - `public_sample_2026_07_03_top20`: Iono no-wall `0.9013`, original Great
    Tusk `0.6645`.
- Focused follow-up on largest apparent regressions:
  `analysis_outputs/post_54495224_gt_iononowall_worstdelta_g16_20260710_0532_summary.csv`.
  - Equal buckets on those eight opponents: original Great Tusk `0.7148`,
    Iono no-wall `0.7031`.
  - Confirmed real regression: `ogerpon_cornerstone`, `0.562` -> `0.281`.
  - Apparent regressions on `alakazam_55_live` and
    `dragapult_rojiomote_live` did not hold up; Iono no-wall was slightly
    better after more games.
- Decision:
  - Keep Iono no-wall as first queue candidate because it improves Iono and
    broad top-sample checks, while the confirmed regression is mostly on a
    lower-weight Ogerpon corner bucket.
  - Keep original Great Tusk as second queue candidate if live losses show the
    no-wall branch is punished by Ogerpon/Cornerstone.
- First post-reset submission candidate remains:
  `submission_great_tusk_crustle_iononowall_20260710_queue.tar.gz`.
- Second candidate:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:38 JST - No-Wall Diff Sanity Check

- Current time was still before reset; no Kaggle submission was made.
- Source diff between original Great Tusk and Iono no-wall is intentionally
  narrow:
  - add `IONO_BELLIBOLT_IDS`.
  - add `facing_iono_bellibolt`.
  - return `False` from `should_wall_mode` only when Iono/Bellibolt markers are
    visible.
- `deck.csv` is identical between the two candidates.
- Non-Iono local results can still differ between runs. The local runner seeds
  Python `random`, but the bundled game engine has its own state/variance, so
  small local deltas on non-Iono buckets should be treated as sampling noise
  unless they persist over thicker checks.
- This supports keeping Iono no-wall first: the code risk is narrow, while the
  observed benefit is in the intended Iono/Bellibolt bucket.

### 2026-07-10 05:44 JST - Pre-Reset Submission Readiness Check

- Current time was `05:39 JST`, still before the expected `09:00 JST` Kaggle
  allowance reset; no submission was made.
- Kaggle `ListEpisodes` for latest submission `54495224` still returned `69`
  public episodes:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0540_episodes.csv`.
- Queue package verification:
  - `submission_great_tusk_crustle_iononowall_20260710_queue.tar.gz`
    SHA256 `62E7A3811A9D60B38CFFA172CAEA6790B9E39B856DF74E0C860FF20434D40760`.
  - `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`
    SHA256 `9BAE212FDAABF2C4BD6AC7D164DED4D8227284A72A30E934B909EC5CDE395367`.
  - Both packages have root `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
  - Both `deck.csv` files have `60` lines.
  - Both extracted `main.py` files compile with Python 3.9 syntax check.
- Local runtime note: Windows `python` points to Python `3.9.13`, while
  `py -3` points to Python `3.11.6`. Local battle checks should use `py -3`
  because the agents use `type | None` annotations that fail under Python 3.9.
- First candidate smoke:
  `analysis_outputs/post_54495224_gt_iononowall_smoke_20260710_0543.csv`.
  - `gt_iononowall` vs `alakazam_ketchum_alt_live` and
    `iono_bellibolt_alghital_live`, both seats, completed with `errors=0`.
- First post-reset submission candidate remains:
  `submission_great_tusk_crustle_iononowall_20260710_queue.tar.gz`.
- Second candidate remains:
  `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:45 JST - Queue Candidate Live-Risk Recheck

- Current time was `05:40 JST`; no submission was made.
- Kaggle `ListEpisodes` for submission `54495224` still returned `69` public
  episodes:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0541_episodes.csv`.
- Ran a short live-risk comparison:
  `analysis_outputs/post_54495224_gt_queue_live_risk_g6_20260710_0542.csv`.
- Seat-combined results:
  - `marnie_mykhailo_live`: both candidates `10/12`.
  - `alakazam_ketchum_alt_live`: Iono no-wall `11/12`, original `9/12`.
  - `cynthia_garchomp_jason_live`: Iono no-wall `12/12`, original `11/12`.
  - `iono_bellibolt_alghital_live`: Iono no-wall `7/12`, original `8/12`
    in this short run, contrary to earlier thicker Iono-only evidence.
  - `ogerpon_cornerstone`: Iono no-wall `4/12`, original `7/12`.
- Decision:
  - Keep Iono no-wall first because the latest live-loss mix still contains no
    Ogerpon and it remains stronger on the three newly imported live opponents.
  - Switch to the original Great Tusk candidate if the first post-reset
    submission loses to Ogerpon/Cornerstone or the live field starts showing
    that bucket.

### 2026-07-10 05:50 JST - Iono No-Wall Detection Patch

- Still before the expected `09:00 JST` reset; no Kaggle submission was made.
- Card-catalog check showed current Iono no-wall IDs were all Iono-specific:
  - `265`: Iono's Voltorb.
  - `268`: Iono's Tadbulb.
  - `269`: Iono's Bellibolt ex.
  - `270`: Iono's Wattrel.
  - `271`: Iono's Kilowattrel.
- No overlap with Ogerpon/Cornerstone markers, so Ogerpon regression is likely
  local variance rather than false Iono detection.
- Added missing Iono-specific marker:
  - `266`: Iono's Electrode.
- New package prepared:
  `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`.
- SHA256:
  `8AFDB5C54816B532832A6D5A0C7466FF3CC503D363ED8CFC506A9EE14ADFB4D6`.
- Package verification:
  - Root entries include `main.py`, `deck.csv`, `requirements.txt`, `cg/`.
  - `deck.csv` has `60` lines.
  - Extracted `main.py` compiles with `py -3`.
- Short live-risk check:
  `analysis_outputs/post_54495224_gt_iononowall266_live_risk_g4_20260710_0548.csv`.
  - `gt_iononowall266`: `34/40`, `errors=0`.
  - `gt_original`: `30/40`, `errors=0`.
  - `gt_iononowall266` was better on Ketchum Alakazam, Jason Cynthia,
    Mykhailo Marnie, and Iono/Bellibolt; original remained slightly safer on
    Ogerpon Cornerstone.
- New first post-reset submission candidate:
  `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`.
- Backup candidates:
  1. `submission_great_tusk_crustle_iononowall_20260710_queue.tar.gz`.
  2. `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 05:56 JST - Pre-Reset Meta Coverage Check

- Current time remained before reset (`05:44 JST` during this pass); no Kaggle
  submission was made.
- Latest Kaggle submissions table was unchanged:
  - latest submission file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - score `929.8`.
- Re-extracted the local `2026-07-08` top sample:
  `analysis_outputs/episode_decks/refresh_20260710_0451_top20`.
- Archetype mix from that sample:
  - `alakazam_psychic`: `10`.
  - `great_tusk_crustle`: `8`.
  - `marnie_grimmsnarl`: `6`.
  - `chandelure_psychic_control`: `3`.
  - `starmie_froslass`: `3`.
  - `okidogi_barbaracle`: `3`.
  - `mega_lucario`: `2`.
  - singletons: `dragapult`, `archaludon_metal`,
    `rocket_mewtwo_spidops`, `cynthia_garchomp`, `ogerpon_toolbox`.
- Okidogi/BKT local check:
  `analysis_outputs/post_54495224_gt_iononowall266_okidogi_btk_g12_20260710_0546.csv`.
  - `gt_iononowall266`: `43/48`, `errors=0`.
  - `gt_original`: `45/48`, `errors=0`.
  - Both are acceptable; original is slightly safer on this slice.
- Full registered `2026-07-08` top20 thin check:
  `analysis_outputs/post_54495224_gt_iononowall266_0708top20_g4_20260710_0548.csv`.
  - `gt_iononowall266`: `93/120` (`0.775`), `errors=0`.
  - `gt_original`: `98/120` (`0.8187`), `errors=0`.
- Follow-up representative non-Iono check with `--fair-seeds`:
  `analysis_outputs/post_54495224_gt_iononowall266_noniono_fair_g8_20260710_0550.csv`.
  - Non-Iono result deltas still did not align exactly despite identical
    intended branch behavior outside Iono/Bellibolt.
  - The bundled Python wrapper exposes `BattleStart(deck0, deck1)` without a
    seed parameter, while the C++ source has native RNG/config seed logic.
  - Treat small non-Iono candidate deltas as native shuffle variance unless
    they are large and repeated across thicker runs.
- Classification tool update:
  - Added `266` to the `iono_bellibolt` marker set in
    `tools/extract_episode_decks.py`.
- Queue decision unchanged:
  - First: `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`.
  - Fallback if live Ogerpon/Cornerstone or broad top-sample losses dominate:
    `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.

### 2026-07-10 06:04 JST - Starmie Weakness Probe

- Current time was `05:48 JST`; still before reset, so no Kaggle submission was
  made.
- Latest Kaggle state stayed unchanged:
  - submission `54495224`.
  - score `929.8`.
  - `69` public episodes:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0558_episodes.csv`.
- Generated Starmie trace sample:
  - results:
    `analysis_outputs/post_54495224_gt_iononowall266_starmie_yushin_trace_20260710_0559.csv`.
  - per-game:
    `analysis_outputs/post_54495224_gt_iononowall266_starmie_yushin_trace_games_20260710_0559.csv`.
  - trace summary:
    `analysis_outputs/summary_starmie_yushin_gt_iononowall266_traces_20260710_0559.csv`.
- Loss pattern:
  - Starmie wins by clearing Great Tusk/Crustle from board before the mill plan
    finishes.
  - Mega Starmie ex repeatedly uses `Jetting Blow` and `Nebula Beam`; some
    games also involve Cinderace `Turbo Flare`.
  - This is not primarily a Kaggle/latest-live loss driver yet; it is a
    2026-07-08 top-sample risk.
- Tested `tmp_compare_submissions/greattusk_iononowall266_starmiefix`:
  - change: make `facing_starmie()` return real visible Starmie detection.
  - output:
    `analysis_outputs/post_54495224_gt_starmiefix_starmie_g12_20260710_0601.csv`.
  - result: worse than `gt_iononowall266` on both tested Starmie buckets.
  - rejected.
- Tested `tmp_compare_submissions/greattusk_iononowall266_starmiestretcher`:
  - change: keep `facing_starmie()` disabled, but prioritize `Night Stretcher`
    when the Starmie package is visible and Great Tusk is depleted.
  - output:
    `analysis_outputs/post_54495224_gt_starmiestretcher_starmie_g12_20260710_0603.csv`.
  - result: mixed and no aggregate improvement.
  - rejected.
- Queue decision unchanged:
  - First: `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`.
  - Keep Starmie as a known local weakness, but do not let it override the
    current live-loss-oriented queue unless live losses start showing Starmie.

### 2026-07-10 06:30 JST - Latest Live Replay Loss Triage

- Current time was `05:55-06:30 JST`; still before the expected daily submit
  reset, so no Kaggle submission was made.
- Latest Kaggle state remained unchanged:
  - submission `54495224`.
  - file: `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - public score: `929.8`.
  - public episodes: `69`.
  - refreshed episode list:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0618_episodes.csv`.
- Replay availability:
  - `--save-replays` successfully downloaded all `69` public replay JSON files.
  - This confirms that older loss replays for the latest submission are
    retrievable and can be triaged locally.
- Latest public result mix, excluding validation:
  - `35` wins, `34` losses.
  - joined replay/deck table:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_join_20260710_0620.csv`.
- Losses by extracted opponent archetype:
  - `alakazam_psychic`: `6-14`.
  - `marnie_grimmsnarl`: `4-9`.
  - `mega_lucario`: `2-4`.
  - `cynthia_garchomp`: `2-2`.
  - `dragapult`: `0-2`.
  - `archaludon_metal`: `8-2`.
  - `great_tusk_crustle`, `starmie_froslass`, and `iono_bellibolt`: undefeated
    in the retrieved latest-submission public games.
- Representative replay analyses:
  - Ketchum Alt Alakazam:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85072862_ketchum_alakazam.txt`.
  - Mykhailo Marnie:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85075581_mykhailo_marnie.txt`.
  - Jason Cynthia:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85074031_jason_cynthia.txt`.
  - me-keh Lucario:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85036843_mekeh_lucario.txt`.
- Main live-loss pattern:
  - Several losses end with only one Pokemon in play or a very thin
    Duraludon/Archaludon line.
  - Common finishers:
    - Alakazam `Powerful Hand`.
    - Marnie's Grimmsnarl ex `Shadow Bullet`.
    - Mega Lucario ex `Aura Jab`.
    - Cynthia's Garchomp ex `Corkscrew Dive`.
  - Decision inspection found a concrete example where non-ex Archaludon
    `840` was held by the rule `hold non-ex Archaludon outside Ogerpon`, but
    non-ex Archaludon is not a clean fix against the main live finishers:
    `Coated Attack` prevents attack damage from Basic Pokemon only.
  - Current Archaludon deck has only `4` true Basic setup Pokemon
    (`Duraludon`), so board-thinning losses are partly structural.
- Added top-sample local opponent coverage:
  - `meta_agents/archaludon_shumpei_84743052_simple`.
  - registered as `archaludon_shumpei_2026_07_08` in
    `tools/run_meta_suite.py`.
  - added to aggregate buckets in `tools/aggregate_meta_summaries.py`.
  - short smoke:
    `analysis_outputs/post_54495224_gt_iononowall266_archshumpei_g4_20260710_0610.csv`.
    `gt_iononowall266` went `6/8` across both seats.
- Ran a live-loss-cluster local comparison:
  - output:
    `analysis_outputs/post_54495224_arch_vs_gt_live_losscluster_g4_20260710_0624_summary.csv`.
  - `arch_current`: `113/136` (`0.8309`).
  - `gt_iononowall266`: `106/136` (`0.7794`).
  - Caveat: this local cluster does not reproduce the actual live Alakazam and
    Marnie failures, so do not over-trust the local Archaludon advantage here.
- Queue decision:
  - Keep the first post-reset submit candidate as
    `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`.
  - Rationale: the latest live Archaludon is near-even (`35-34`) and loses most
    often into Alakazam/Marnie/Lucario, while Great Tusk has more true Basic
    setup density and remains the prepared deck-change test.

### 2026-07-10 06:40 JST - Pre-Reset Local Expansion And Rejected Arch Fixes

- Current time was still before the daily submit reset (`06:01 JST` at the
  start of this pass), so no Kaggle submission was made.
- Latest Kaggle state was unchanged:
  - `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - score `929.8`.
- Added reusable loss-summary tooling:
  - `tools/summarize_submission_losses.py`.
  - Input: `list_kaggle_submission_episodes.py` CSV plus
    `extract_episode_decks.py` `decks.csv`.
  - Output for latest submission:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_0615`.
  - It reproduced the key live-loss picture:
    - `alakazam_psychic`: `6-14`.
    - `marnie_grimmsnarl`: `4-9`.
    - `mega_lucario`: `2-4`.
    - `archaludon_metal`: `8-2`.
- Tested Archaludon deck transplant:
  - candidate: `tmp_compare_submissions/gtmidguard_lucariobev_shumpeideck_rules`.
  - change: current Archaludon rules with Shumpei-style deck:
    `Relicanth` + `Team Rocket's Articuno`, no `Cinderace`, no non-ex
    `Archaludon`, `14` Metal Energy.
  - live-loss cluster output:
    `analysis_outputs/post_54495224_arch_shumpeideck_live_losscluster_g4_20260710_0610_summary.csv`.
  - result: `0.8088` on the selected cluster, below the Great Tusk candidate
    `0.8382`; improves some Alakazam buckets but gives back too much into
    Marnie. Rejected as first queue candidate.
- Tested Archaludon Lillie-backup rule:
  - candidate:
    `tmp_compare_submissions/gtmidguard_lucariobev_crustledeckguard_lilliebackup`.
  - change: when `Boss's Orders` is in hand and an Archaludon can attack, still
    play `Lillie's Determination` if bench is empty and no backup Duraludon is
    in hand.
  - replay inspection confirmed the intended behavior on
    `episode_85046024`.
  - live-loss cluster output:
    `analysis_outputs/post_54495224_arch_lilliebackup_live_losscluster_g4_20260710_0622_summary.csv`.
  - result: `0.8235`, below current Archaludon `0.8824` in that run. Rejected.
- Added a new local top-meta proxy:
  - `meta_agents/kangaskhan_crustle_dung_84743044_simple`.
  - registered as `kangaskhan_crustle_dung_2026_07_08`.
  - deck source: public `2026-07-08` sample / Dũng Đỗ style
    Mega Kangaskhan ex + Dwebble/Crustle energy-denial list.
  - implementation: started from the existing Ogerpon/Raging Bolt simple agent,
    which already supports `Mega Kangaskhan ex` as a main attacker.
  - aggregate scenario:
    `public_dung_kangaskhan_crustle_2026_07_08`.
  - smoke output:
    `analysis_outputs/post_54495224_kangaskhan_crustle_dung_smoke_g4_20260710_0635_summary.csv`.
  - result:
    - current Archaludon: `2/8`.
    - `gt_iononowall266`: `8/8`.
- Queue decision reinforced:
  - Submit
    `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`
    after reset if the latest Archaludon remains stalled.
  - The new Kangaskhan/Crustle proxy is another reason to prefer the Great Tusk
    deck-change test over another Archaludon patch.

### 2026-07-10 06:35 JST - Rmy Loss And Gold-Copy Sanity Checks

- Current time was `06:09 JST`, still before the submit reset.
- Latest Kaggle state:
  - submission `54495224`.
  - score dropped from `929.8` to `927.2`.
  - public/validation episodes increased from `69` to `70`:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_continue_replays_episodes.csv`.
- New episode:
  - `85082271` vs `Rmy`.
  - result: loss, `929.8204 -> 927.2574`.
  - opponent initial score: `1062.2466`.
  - replay:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/episode_85082271_replay.json`.
  - analysis:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85082271_rmy.txt`.
- New Rmy loss pattern:
  - Rmy is another `alakazam_psychic` deck.
  - Ended through Alakazam `Powerful Hand`.
  - Our board was again a thin Archaludon line: active `Archaludon ex` removed,
    bench only `Duraludon x1`.
- Updated latest-submission public summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_continue/submission_54495224_70eps_archetype_summary.csv`.
  - public games: `69`.
  - wins/losses: `34-35`.
  - `alakazam_psychic`: `6-15` (`0.2857`).
  - `marnie_grimmsnarl`: `4-9` (`0.3077`).
  - `mega_lucario`: `2-4` (`0.3333`).
- Added Rmy local opponent:
  - `meta_agents/alakazam_rmy_live_85082271_simple`.
  - registered as `alakazam_rmy_live`.
  - scenario: `live_rmy_alakazam_2026_07_10`.
  - The deck is materially the same as the live matsurih Alakazam shell, but
    keeping Rmy as a separate bucket makes live-loss triage clearer.
- Rmy smoke:
  - output:
    `analysis_outputs/post_54495224_rmy_alakazam_smoke_g8_20260710_0615_summary.csv`.
  - `arch_current`: `12/16`.
  - `gt_iononowall266`: `13/16`.
- Updated loss-cluster comparison with Rmy and Kangaskhan/Crustle:
  - output:
    `analysis_outputs/post_54495224_arch_vs_gt_losscluster_plus_g4_20260710_0620_summary.csv`.
  - `arch_current`: `0.8882`.
  - `gt_iononowall266`: `0.8158`.
  - Caveat: this local score still contradicts the live Alakazam/Marnie losses,
    so it should not override live evidence.
- Tested gold-copy-style local candidates:
  - `kang_bono_copy` from `meta_agents/great_tusk_bono_junlee_84743036_simple`.
    - output:
      `analysis_outputs/post_54495224_bono_candidate_losscluster_plus_g4_20260710_0625_summary.csv`.
    - result: `0.7303`; weak into Alakazam buckets. Rejected as first queue.
  - `liamk_copy` from `meta_agents/great_tusk_liamk_84743031_simple`.
    - output:
      `analysis_outputs/post_54495224_liamk_candidate_losscluster_plus_g4_20260710_0630_summary.csv`.
    - result: `0.6382`; very weak into Alakazam buckets. Rejected as first
      queue.
- Queue decision unchanged:
  - First post-reset submit remains
    `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`.
  - Reason: latest live Archaludon has fallen to `34-35` public and is
    consistently losing to high-score Alakazam/Marnie/Lucario. The gold-copy
    Kangaskhan/LiamK candidates do not currently beat the local Alakazam
    checks, while `gt_iononowall266` remains the best prepared deck-change
    experiment.

### 2026-07-10 06:45 JST - Kazuki Marnie Loss And Final Pre-Reset GT Check

- Current time was `06:15 JST`, still before submit reset.
- Latest Kaggle state:
  - submission `54495224`.
  - score dropped again: `927.2 -> 924.0`.
  - episodes increased to `71`.
- New episode:
  - `85083586` vs `kazuki0123`.
  - result: loss, `927.2574 -> 924.0665`.
  - opponent initial score: `1012.4060`.
  - replay:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/episode_85083586_replay.json`.
  - analysis:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85083586_kazuki.txt`.
- New kazuki loss pattern:
  - `marnie_grimmsnarl`.
  - Ended with our `Archaludon ex` alone on board, no bench, knocked out by
    Marnie's Grimmsnarl ex `Shadow Bullet`.
  - This is the same thin-board failure family as the latest Alakazam losses.
- Updated latest-submission public summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_continue2/submission_54495224_71eps_archetype_summary.csv`.
  - public games: `70`.
  - wins/losses: `34-36`.
  - `alakazam_psychic`: `6-15` (`0.2857`).
  - `marnie_grimmsnarl`: `4-10` (`0.2857`).
  - `mega_lucario`: `2-4` (`0.3333`).
- Added kazuki local opponent:
  - `meta_agents/marnie_kazuki_live_85083586_simple`.
  - registered as `marnie_kazuki_live`.
  - scenario: `live_kazuki_marnie_2026_07_10`.
- kazuki smoke:
  - output:
    `analysis_outputs/post_54495224_kazuki_marnie_smoke_g8_20260710_0622_summary.csv`.
  - `arch_current`: `15/16`.
  - `gt_iononowall266`: `12/16`.
  - Caveat: this again shows local simple Marnie play is easier than live
    high-score play, so live replay evidence remains more important.
- Updated Rmy/kazuki/Kangaskhan cluster:
  - output:
    `analysis_outputs/post_54495224_arch_vs_gt_losscluster_plus2_g4_20260710_0628_summary.csv`.
  - `arch_current`: `0.8187`.
  - `gt_iononowall266`: `0.8500`.
  - The update finally favors the Great Tusk candidate even under the local
    simplified agents.
- Tested `tmp_compare_submissions/greattusk_iononowall_marnie_readyrace`:
  - change: disable Crustle wall mode against Marnie when active Great Tusk can
    already use `Land Collapse`.
  - focused Marnie output:
    `analysis_outputs/post_54495224_gt_marnie_readyrace_marnie_g8_20260710_0635_summary.csv`.
  - result: `gt_iononowall266` `0.7917`, ready-race `0.7604`.
  - improved kazuki/shota but hurt Mykhailo/Sota too much. Rejected.
- Queue decision unchanged and stronger:
  - Submit
    `submission_great_tusk_crustle_iononowall_iono266_20260710_queue.tar.gz`
    after reset unless the live state changes materially.
  - Do not patch the queued package with `marnie_readyrace`.

### 2026-07-10 06:30 JST - Pre-Reset Queue Changed To GT SetupAZ Fallback

- Current time was `06:28 JST`, still before the expected daily submit reset.
- Kaggle latest state remained unchanged:
  - latest submission: `54495224`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - score: `924.0`.
  - public episodes: `70`.
  - public record: `34-36`.
- Refreshed live-loss summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_0625/submission_54495224_71eps_archetype_summary.csv`.
  - `alakazam_psychic`: `6-15` (`0.2857`).
  - `marnie_grimmsnarl`: `4-10` (`0.2857`).
  - `mega_lucario`: `2-4` (`0.3333`).
  - `archaludon_metal`: `8-2` (`0.8000`).
  - `starmie_froslass`, `iono_bellibolt`, `great_tusk_crustle`: all unbeaten
    in the small live sample.
- Re-checked the two prepared Great Tusk candidates:
  - `gt_iononowall266`:
    `tmp_compare_submissions/greattusk_iononowall`.
  - `gt_setupaz_fallback`:
    `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr`.
  - Deck lists are identical; only rule logic differs.
- Broad final compare:
  - output:
    `analysis_outputs/post_54495224_gt_queue_vs_fallback_cluster_starmie_g4_20260710_0642_summary.csv`.
  - equal public buckets:
    - `gt_iononowall266`: `0.8073`.
    - `gt_setupaz_fallback`: `0.8438`.
- Focused re-check with more games on the disputed buckets:
  - output:
    `analysis_outputs/post_54495224_gt_queue_vs_fallback_focus_g8_20260710_0630_summary.csv`.
  - equal public buckets:
    - `gt_iononowall266`: `0.7375`.
    - `gt_setupaz_fallback`: `0.7688`.
  - fallback improved the important Marnie/Kangaskhan/Starmie-side insurance:
    - `marnie_gonsaku_live`: `0.7500 -> 0.8750`.
    - `marnie_shishio_live`: `0.8125 -> 0.9375`.
    - `kangaskhan_crustle_dung_2026_07_08`: `0.7500 -> 0.8750`.
    - `starmie_windecks_2026_07_08`: `0.4375 -> 0.6250`.
    - `cynthia_garchomp_topdecking_live`: `0.6875 -> 0.8750`.
  - fallback lost ground into:
    - `iono_bellibolt_alghital_live`: `0.7500 -> 0.5000`.
    - `alakazam_capbloo2_live`: `0.9375 -> 0.8125`.
    - `starmie_yushin_2026_07_08`: `0.3750 -> 0.3125`.
- Queue decision changed:
  - First post-reset submit should now be:
    `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.
  - SHA256:
    `9BAE212FDAABF2C4BD6AC7D164DED4D8227284A72A30E934B909EC5CDE395367`.
  - Verified:
    - package has root `main.py`, `deck.csv`, `requirements.txt`, and `cg/`.
    - package has `13` entries.
    - `deck.csv` has `60` cards.
    - `py -3 -m py_compile` passes.
- Submit command after reset, if the live state is still stalled:
  - `kaggle competitions submit -c pokemon-tcg-ai-battle -f submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz -m "Great Tusk setupaz fallback: Starmie/Kangaskhan/Marnie insurance after Archaludon 924 plateau"`
- Monitoring rule:
  - If the new submission gets execution errors, stop immediately.
  - If it reaches roughly `20-40` public games and is clearly below the
    Archaludon baseline, cut after about `1-2` hours.
  - If it is near or above silver pace, keep it running at least `6` hours and
    prefer `24` hours before replacing it.

### 2026-07-10 06:55 JST - Heartbeat Monitor Retargeted

- Heartbeat instructions were stale and still pointed at submission `54493893`.
- Refreshed Kaggle submissions:
  - current latest submission remains `54495224`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - score remains `924.0`.
  - previous submission `54493893` has fallen to `852.2`, so it is no longer
    the active monitor target.
- Refreshed episodes for `54495224`:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0655_episodes.csv`.
  - episodes remain `71`.
  - public record remains `34-36`.
  - latest public episode is still `85083586` vs `kazuki0123`, a Marnie loss.
- Automation update:
  - `kaggle-ptcg-submit-loop` now targets submission `54495224`.
  - It also records the next prepared candidate:
    `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.
- Decision:
  - No submit yet because it is still before the expected reset window.
  - If the same state persists after reset, submit the GT SetupAZ fallback
    candidate.

### 2026-07-10 07:25 JST - New Losses Before Reset

- Current time was `07:25 JST`, still before the expected submit reset.
- Kaggle latest state:
  - submission `54495224`.
  - score fell from `924.0` to `922.4`.
  - episodes increased from `71` to `74`.
  - public record is now `35-38`.
- Refreshed episode output:
  - `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0725_episodes.csv`.
- New public games since the 06:55 check:
  - `85090675` vs `mitomeat823`: loss, `mega_lucario`, opponent initial
    `1033.9`, updated score `921.2`.
  - `85091788` vs `Reki`: win, `great_tusk_crustle`, opponent initial
    `915.1`, updated score `925.6`.
  - `85093671` vs `Bozo Boys`: loss, `alakazam_psychic`, opponent initial
    `1014.9`, updated score `922.4`.
- Updated archetype summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_0725/submission_54495224_74eps_archetype_summary.csv`.
  - `alakazam_psychic`: `6-16` (`0.2727`).
  - `marnie_grimmsnarl`: `4-10` (`0.2857`).
  - `mega_lucario`: `2-5` (`0.2857`).
  - `great_tusk_crustle`: `4-0` (`1.0000`).
- New replay triage:
  - `85090675`:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85090675_mitomeat823.csv`.
    - Loss ended with opponent `Mega Lucario ex` attacking into our empty
      board; our side had no bench.
  - `85093671`:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/replay_analysis_85093671_bozoboys.csv`.
    - Bozo Boys uses the same Alakazam 60 as several existing buckets
      (`alakazam_rmy_live`, `alakazam_matsurih_live`, `alakazam_noor_live`).
    - Loss ended after Alakazam `Powerful Hand`; our board still had
      Archaludon pieces, but the Alakazam chain survived the prize race.
- Deck matching:
  - Bozo Boys Alakazam: exact `60/60` match to existing Rmy/matsurih/noor
    buckets.
  - mitomeat823 Lucario: near match (`59/60`) to
    `mega_lucario_akira_84743057_simple`,
    `mega_lucario_mekeh_live_85036843_simple`, and
    `mega_lucario_public_simple`.
- Local re-check for queued GT SetupAZ fallback:
  - output:
    `analysis_outputs/post_54495224_0725_newloss_gtsetupaz_g8_summary.csv`.
  - equal buckets: `0.8393`.
  - Alakazam buckets:
    - `alakazam_noor_live`: `14/16` (`0.8750`).
    - `alakazam_matsurih_live`: `13/16` (`0.8125`).
    - `alakazam_rmy_live`: `13/16` (`0.8125`).
  - Lucario buckets:
    - `lucario_akira_2026_07_08`: `15/16` (`0.9375`).
    - `lucario_mekeh_live`: `16/16` (`1.0000`).
    - `lucario_fujiborozoukin_live`: `14/16` (`0.8750`).
    - `lucario_genki_live`: `9/16` (`0.5625`).
- Decision:
  - New losses strengthen the case that current Archaludon has stalled against
    high-score Alakazam/Lucario.
  - Still no submit before reset.
  - GT SetupAZ fallback remains the first post-reset submission candidate.

### 2026-07-10 07:55 JST - No New Games

- Current time was `07:55 JST`, still before the expected submit reset.
- Kaggle latest state:
  - submission `54495224`.
  - score remains `922.4`.
  - episodes remain `74`.
  - public record remains `35-38`.
- Refreshed episode output:
  - `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0755_episodes.csv`.
- There were no new games since the `07:25 JST` check.
- Automation update:
  - `kaggle-ptcg-submit-loop` now includes the `07:55 JST` state.
- Decision:
  - No submit yet.
  - If this state persists after the expected reset, submit the queued GT
    SetupAZ fallback candidate.

### 2026-07-10 08:25 JST - One More Loss Before Reset

- Current time was `08:25 JST`, still before the expected submit reset.
- Kaggle latest state:
  - submission `54495224`.
  - score fell from `922.4` to `917.6`.
  - episodes increased from `74` to `75`.
  - public record is now `35-39`.
- Refreshed episode output:
  - `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0825_episodes.csv`.
- New public game since the `07:55 JST` check:
  - `85103885` vs `Rajan Nagarajan`: loss, `archaludon_metal`,
    opponent initial `904.2`, updated score about `917.6`.
- Updated archetype summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_0825/submission_54495224_75eps_archetype_summary.csv`.
  - `alakazam_psychic`: `6-16` (`0.2727`).
  - `marnie_grimmsnarl`: `4-10` (`0.2857`).
  - `mega_lucario`: `2-5` (`0.2857`).
  - `archaludon_metal`: `8-3` (`0.7273`).
- Since the new loss was an Archaludon mirror, ran a final mirror sanity check
  for the queued GT SetupAZ fallback:
  - output:
    `analysis_outputs/post_54495224_0825_archmirror_gtsetupaz_g8_summary.csv`.
  - equal buckets: `0.8000`.
  - bucket results:
    - `archaludon`: `14/16` (`0.8750`).
    - `archaludon_ezreal77_live`: `14/16` (`0.8750`).
    - `archaludon_victorvv_live`: `11/16` (`0.6875`).
    - `archaludon_toru_live`: `12/16` (`0.7500`).
    - `archaludon_shumpei_2026_07_08`: `13/16` (`0.8125`).
- Automation update:
  - `kaggle-ptcg-submit-loop` now includes the `08:25 JST` state.
- Decision:
  - No submit yet because it is still before reset.
  - The current submission is clearly still drifting down.
  - GT SetupAZ fallback remains the first post-reset submission candidate.

### 2026-07-10 09:05 JST - Submitted GT SetupAZ Fallback

- Pre-submit check at `08:55 JST`:
  - latest Archaludon submission `54495224`.
  - score had recovered from `917.6` to `921.4`, but remained below the
    earlier `924.0` plateau.
  - episodes increased from `75` to `77`.
  - public record was `36-40`.
  - refreshed output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260710_0855_episodes.csv`.
- New public games since `08:25 JST`:
  - `85104465` vs `Benarg`: win, `starmie_froslass`, opponent initial
    `1009.2`, updated score `923.7`.
  - `85105005` vs `bono`: loss, `alakazam_psychic`, opponent initial
    `1079.1`, updated score `921.5`.
- Final old-submission archetype summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/loss_summary_20260710_0855/submission_54495224_77eps_archetype_summary.csv`.
  - `alakazam_psychic`: `6-17` (`0.2609`).
  - `marnie_grimmsnarl`: `4-10` (`0.2857`).
  - `mega_lucario`: `2-5` (`0.2857`).
  - `archaludon_metal`: `8-3` (`0.7273`).
  - `starmie_froslass`: `4-0` (`1.0000`).
- Submit action:
  - waited until `2026-07-10T09:00:05+09:00`.
  - submitted:
    `submission_great_tusk_crustle_setupaz_targeted19_starmierush_nostarmieoverride_nogiantstarmie_stretcher_cutterr_20260710_queue.tar.gz`.
  - message:
    `Great Tusk setupaz fallback: Starmie/Kangaskhan/Marnie insurance after Archaludon 924 plateau`.
  - CLI uploaded successfully, then hit a local `cp932` Unicode print error.
    Submission list confirmed the upload was accepted, so no duplicate submit
    was attempted.
- New submission:
  - id: `54509450`.
  - status: `COMPLETE`.
  - initial score: `600.0`.
  - submitted at `2026-07-10 00:00:07.987 UTC` / `09:00:07.987 JST`.
  - no error description.
- Initial episode fetch:
  - output:
    `analysis_outputs/kaggle_live/submission_54509450_gtsetupaz/monitor_54509450_20260710_0903_episodes.csv`.
  - episodes: `1`.
  - validation: `1-0`.
  - public games: `0`.
  - replay:
    `analysis_outputs/kaggle_live/submission_54509450_gtsetupaz/episode_85109238_replay.json`.
- Automation update:
  - `kaggle-ptcg-submit-loop` now targets submission `54509450`.
- Monitoring rule for `54509450`:
  - watch immediately for execution errors.
  - use `20-40` public games as the early failure window.
  - if it is near or above silver pace, prefer at least `6` hours and ideally
    `24` hours before replacing it.

### 2026-07-10 09:30 JST - GT SetupAZ Early Failure And Rescue Revert

- First monitor of GT SetupAZ submission `54509450` at `09:25 JST`:
  - status: `COMPLETE`.
  - score: `428.8`.
  - episodes: `6`.
  - validation: `1`.
  - public games: `5`.
  - public record: `1-4`.
  - output:
    `analysis_outputs/kaggle_live/submission_54509450_gtsetupaz/monitor_54509450_20260710_0925_episodes.csv`.
- Public game summary:
  - `85109987` vs `DeeSaa`: loss, `alakazam_psychic`, opponent initial
    `983.3`.
  - `85110694` vs `TOSS`: win, `alakazam_psychic`, opponent initial `444.8`.
  - `85111321` vs `Roy Lo TW`: loss, `mega_lucario`, opponent initial `763.7`.
  - `85111905` vs `A.Ishibashi`: loss, unknown by current classifier,
    but deck was Mega Abomasnow/Kyogre-style water, opponent initial `518.5`.
  - `85112505` vs `DeviPriya Raju`: loss, unknown by current classifier,
    but deck was Mega Abomasnow/Kyogre-style water, opponent initial `480.3`.
- Loss summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54509450_gtsetupaz/loss_summary_20260710_0925/submission_54509450_6eps_archetype_summary.csv`.
  - `unknown`: `0-2`.
  - `alakazam_psychic`: `1-1`.
  - `mega_lucario`: `0-1`.
- Decision:
  - This was too poor to wait for `20-40` public games.
  - The two losses to low-score Mega Abomasnow/Kyogre-style decks indicate a
    structural blind spot in GT SetupAZ, not just top-ladder variance.
  - Immediate rescue was preferred to protect the run.
- Rescue submit:
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - reason: previous same archive submission `54495224` was around `926.1`
    when the rescue decision was made.
  - package check:
    - SHA256:
      `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`.
    - `deck.csv` has `60` cards.
    - `py -3 -m py_compile` passed after extraction.
  - submit message:
    `Restore Archaludon crustledeckguard after GT setupaz early failure`.
  - new submission id: `54510332`.
  - submitted at `2026-07-10 00:27:22 UTC` / `09:27:22 JST`.
- Rescue initial state:
  - status: `COMPLETE`.
  - score: `600.0`.
  - episodes: `1`.
  - public games: `0`.
  - output:
    `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_0930_episodes.csv`.
  - replay:
    `analysis_outputs/kaggle_live/submission_54510332_archrescue/episode_85113601_replay.json`.
  - Note: the validation row shows `target_reward = -1`, but Kaggle status is
    `COMPLETE` with no error description, so this is not treated as a submit
    failure.
- Automation update:
  - `kaggle-ptcg-submit-loop` now targets submission `54510332`.
- Next action:
  - Monitor `54510332` public games.
  - Do not submit another candidate unless this rescue submission errors or
    clearly fails after public games begin.
  - Add Mega Abomasnow/Kyogre to local meta coverage before attempting another
    Great Tusk style deck.

### 2026-07-10 09:55 JST - Rescue Archaludon First Public Games

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - score: `623.7`.
  - episodes: `7`.
  - public games: `6`.
  - public record: `3-3`.
- Refreshed episode output:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_0955_episodes.csv`.
- Public results:
  - win vs `lucasta1`, `mega_lucario`, opponent initial `603.2`.
  - win vs `MMA`, `cynthia_garchomp`, opponent initial `692.3`.
  - loss vs `kurikuri54`, `starmie_froslass`, opponent initial `706.4`.
  - loss vs `giacomovin`, `alakazam_psychic`, opponent initial `755.5`.
  - win vs `ituhime`, `dragapult`, opponent initial `526.7`.
  - loss vs `lolzpo rpg`, `marnie_grimmsnarl`, opponent initial `680.1`.
- Loss summary:
  - output:
    `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_0955_reclassified/submission_54510332_7eps_archetype_summary.csv`.
  - `starmie_froslass`: `0-1`.
  - `alakazam_psychic`: `0-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - wins came against `mega_lucario`, `cynthia_garchomp`, and `dragapult`.
- Tooling update:
  - `tools/extract_episode_decks.py` now recognizes
    `mega_abomasnow_kyogre` with marker IDs `{721, 722, 723}`.
  - `py -3 -m py_compile tools/extract_episode_decks.py` passed.
  - Reclassified the failed GT SetupAZ run:
    `analysis_outputs/kaggle_live/submission_54509450_gtsetupaz/loss_summary_20260710_0925_reclassified/submission_54509450_6eps_archetype_summary.csv`.
  - The former `unknown` losses are now clearly `mega_abomasnow_kyogre`:
    `0-2`.
- Decision:
  - No new submission.
  - `54510332` is not good yet, but it is no longer an immediate GT-style
    collapse. Continue monitoring until roughly `20` public games before
    making another submit decision unless it sharply fails sooner.

### 2026-07-10 10:28 JST - Rescue Archaludon At 15 Public Games

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - score: `673.2`.
  - episodes: `16`.
  - public games: `15`.
  - public record: `7-8`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1028_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1028`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1028/submission_54510332_16eps_archetype_summary.csv`.
- New games since `09:55 JST`:
  - wins:
    - `85117075` vs `Julian Vignes`, `great_tusk_crustle`.
    - `85117658` vs `Marcus Vinicius`, `mega_abomasnow_kyogre`.
    - `85118191` vs `Ville`, `starmie_froslass`.
    - `85118677` vs `Tys TANA`, `dragapult`.
  - losses:
    - `85118719` vs `kabu strongest legend`, `dragapult`.
    - `85119222` vs `AbdulHannan Siddiqui`, `alakazam_psychic`.
    - `85119777` vs `tennogh`, `dragapult`.
    - `85120309` vs `Hayauchiwasabi`, `great_tusk_crustle`.
    - `85120883` vs `yankoGPT`, `okidogi_barbaracle`.
- Current archetype summary:
  - `dragapult`: `2-2`.
  - `alakazam_psychic`: `0-2`.
  - `great_tusk_crustle`: `1-1`.
  - `starmie_froslass`: `1-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `cynthia_garchomp`: `1-0`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `mega_lucario`: `1-0`.
- Decision:
  - No new submission.
  - The rescue submission is weak so far, but not an execution failure and not
    a GT-style immediate collapse.
  - Wait until at least about `20` public games unless the next check shows a
    sharp collapse.
  - If it stays near `50%` or below, the next candidate must explicitly cover
    Alakazam plus the spread of Dragapult/Great Tusk/Okidogi losses; do not
    panic-submit another untested deck change.

### 2026-07-10 10:55 JST - Rescue Archaludon Recovering

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - score: `758.5`.
  - episodes: `23`.
  - public games: `22`.
  - public record: `13-9`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1055_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1055`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1055/submission_54510332_23eps_archetype_summary.csv`.
- Since the `10:28 JST` fetch:
  - new public games: `7`.
  - record: `6-1`.
  - wins vs `great_tusk_crustle`, `mega_lucario`, `rocket_mewtwo_spidops`,
    `starmie_froslass`, and another `great_tusk_crustle`.
  - only loss was vs `iono_bellibolt` (`Tomonobu Niwa`, opponent initial
    `800.8`).
- Current archetype summary:
  - `dragapult`: `2-2`.
  - `alakazam_psychic`: `0-2`.
  - `great_tusk_crustle`: `3-1`.
  - `starmie_froslass`: `2-1`.
  - `iono_bellibolt`: `0-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `mega_lucario`: `3-0`.
  - `cynthia_garchomp`: `1-0`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `rocket_mewtwo_spidops`: `1-0`.
- Decision:
  - No new submission.
  - The rescue Archaludon has recovered from the weak first `15` public games
    and passed the `20` public game early-failure check.
  - Keep monitoring. If score continues climbing or approaches silver pace,
    prefer at least `6` hours and ideally `24` hours before replacing.
  - Any replacement candidate must address the actual persistent losses,
    especially Alakazam, and should not be a broad untested deck swap.

### 2026-07-10 11:28 JST - Rescue Archaludon Still Climbing

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - score: `773.8`.
  - episodes: `31`.
  - public games: `30`.
  - public record: `18-12`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1128_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1128`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1128/submission_54510332_31eps_archetype_summary.csv`.
- Score path during this monitoring window:
  - `10:55 JST`: `758.5`, public `13-9`.
  - `11:25 JST`: `781.1`, public `18-11`.
  - `11:28 JST`: `773.8`, public `18-12`.
- New games since the `10:55 JST` fetch:
  - wins:
    - `85125056` vs `macaron`, `mega_lucario`.
    - `85125566` vs `Steve Watson`, classified `unknown`.
    - `85126075` vs `Ra'uf Fauzan Rambe`, `dragapult`.
    - `85127065` vs `Kota Morimoto`, `starmie_froslass`.
    - `85128130` vs `tktkyamyam`, `great_tusk_crustle`.
  - losses:
    - `85126578` vs `AEONcorridor`, `dragapult`.
    - `85127556` vs `Kirill Tushin`, `mega_lucario`.
    - `85128618` vs `Clark Kitchen`, `archaludon_metal`.
- Current archetype summary:
  - `dragapult`: `3-3`.
  - `alakazam_psychic`: `0-2`.
  - `great_tusk_crustle`: `4-1`.
  - `mega_lucario`: `4-1`.
  - `starmie_froslass`: `3-1`.
  - `archaludon_metal`: `0-1`.
  - `iono_bellibolt`: `0-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `cynthia_garchomp`: `1-0`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `rocket_mewtwo_spidops`: `1-0`.
  - `unknown`: `1-0`.
- Decision:
  - No new submission.
  - The run is still below the old `54495224` reference, but it is climbing
    and has not met a measured replacement threshold.
  - Continue monitoring. If the score reverses sharply, prioritize candidates
    that cover persistent `alakazam_psychic` plus the broader
    `dragapult`/`archaludon_metal`/`iono_bellibolt` loss spread.

### 2026-07-10 11:55 JST - Alakazam Emerging As Main Weakness

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - score: `780.9`.
  - episodes: `38`.
  - public games: `37`.
  - public record: `22-15`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1155_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1155`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1155/submission_54510332_38eps_archetype_summary.csv`.
- Since the `11:28 JST` check:
  - new public games: `7`.
  - record: `4-3`.
  - wins:
    - `85130114` vs `Takayuki Nukui`, `dragapult`.
    - `85131067` vs `EF`, `starmie_froslass`.
    - `85131564` vs `Team Rockets MAGIKARP`, `starmie_froslass`.
    - `85132048` vs `kunihiro`, `mega_lucario`.
  - losses:
    - `85129115` vs `llkarill`, `alakazam_psychic`, opponent initial `985.7`.
    - `85129621` vs `CodeAmansa`, `alakazam_psychic`, opponent initial
      `718.4`.
    - `85130601` vs `TomJ286991`, `mega_lucario`, opponent initial `834.9`.
- Current archetype summary:
  - `alakazam_psychic`: `0-4`.
  - `dragapult`: `4-3`.
  - `mega_lucario`: `5-2`.
  - `starmie_froslass`: `5-1`.
  - `great_tusk_crustle`: `4-1`.
  - `archaludon_metal`: `0-1`.
  - `iono_bellibolt`: `0-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `cynthia_garchomp`: `1-0`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `rocket_mewtwo_spidops`: `1-0`.
  - `unknown`: `1-0`.
- Decision:
  - No new submission.
  - Score is still climbing slowly, so replacing now would be premature.
  - The next candidate, if needed, should primarily target Alakazam while
    preserving current strengths into Mega Lucario, Starmie, and Great Tusk.

### 2026-07-10 12:25 JST - Mild Pullback, No Submit

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - score observed around `756.1` to `764.0` during the check.
  - episodes: `46`.
  - public games: `45`.
  - public record: `25-20`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1225_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1225`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1225/submission_54510332_46eps_archetype_summary.csv`.
- Since the `11:55 JST` check:
  - new public games: `8`.
  - record: `3-5`.
  - wins:
    - `85133029` vs `Sama`, `archaludon_metal`.
    - `85133518` vs `AKIYA NAKASATO`, `dragapult`.
    - `85135575` vs `monicrew`, `alakazam_psychic`.
  - losses:
    - `85132533` vs `SuperNorman`, `mega_lucario`.
    - `85134031` vs `nowan`, `dragapult`.
    - `85134237` vs `TMMT`, `archaludon_metal`.
    - `85134518` vs `TrustHub hiroingk`, `alakazam_psychic`.
    - `85135012` vs `aoi_sugawara`, `cynthia_garchomp`.
- Current archetype summary:
  - `alakazam_psychic`: `1-5`.
  - `dragapult`: `5-4`.
  - `mega_lucario`: `5-3`.
  - `archaludon_metal`: `1-2`.
  - `starmie_froslass`: `5-1`.
  - `great_tusk_crustle`: `4-1`.
  - `cynthia_garchomp`: `1-1`.
  - `iono_bellibolt`: `0-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `rocket_mewtwo_spidops`: `1-0`.
  - `unknown`: `1-0`.
- Decision:
  - No new submission.
  - This is a mild pullback, not a sharp collapse.
  - If a replacement is needed later, target persistent `alakazam_psychic`
    first, then `archaludon_metal` mirror, while preserving current favorable
    matchups into `starmie_froslass` and `great_tusk_crustle`.

### 2026-07-10 12:55 JST - Mild Recovery Continues

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - public score: `768.8`.
  - episodes: `48`.
  - public games: `47`.
  - public record: `27-20`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1255b_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1255b`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1255b/submission_54510332_48eps_archetype_summary.csv`.
- Since the `12:25 JST` check:
  - new public games: `2`.
  - record: `2-0`.
  - wins:
    - `85136098` vs `Riku Suzuki`, likely `mega_lucario`.
    - `85139120` vs `monicrew`, `alakazam_psychic`.
- Current archetype summary:
  - `alakazam_psychic`: `2-5`.
  - `dragapult`: `5-4`.
  - `mega_lucario`: `6-3`.
  - `archaludon_metal`: `1-2`.
  - `starmie_froslass`: `5-1`.
  - `great_tusk_crustle`: `4-1`.
  - `cynthia_garchomp`: `1-1`.
  - `iono_bellibolt`: `0-1`.
  - `marnie_grimmsnarl`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `rocket_mewtwo_spidops`: `1-0`.
  - `unknown`: `1-0`.
- Decision:
  - No new submission.
  - The rescue Archaludon recovered lightly and has a positive public record.
  - Continue monitoring; a replacement should still target `alakazam_psychic`
    and `archaludon_metal` only if the score rolls over again.

### 2026-07-10 13:29 JST - Recovery Still Intact

- Current latest submission:
  - id: `54510332`.
  - file:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`.
  - status: `COMPLETE`.
  - public score: `773.7`.
  - episodes: `49`.
  - public games: `48`.
  - public record: `28-20`.
- Refreshed outputs:
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/monitor_54510332_20260710_1329_episodes.csv`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/decks_20260710_1329`.
  - `analysis_outputs/kaggle_live/submission_54510332_archrescue/loss_summary_20260710_1329/submission_54510332_49eps_archetype_summary.csv`.
- Since the `12:55 JST` check:
  - new public games: `1`.
  - record: `1-0`.
  - win:
    - `85143484` vs `Japanese Kaggle Newbie`, `marnie_grimmsnarl`.
- Current archetype summary:
  - `alakazam_psychic`: `2-5`.
  - `dragapult`: `5-4`.
  - `mega_lucario`: `6-3`.
  - `archaludon_metal`: `1-2`.
  - `starmie_froslass`: `5-1`.
  - `great_tusk_crustle`: `4-1`.
  - `marnie_grimmsnarl`: `1-1`.
  - `cynthia_garchomp`: `1-1`.
  - `iono_bellibolt`: `0-1`.
  - `okidogi_barbaracle`: `0-1`.
  - `mega_abomasnow_kyogre`: `1-0`.
  - `rocket_mewtwo_spidops`: `1-0`.
  - `unknown`: `1-0`.
- Decision:
  - No new submission.
  - The current submission has recovered from the 12:25 pullback.
  - Keep monitoring; the replacement threshold remains a sharper reversal or
    repeated losses into the persistent `alakazam_psychic` and
    `archaludon_metal` buckets.

### 2026-07-10 19:18 JST - Rating Snapshot Removed From RL Promotion Gate

- The active `54510332` archive is byte-identical in policy and deck to the
  earlier `54495224` archive, so its lower displayed rating is not evidence of
  a weaker implementation.
- Same-policy replay windows now available locally:
  - `54495224`: `77` games, approximately `41-36`.
  - `54510332`: `54` saved replays, approximately `31-22` public at the latest
    usable snapshot plus validation.
  - episode overlap: `0`.
- The first exact-hidden teacher dataset from `54510332` contains:
  - `829` usable states from `47` episodes.
  - `2,343` independently generated, actually evaluated non-baseline options.
  - `51` accepted rollout changes, concentrated in only `19` episodes.
- Strict episode-grouped results:
  - binary Gradient Boosting recovered `0/51` accepted changes at conservative
    thresholds and produced false overrides.
  - continuous rollout-advantage regression had correlation about `0.069`.
  - adding public deck-count belief features made `295/829` states uniquely
    identify a catalog deck but still recovered `0/51` accepted changes.
- A previous apparently high-precision tree result was invalidated: its option
  pool appended the expert action when missing, leaking label information.
  Rebuilt datasets now use only the rollout engine's teacher-independent
  `candidate_actions` set.
- Current action:
  - no submission.
  - generate exact-hidden labels for all `77` historical same-policy replays.
  - train only on `54495224`, then evaluate once on `54510332` as a separate
    submission-window holdout.
  - do not use the current Kaggle rating as an RL model-selection metric.

### 2026-07-10 20:50 JST - Seeded Residual RL Submitted

- New submission:
  - id: `54526221`.
  - archive:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v3_20260710.tar.gz`.
  - SHA256:
    `5301449d1e31a8c1be32324351c13c479626403c39ea9b114795ad43375cb211`.
  - message: `Seeded residual RL: conservative early/mid energy ordering for Archaludon mirrors`.
- Implementation:
  - unchanged 60-card Archaludon deck and existing rule agent.
  - two sparse residual weights, both `+0.03`, favoring close Energy Attach
    actions in identified Archaludon mirrors during turn buckets `<=4` and
    `<=10`.
  - all other public matchups retain exact baseline behavior.
- Corrected evaluation infrastructure before submission:
  - added a local `BattleStartSeeded` C++ API because stock `BattleStart`
    ignores Python seeds and uses `std::random_device`.
  - zero residual now returns the exact rule action instead of rescoring it.
  - training obtains baseline actions through the real stateful `agent()` path.
  - package runtime loads sibling `residual_policy.py` by absolute file path;
    it no longer silently drops weights when the agent directory is absent from
    `sys.path`.
- Verification:
  - `64` RL tests passed.
  - archive has `60` cards, `14` entries, required runtime files, and no
    duplicate paths.
  - built package exactly matched the training policy over `220` seeded games.
  - non-Archaludon package and baseline exactly matched over `320` games across
    eight archetypes.
  - final 11-opponent Archaludon panel: baseline `1026/2200`, candidate
    `1030/2200`; shaped reward `-0.07060 -> -0.06669`.
- Status at submission time: `PENDING`.
- Next action:
  - monitor for execution errors immediately.
  - collect public episodes and rating; the goal remains incomplete until this
    or a later submitted agent reaches the live gold range.

### 2026-07-10 20:59 JST - Minimal Inline RL Passed Validation

- Generic residual-runtime attempts:
  - `54526221`: `ERROR`, both validation seats failed at step zero.
  - `54526456`: `ERROR`, the static-runtime/tar-structure revision failed at
    the same step.
  - neither reached public matchmaking and neither provides a performance
    result.
- Final minimal submission:
  - id: `54526632`.
  - archive:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710.tar.gz`.
  - SHA256:
    `63aa08ca773a3edf44f482602a1b80d8285708386883fac4a4b092332577687a`.
  - status: `COMPLETE`.
  - initial score: `600.0` from one validation episode; no public games yet.
- Deployment change:
  - copied the last successful archive member-for-member and replaced only
    `main.py` (`53,448 -> 54,331` bytes).
  - implemented the same normalized `+0.03` Attach preference directly inside
    the existing rule scorer for Archaludon turn windows `<=4` and `7..10`.
  - no helper module, JSON runtime load, or archive-layout change remains.
- Verification:
  - inline scorer and generic residual policy were exactly equal over 220
    seeded games.
  - source archive and final archive have identical 22-member names and order;
    only `main.py` differs.
  - all 64 tests pass.
- Next action:
  - monitor `54526632` public episodes and score.
  - continue corrected seeded optimization in parallel; stop only after a
    submitted agent reaches the live gold range.

### 2026-07-10 22:01 JST - Inline RL Live Start and Alakazam Holdout Rejection

- Current submitted agent:
  - id: `54526632`.
  - public games: `12`.
  - public record: `8-4`.
  - current public score: `808.4`.
  - latest episode CSV:
    `analysis_outputs/kaggle_live/submission_54526632_archattach_inline/monitor_54526632_2201_episodes.csv`.
- Public archetype record:
  - `archaludon_metal`: `1-0`.
  - `alakazam_psychic`: `1-1`.
  - `mega_lucario`: `1-2`.
  - `great_tusk_crustle`: `0-1`.
  - `dragapult`, `hop_trevenant`, `starmie_froslass`,
    `mega_abomasnow_kyogre`, and `chandelure_psychic_control`: `1-0` each.
- Current leaderboard snapshot:
  - CSV:
    `analysis_outputs/leaderboard_current_2026_07_10_2145/pokemon-tcg-ai-battle-publicleaderboard-2026-07-10T12_43_32.csv`.
  - rank-20 / working gold cutoff: `1055.8`.
  - the goal is not complete; the submitted agent remains below gold range.
- First public Archaludon mirror:
  - episode `85205692`, win over `Mega Layer eX`.
  - exact baseline versus submitted-inline replay comparison found `0`
    differences across `84` decisions.
  - report:
    `analysis_outputs/kaggle_live/submission_54526632_archattach_inline/episode_85205692_baseline_vs_inline.json`.
  - this win cannot be attributed to the RL attach residual.
- Alakazam residual follow-up:
  - the initial 21-variable policy was only `+2/2400` across three independent
    panels.
  - turn-band ablation localized both flips to the seven turn-`<=6`
    variables.
  - a focused seven-variable refinement was exactly neutral on three new
    holdouts: `+1`, `-2`, `+1` over 800 games each.
  - reject this candidate; it regressed Ebi and Ketchum variants in the middle
    holdout.
- New reusable diagnostic:
  - `tools/compare_replay_agent_actions.py` feeds a replay's observations to
    two stateful agents and records only action divergences.
- Decision:
  - keep `54526632` running; 12 public games are still too volatile for a
    replacement decision.
  - do not submit the Alakazam residual.
  - continue local work while monitoring; completion still requires a live
    submitted score in gold range.

### 2026-07-10 23:35 JST - Baseline Plateau and Balanced RL Audit

- Submission `54526632` after `38` public games:
  - record: `22-16`.
  - public score: `830.3`.
  - latest episode CSV:
    `analysis_outputs/kaggle_live/submission_54526632_archattach_inline/monitor_54526632_2335_episodes.csv`.
  - this is a live plateau, not gold range; the working rank-20 cutoff remains
    `1055.8` from the `2026-07-10T12:43:32 UTC` leaderboard snapshot.
- Public Archaludon mirrors available at this check:
  - record: `4-3` across episodes `85205692`, `85208662`, `85209049`,
    `85209585`, `85210060`, `85210566`, and `85211551`.
  - exact pre-residual versus submitted-inline comparison: `0` action
    differences over `479` target decisions.
  - the submitted residual has not changed a public action yet, so the current
    live score is effectively evidence for the rule baseline.
- Corrected evaluation bug:
  - the old even-opponent schedule fixed every named opponent to one trainee
    seat because both opponent and seat used `game_id` parity.
  - CEM and REINFORCE now pair both seats for each opponent explicitly.
  - old Alakazam CEM panels are not promotion evidence.
- Corrected low-temperature REINFORCE:
  - strict Alakazam-filtered, magnitude-pruned checkpoint scored `+20/800` on
    validation.
  - two new seed panels scored `-4/800` and `+8/800`; combined training-agent
    total was `+24/2400`.
  - eight excluded Alakazam implementations scored `625 -> 616`, so the
    candidate failed external policy/deck holdout and is rejected.
- Current action:
  - retrain the same low-temperature method on all 16 Alakazam implementations.
  - reserve remaining Alakazam agents for final external holdout.
  - do not submit before a candidate passes independent seeds, external agents,
    non-Alakazam equivalence, and Kaggle package validation.

### 2026-07-11 00:32 JST - Balanced Alakazam Blend Ready for Reset

- Current live submission `54526632`:
  - `48` public games at the latest saved check.
  - record: `28-20`.
  - score: `828.7`.
  - latest CSV:
    `analysis_outputs/kaggle_live/submission_54526632_archattach_inline/monitor_54526632_0018_episodes.csv`.
  - it remains far below the working gold cutoff and is eligible for
    replacement after the daily quota reset.
- Prepared candidate:
  - archive:
    `submission_archaludon_rl_alakblend5050_fullcontext_20260711.tar.gz`.
  - SHA256:
    `F1F82184EE318AB272218FE8C5ECE0029C9B3CF0BC4B5DF45B9B4FC6C1391DBF`.
  - unchanged 60-card Archaludon deck and current rule baseline.
  - `396` sparse, strict-Alakazam residual weights from a 50/50 blend of the
    eight-agent and sixteen-agent low-temperature REINFORCE runs.
- Generalization gates:
  - eight-agent external validation: `625 -> 632`, `+7/800`.
  - untouched seven-agent final holdout: `670 -> 677`, `+7/840`.
  - eight non-Alakazam archetypes: `320/320` exact histories.
  - training-time versus packaged policy: `140/140` exact histories.
  - unit tests: `67` passed.
- Deployment corrections:
  - the old wrapper applied learned residuals only in MAIN although training
    applied them in every selection context; this made the package equal the
    zero policy.
  - full-context wrapper now matches training exactly.
  - the archive builder preserves all `22` member names and order from the last
    validated archive and replaces only `main.py`.
- Submission plan:
  - do not use a quota slot before the expected reset around `09:00 JST`.
  - after reset, submit with message:
    `Balanced residual RL: blended Alakazam policy with external holdout gains`.
  - monitor validation immediately, then retain for enough public games unless
    there is a clear execution error or severe early failure.
  - goal remains active until the submitted agent reaches live gold range.

### 2026-07-11 01:05 JST - Combined Alakazam RL and Iono Endgame Candidate

- Goal interpretation is explicit: completion requires an actually submitted
  agent to reach the live Kaggle gold range. Local metrics, successful archive
  validation, or submitting a candidate do not complete the goal.
- Current live submission `54526632`:
  - latest fetched public record: `29-20` after `49` public games.
  - latest added game: win in episode `85226235` versus Evex Developers.
  - fetched score: `832.4552`; Kaggle CLI later listed `837.9`.
- Rejected Mega Lucario residual:
  - training-agent seed panel: `370/400 -> 374/400`.
  - excluded three-agent holdout: `338/360 -> 335/360`.
  - do not merge because the gain did not generalize across agent policies.
- Narrow Iono rule:
  - only when Iono/Bellibolt is detected and opponent prizes are `<=2`.
  - prefer one-prize Archaludon over Archaludon ex in TO_HAND and EVOLVE.
  - the earlier `<=3` version lost one local game and was narrowed.
  - the `<=2` version had zero result differences in the existing 400-game
    Iono panel while retaining the verified late-game replay correction.
- Final combined archive:
  - `submission_archaludon_rl_alakblend5050_ionoprize2_cap012_20260711.tar.gz`.
  - SHA256:
    `0164F3D0CFAA6E234A9F88F6E346C7044998CBC71ABA8E48C930A0B2EE0D26AD`.
  - 60 cards and 22 preserved archive members.
  - frozen inference settings: `top_n=3`, `residual_cap=0.12`.
- Final gates:
  - Alakazam training policy versus package: `140/140` exact histories.
  - six non-Alakazam/non-Iono buckets: `240/240` exact histories, `195/240`
    wins for both baseline and candidate.
  - standalone Iono rule versus final package: `120/120` exact histories,
    `119/120` wins for both.
  - unit tests: `67` passed.
- Packaging lesson:
  - an intermediate archive accidentally used `residual_cap=0.35` instead of
    the frozen `0.12` and failed package equivalence despite compiling.
  - archive source, weights, candidate pool, cap, temperature, and context
    coverage must all be treated as one deployable policy artifact.
  - reject `submission_archaludon_rl_alakblend5050_ionoprize2_20260711.tar.gz`.
- Quota and submission plan:
  - all five July 10 quota slots were used between `09:00` and `21:06 JST`.
  - submit the cap-0.12 archive after the expected `2026-07-11 09:00 JST`
    reset with message:
    `Balanced residual RL plus narrow Iono endgame guard`.
  - monitor validation immediately and continue until a submitted agent is
    verified in live gold range.

### 2026-07-11 01:35 JST - Live Attribution and Lucario Follow-up

- Current live submission `54526632`:
  - latest Kaggle CLI score: `842.7`.
  - `51` public games, record `31-20`, plus one validation episode.
  - latest added public game: win `85229144` versus Unicorn Great
    Tusk/Crustle.
  - current gold cutoff snapshot: rank 20 at `1068.4`.
- Full live action attribution for the Alakazam-plus-Iono candidate:
  - Alakazam: all `7/7` public games changed, `26` target decisions.
  - Iono/Bellibolt: both `2/2` games changed, `3` target decisions.
  - all other archetypes: `0/41` games and `0` decisions changed.
- Mega Lucario rule candidate:
  - force evolution of a three-Energy Active Duraludon when Riolu or Mega
    Lucario is visible.
  - live replay changes: loss `85204177` and win `85218495`, one decision each.
  - seed `8400000`: `741/800 -> 742/800`, live bucket `87 -> 88`, no other
    bucket changed.
  - seed `8500000`: `374/400 -> 374/400`, every bucket equal.
  - retain as a small, non-negative addition.
- Mega Lucario RL persistence check:
  - sweeping all eight checkpoints found checkpoint 6 at `340/360` versus
    zero `338/360` under the original inference settings.
  - under the required combined settings `top_n=3`, `cap=0.12`, it scored
    `339/360`, then `331/360` versus `332/360` on a new seed, and `457/500`
    versus `470/500` on the five training policies.
  - reject the Lucario residual; do not merge it with the Alakazam weights.
- Mirror Cinderace Cape rule:
  - broad narrow-state version: `277/600` versus baseline `278/600`.
  - refined turn-two/no-line-in-hand version: still `277/600`.
  - reject despite fixing exact live loss `85215960`.
- New combined package selected for the next submission:
  - `submission_archaludon_rl_alakblend5050_ionoprize2_lucarioreadyevolve_cap012_20260711.tar.gz`.
  - SHA256:
    `5AD444B15E1ED27B331CAC174D3D8F18A95592F2591203CF35486B71CF30595F`.
  - 60 cards, 22 preserved members, and 67 unit tests pass.
  - Alakazam training-policy/package gate: `140/140` exact, `111/140` wins.
  - Iono/Lucario rule/package gate: `300/300` exact, `285/300` wins.
  - non-target baseline/package gate: `240/240` exact, `201/240` wins.
  - promote this archive after the expected `09:00 JST` quota reset.

### 2026-07-11 02:30 JST - Late Lucario Boss-Keep Rule Rejected

- New live games after the previous check:
  - win `85234644` versus Alakazam.
  - loss `85234984` versus Mega Lucario using the exact AIB4 deck list.
  - current score after the pair: about `840.4`.
- The selected final candidate changed one Explorer discard choice in the
  Alakazam win and made no action change in the Lucario loss.
- Lucario loss analysis:
  - turn 10 Explorer kept two Archaludon ex and discarded Boss's Orders.
  - the opponent had another Riolu/Mega Lucario on the bench.
  - a proposed rule kept Boss over the second ex only in Lucario games.
- Scope correction:
  - the first form also changed Explorer choices on turns 2 and 6.
  - adding `turn >= 8` reduced the live change to the intended turn-10 choice.
- Paired local results across eight Lucario agents:
  - seed `9500000`: `754/800 -> 753/800`.
  - seed `9600000`: `370/400 -> 368/400`.
  - combined: `1124/1200 -> 1121/1200`.
- Decision:
  - reject `gtmidguard_lucariobev_crustledeckguard_iono_lucarioreadyevolve_lucariobosskeep`.
  - keep the selected final archive and its SHA256 unchanged.

### 2026-07-11 03:20 JST - Lucario Linear CEM Exhausted

- Current live update:
  - win `85238230` versus pompom555 Alakazam.
  - score after the win: about `846.9`.
  - the selected final candidate made no action change in this short
    14-decision Alakazam game.
- Corrected-seat robust CEM, training policies AIB4/Akira/Genki/Mekeh/Public:
  - matchup-wide option type, four iterations: no win gain.
  - turn-conditioned option type: best training iteration `95/100 -> 96/100`,
    worst policy bucket non-negative.
- External policies Fujiboro/Hamu/Live:
  - seed `9900000`: `560/600 -> 561/600`.
  - seed `9910000`: `561/600 -> 560/600`.
  - combined: `1121/1200 -> 1121/1200`.
- Bucket ablation on the first 300 games of both seeds:
  - turn 4: zero win difference, reward `-0.03` total.
  - turn 6: zero win difference, reward `-0.06` total.
  - turn 10: zero win difference, reward `+0.09` total.
  - turn 16: zero win difference, reward `+0.06` total.
- Decision:
  - reject the Lucario CEM weights.
  - REINFORCE checkpoint selection, type CEM, turn-type CEM, and bucket
    ablation all failed to reproduce an external Lucario win gain.
  - retain only the narrow ready-Active evolve rule in the selected archive.

### 2026-07-11 04:05 JST - Mirror Ready-Evolve Rule Rejected

- New live pair:
  - loss `85243534` versus EUGENEYEUNG Archaludon mirror.
  - win `85243602` versus Mega Lucario.
  - score after both: about `847.0`.
- Mirror loss decision:
  - turn 14, Active Duraludon had three Energy and bench Duraludon had two.
  - baseline evolved the bench; a mirror ready-Active rule changed only this
    live decision.
- Broad mirror rule, two 600-game seeds:
  - total `598/1200 -> 599/1200`.
  - policy movement included public `-4` and Toru `-3`, offset by gains on
    Ezreal/Ozanm/Victor/Shumpei.
- Turn-12-or-later refinement:
  - total again `598/1200 -> 599/1200`.
  - public bucket became neutral, but Toru remained `-2` total.
- Deck-counter check:
  - live opponent deck exactly matched `archaludon_public`.
  - public versus Toru differs by one extra Boss's Orders versus card `1213`.
  - at the live turn-14 decision only one opposing Boss and no `1213` were
    visible, so a submission could not safely distinguish the variants.
- Decision:
  - reject the mirror ready-evolve rule despite aggregate `+1/1200`.
  - do not add a hidden-deck assumption that cannot be derived from visible
    state.
  - selected 09:00 archive and SHA256 remain unchanged.

### 2026-07-11 04:35 JST - Live Mirror Win and Gold Cutoff Refresh

- New public episode `85252038` was a win over NSK.
- Both decks classified as `archaludon_metal`.
- The live score moved from about `847.1` to `851.8`.
- Current submission now has 57 public games at `35-22`, plus validation.
- Downloaded leaderboard snapshot:
  - `analysis_outputs/leaderboard_current_2026_07_11_0434/pokemon-tcg-ai-battle-publicleaderboard-2026-07-10T19_35_18.csv`.
  - rank-20 working gold cutoff: `1063.7`.
- Decision:
  - retain the selected Alakazam/Iono/Lucario candidate for the post-reset
    submission;
  - do not spend a slot before the expected 09:00 JST reset.

### 2026-07-11 14:58 JST - Balanced Residual RL Deployed After Entrypoint Fix

- First post-reset submission:
  - id `54561161`;
  - same selected Alakazam/Iono/Lucario policy;
  - `ERROR`, with both seats failing before gameplay.
- The deck, `cg/`, requirements, archive member names/order, and local behavior
  matched the known-good package structure. This repeated the two earlier
  failures where a generic runtime was appended after `agent()`.
- Deployment-only correction:
  - move the sole top-level `agent()` after the embedded runtime and final
    `choose_options()`;
  - no policy, residual weight, rule, or deck change;
  - 36 saved replays compared with zero action differences;
  - local candidate/baseline smoke games completed with zero action errors.
- Corrected archive:
  - `submission_archaludon_rl_alakblend5050_ionoprize2_lucarioreadyevolve_cap012_agentlast_20260711.tar.gz`;
  - SHA256 `D9304CF18E4EE234CB24819E97CBEB41718C477732D56B38623E8DA16722C294`.
- Corrected submission:
  - id `54561652`;
  - status `COMPLETE`;
  - validation episode `85346900` completed despite a `-1` self-play reward;
  - first public episode `85347010` was a loss to Roo333's
    Great Tusk/Crustle/Kangaskhan deck;
  - initial public record `0-1`, score `483.1`.
- Decision:
  - validation execution is fixed;
  - do not reject from one public loss;
  - collect at least the normal early 20-40 public-game window unless execution
    errors or a catastrophic repeated pattern appears.
- 15:02 JST refresh:
  - win `85347539` versus Mega Abomasnow/Kyogre;
  - public record `1-1`, score `602.4`;
  - no execution errors, so the normal observation window remains appropriate.

### 2026-07-11 16:32 JST - Early Live Window and Crustle Counterfactual Rejected

- Current submission `54561652`:
  - status `COMPLETE`;
  - score `884.1`;
  - 26 public games, record `17-9` at the reclassification refresh.
- Reclassified public record:
  - Alakazam `0-4`;
  - Great Tusk/Crustle `3-2`;
  - Archaludon mirror `2-2`;
  - Dragapult `4-0`;
  - Marnie `2-0`;
  - Mega Abomasnow/Kyogre `2-0`;
  - Mega Lucario, Ogerpon, and Starmie `1-0` each;
  - Cynthia `0-1`.
- First Great Tusk/Crustle loss `85347010`:
  - opponent deck exactly matched local Bono/Junlee;
  - submitted residual made zero action changes versus the inline baseline;
  - blanket Crustle ex suppression looked suspicious in the live sequence.
- The same ex-unlock hypothesis was refined repeatedly rather than abandoned:
  - broad active-Kangaskhan exemption;
  - healthy-Kangaskhan tempo guard;
  - full-health Raging Hammer guard;
  - Hammer guard independent of opponent HP;
  - second-seat-only exemption.
- Diagnostic traces reached `7-0`, but independent promotion panels rejected
  the family.
- Evaluation audit:
  - one intermediate evaluator incorrectly counted `result == 0` as a win in
    both seats;
  - `result` is the winning player index, so player 1 requires `result == 1`;
  - corrected second-seat-only result: baseline `491/800`, candidate `473/800`,
    delta `-18`.
- Decision:
  - reject all Kangaskhan-active ex-unlock archives;
  - do not submit a Great Tusk response from a single public loss when the
    current live record is already `3-2` and the exact local baseline is strong;
  - prioritize the repeated live Alakazam `0-4` bucket next.

### 2026-07-11 18:00 JST - Refreshed Loss Buckets

- Submission `54561652` is `COMPLETE` at 49 public games, record `30-19`,
  fetched score about `887.9`.
- Latest episode `85369337` was a win over GoodSmell's Marnie/Grimmsnarl.
- The three new Alakazam losses did not contain the previously observed
  turn-two empty-bench Duraludon-before-Pokégear decision. The narrow rule was
  also exactly neutral in a valid seeded paired panel: `676/800 -> 676/800`.
  It is rejected rather than broadened from two older replay triggers.
- Four new Archaludon mirror losses were action-identical to the inline
  baseline. Two independent games repeated a more specific prize-race state:
  at tied `2-2` prizes, with full-HP opposing Archaludon ex in both Active and
  bench, Boss targeted the one-prize card `57`.
- The earlier general mirror Boss suppression and mirror-front probes were
  noisy or harmful by seat/policy. The only admissible new probe is restricted
  to the visible `2-2` double-Archaludon state. It must preserve the earlier
  Boss choices in `85363017` step 108 and `85363997` step 118 where the full
  predicate is false.
- Empty-bench Ultra Ball did not recur across the mirror loss set, so no new
  Ultra Ball override is being tested.
- The narrow `2-2` double-Archaludon Boss guard passed direct replay gating:
  it changed only `85363017` step 126 and `85364940` step 150 among the four
  refreshed mirror losses.
- Authoritative seeded paired mirror suite:
  - valid, duplicate mismatch `0`, action errors `0`, max-step games `0`;
  - six mirror opponents, two seed windows, both seats, `1200` games;
  - baseline `559/1200`, candidate `563/1200`, delta `+4`;
  - no opponent bucket regressed; public/Ozanm/Toru/Victor were each `+1`,
    Ezreal and Shumpei were neutral.
- Candidate archive SHA256:
  `1408E6E46FCD60A4573B97ACCFB6467200080DB25C0E9FF0E2982F963821BE52`.
- Decision: retain as the next measured candidate, but do not interrupt the
  current climbing submission before its six-hour observation point for a
  local gain of only `+0.33` percentage points.
- 18:18 JST refresh: public record `31-21`, score about `880.7`. New losses
  were Toru Archaludon and Mega Lucario, followed by an Alakazam win. The
  queued mirror guard made zero replay action changes in the Toru loss
  `85369826`, so no immediate replacement is justified.

### 2026-07-11 18:25 JST - Lucario Public-Belief Recheck

- Loss `85370349` was an early two-attacker Mega Lucario race, not a failure of
  the packaged ready-evolve rule. The rule fired on turn four but selected the
  same evolution as the inline baseline.
- The suspicious turn-two Explorer selection kept Metal Energy plus
  Archaludon ex and discarded two Ultra Balls.
- Public-belief rollout at 32 determinizations showed recorded `31/32` versus
  Energy plus Ultra Ball `32/32`, but the one-sample difference failed the
  confidence gate.
- Focused independent rerun at 128 determinizations:
  - recorded action `128/128`;
  - Energy plus Ultra Ball `127/128`;
  - paired delta `-0.01562`, lower bound `-0.04125`.
- Decision: keep the prior Lucario Ultra Ball family rejected. Small public-
  belief screens must be repeated with an independent 128-sample run before a
  replay action is turned into a rule.

### 2026-07-11 18:50 JST - Policy-ensemble Rollout Candidate Rejected

- A different Explorer action, Archaludon ex plus Ultra Ball, appeared mildly
  positive across four public-belief Lucario rollout policies.
- Direct replay candidate changed only `85370349` step 22 and no Crustle,
  Alakazam, or Starmie control decisions.
- Seeded eight-policy Lucario screen:
  - valid duplicate controls;
  - baseline `295/320`, candidate `293/320`;
  - Akira `-1`, public `-1`, all other policy buckets neutral;
  - seat zero neutral, seat one `-2`;
  - action errors `0`, max-step games `0`.
- Decision: reject. Root rollout optimism did not transfer to end-to-end games.
- Current live refresh: submission `54561652` has 53 public games at `31-22`,
  score about `875.0`. New loss `85373331` was Davide Alakazam.
- Adopt the 512-state teacher reproducibility pilot and a +1.5-point blind-seed
  submission threshold from `docs/gpt_pro_strategy_review_2026-07-11.md`.

### 2026-07-11 19:30 JST - Six-Hour Live Hold and Teacher Pilot

- Submission `54561652` reached 55 public games at `33-22`; CLI public score
  was `884.7`. The two newest public games, `85376719` and `85378750`, were
  wins. It remains below the saved gold boundary near `1063.7`, but is not in
  collapse and no replacement candidate passes the stricter submission gate.
- The `+4/1200` narrow mirror candidate remains an internal ablation, not a
  Kaggle candidate under the required `+1.5` blind win-rate-point threshold.
- A leakage-free public-belief teacher now evaluates multiple compatible deck
  hypotheses, three opponent policies, and two own continuation policies.
- On 32 frozen states at four particles per scenario, top-action agreement was
  `56.25%`, sign agreement `78.54%`, and high-margin top agreement `3/3`.
- Positive-LCB actions outside the current top-three support occurred in both
  batches for `2/32` states (`6.25%`). Complete-action learning has measured
  headroom, but teacher calibration must improve before neural distillation.
- Support split: 15 real-catalog-compatible states had sign agreement `85.71%`;
  17 states needing synthetic unknown variants had only `71.96%`. Future
  learned overrides will abstain on unsupported public beliefs and fall back
  to the current rule/residual policy.

### 2026-07-11 20:36 JST - Exploratory Submit Policy and Mirror Probe

- User policy now permits informative Kaggle probes when the current and prior
  mature submissions are both below 1000. The strict `+1.5` local point gate
  remains the champion-promotion gate, not an absolute ban on live probes.
- Prior submission `54561652` matured to 58 public games, `35-23`, score about
  `884.90`, with no execution error.
- Submitted id `54570077`: narrow tied-`2-2`, double-Archaludon mirror Boss
  guard. Local mirror evidence was `559/1200 -> 563/1200`, every one of six
  policy buckets nonnegative, action errors `0`, max-step games `0`.
- Initial state was `PENDING`; monitor validation before spending another slot.
- Supported teacher confirmation at 64 states and four particles/scenario was
  valid but just below the sign gate (`79.74%`). Only six stable positive-LCB
  labels remained, so neural ranker training is paused.
- Initial frozen-policy deck factorial matrix: add one of Relicanth `57`, Full
  Metal Lab `1244`, Jumbo Ice Cream `1147`, Night Stretcher `1097`, or Metal
  Energy `8`; cut one of Ice `1147`, Lillie `1227`, FML `1244`, Stretcher
  `1097`, or Energy `8`; exclude no-op pairs and protect the core attackers,
  search engine, non-ex pair, Cape, and Boss package.
- Validation completed without an execution error. The first two public games
  were both wins, moving the score from `600` to `752.9`; continue collecting.
- The last loss of prior submission `54561652`, episode `85388354`, was Mega
  Lucario and outside the new mirror predicate.
- The 21-arm g4 factorial screen used 14 policy buckets, both seats, and 112
  games per arm. Top non-regressing screens versus the shared baseline were:
  - Relicanth `57` for Stretcher `1097`: total `+7`, weak `+5`, strong `+2`;
  - fourth Stretcher for one Ice: `+6`, weak `+4`, strong `+2`;
  - thirteenth Energy for one Lillie: `+6`, weak `+2`, strong `+4`;
  - fourth Ice for one Lillie: `+4`, weak `0`, strong `+4`.
- These are low-sample rankings only. All four advanced to duplicate-controlled
  seeded paired evaluation over the same 14 policy buckets.

### 2026-07-11 21:06 JST - Relicanth Deck Factorial Probe

- Four g4 finalists received duplicate-controlled, engine-seeded evaluation
  over 14 policy buckets, both seats, and 336 candidate games per seed window.
- First seed window:
  - Relicanth `57` for one Stretcher `1097`: `259 -> 273`, delta `+14`;
  - fourth Stretcher for one Ice: `259 -> 263`, delta `+4`;
  - thirteenth Energy for one Lillie: `259 -> 245`, delta `-14`;
  - fourth Ice for one Lillie: `259 -> 244`, delta `-15`.
- Independent Relicanth seed window: `247 -> 248`, delta `+1`.
- Combined Relicanth evidence: `+15/672` (`+2.23` points), one-sided
  lower-90 `+0.05` points; weak group `+8/432`, strong group `+7/240`, seats
  `+7/+8`. Duplicate mismatch, action errors, and max-step games were all `0`.
- Remaining combined policy regressions were Lucario `-1`, Dragapult `-2`,
  and Cynthia `-2`; mirror net `0`, Alakazam `+9`, Great Tusk `+4`, Starmie
  `+6`, and Marnie `+1`.
- Mirror probe `54570077` had five public games at `3-2`, score `668.0`, with
  no mirror game. It was replaced under the user's below-700 probe policy.
- Submitted Relicanth/Stretcher archive as id `54570845`:
  `submission_archaludon_rl_agentlast_relic1_cutstretcher_20260711.tar.gz`;
  SHA256 `31C1FCAD5AA5053B15A1A17D654DB89729FCB43A5EDD9A4BDF43B2B60210FC91`.
  Validation completed successfully at score `600.0`; no public games yet.
- Compensation-cut ablation on the same Relicanth add:
  - cut Stretcher: `+15/672`;
  - cut Lillie: `-20/672`, weak group `-22`, both seats and both seeds negative.
  - Decision: keep the submitted Stretcher cut. Complete add/cut swaps, not
    independent card additions, are the correct experimental unit.

### 2026-07-11 21:25 JST - Relicanth Probe Early Live Check

- Submission `54570845` passed validation and reached four public games at
  `4-0`, public score `939.48`, with no execution errors.
- The wins covered Mega Abomasnow/Kyogre, Dragapult, Starmie/Froslass, and
  Mega Lucario. This is broad early coverage but not yet a mature estimate.
- Submission policy: use the five daily slots actively when both the current
  and preceding mature submissions remain below 1000; replace a roughly-700
  or lower result after basic diagnosis. Do not replace a rising, few-game
  submission solely because it has not yet reached 1000. Hold this probe to
  about 20 public games unless it clearly collapses or errors.
- Rejected Dragapult guard: suppressing Relicanth only when the observed
  matchup classifier already returned Dragapult was neutral in all 48 exact-
  policy seeded games. It did not fix seat-one losses `46071103` or
  `46071108`, because the harmful search/setup decision occurred before public
  evidence identified the archetype. Do not package this guard.
- At six public games the live record was `4-2`, score `816.79`. Losses:
  - `85394807`, Ogerpon toolbox: Cornerstone was handled correctly, but after
    it left play Cubchoo used Snotted Up. That attack explicitly prevented the
    defending Archaludon from attacking on its next turn, so the engine
    correctly exposed no attack option. This was not an attack-ranking error;
    the simple priority patch was rejected.
  - `85395306`, Alakazam: two ex attackers were KOed by Powerful Hand;
    Relicanth arrived late and Raging Hammer dealt only 80 to a 90-HP target.
    This is a known strong-board Alakazam loss, not yet enough for a new rule.
- Rejected after third-seed direct confirmation:
  `submission_archaludon_rl_agentlast_stretcher4_cutice2_20260711.tar.gz`.
  It changes Stretcher `3 -> 4` and Ice `3 -> 2`. Although it was `+21/672`
  versus the older shared baseline, direct comparison with the live Relicanth
  swap was only `+5/1008` across three seeds, with seat-one and several policy
  regressions. Do not submit. SHA256
  `2A371AA8399487DD46776C61F43297F0CC2AF82636247B95435D468CE1F9AEA3`.
- 21:43 JST refresh: two wins followed the two losses. Public record `6-2`,
  score `900.89`. The current probe is recovering and remains active.
- 21:55 JST refresh: public record `7-4`, score `866.99`. Episode `85396751`
  was an Archaludon mirror loss. The live agent used both Stretchers and all
  three visible Ice copies; the opponent won by a final-prize Boss gust onto
  an exposed 130-HP Duraludon. It does not share the Stretcher4 seeded mirror
  flip pattern.
- Episode `85397745` was also an Archaludon mirror loss, but it followed a
  different attacker/resource race. The two live mirror losses do not share a
  safe public-state predicate; only `85396751` supports a narrow final-Boss
  prize-map concern, and prior broad Boss guards were unstable.
- 22:02 JST refresh: public record `8-4`, score `889.36`.
- Current leaderboard snapshot:
  `analysis_outputs/leaderboard_current_2026_07_11_2200/`.
  Rank 20 / working gold cutoff is `1054.5`; team `rurumi` is rank 424 at
  `889.3` in the snapshot.
- Stage-two deck search fixes the submitted Relicanth swap as the incumbent
  and generates 16 complete add/cut arms over Stretcher, Ice, Full Metal Lab,
  Metal Energy, and Lillie cuts. This prevents an older shared baseline from
  making a merely adjacent deck look stronger than the deployed candidate.
- Stage-two result: reject both g4 leaders. Ice4/FML2 fell from `+24/112` in
  selection to `+2/336` independent; Stretcher3/FML2 fell from `+21/112` to
  `+4/336`. Both were seat-sensitive and regressed in every Alakazam policy.
  Do not pool selected-screen and confirmation deltas.
- 22:20 JST refresh: public record `11-7`, score `880.02`; still above the
  early-replacement threshold and two games short of the maturity checkpoint.
- 22:26 JST maturity checkpoint: public record `13-7`, score `908.61`, with
  four consecutive wins. Do not replace while recovering.
- Seven-loss classification at 19 public games: Alakazam `3`, Archaludon
  mirror `2`, Starmie/Froslass `1`, Ogerpon toolbox `1`.
- Two of three Alakazam losses (`85400387`, `85395306`) continued acquiring or
  benching extra Duraludon-family bodies after two ex KOs with the opponent at
  three or fewer prizes. SantaClaws `85398769` followed a different fragile
  one-prize exchange. A narrow low-prize setup cap is under local evaluation;
  it changes only two digimagi replay decisions and leaves the other two loss
  replays action-identical.
- The low-prize cap is rejected after seeded evaluation: Alakazam `158/192 ->
  158/192`, non-Alakazam controls `53/72 -> 53/72`, zero changed winners.
- 22:38 JST refresh: public record `13-10`, score `869.89`, after three new
  consecutive losses. The submission is mature and below 1000, so a new live
  probe is allowed once a locally valid replacement is identified.

### 2026-07-12 10:00 JST - Mature Relicanth Probe Refresh

- Submission `54570845` now has `67` public games, record `34-33`, fetched
  score `843.496`; this is mature and below 1000. Latest episode CSV:
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/monitor_54570845_20260712_0000_retry_episodes.csv`.
- Full refreshed archetype record:
  - Alakazam `5-12`;
  - Archaludon mirror `8-8`;
  - Great Tusk/Crustle `3-3`;
  - Mega Lucario `8-2`;
  - Marnie `0-2`;
  - Ogerpon toolbox `0-2`;
  - remaining classified field `10-6`.
- The current and preceding mature submissions are both below 1000, so the
  live-feedback policy permits another evidence-backed probe. No replacement
  is submitted yet: the active Gold-rollout research has only narrow Marnie
  tempo hypotheses at p4, while the dominant live loss buckets remain
  Alakazam and mirror. Wait for p8/p16 and require adjacent-bucket preservation
  before using a competition slot.
- Current leaderboard rank-20 / working gold cutoff is about `1092.1`.
- Review of all 12 Alakazam losses found a repeated late-tempo shape, not a
  repeated opening-choice error: by turn 6-7 the opponent showed at least two
  Alakazam-line bodies in 10/12 losses, while the Cinderace bridge often fell
  before a second Archaludon attacker stabilized. The only new testable
  hypothesis is a late, visible-two-Alakazam backup-attacker priority; it must
  pass the fixed 800-game Alakazam panel and adjacent controls before packaging.
- Review of all eight mirror losses found no new promotion-ready common rule.
  Four were Cinderace-front resource races; the lone final-Boss bench guard is
  still isolated to episode `85396751` and remains below the `+18/1200`
  promotion threshold without further evidence. Do not revive broad Boss or
  ready-evolve variants.

### 2026-07-12 11:53 JST - Alakazam Backup-Line Rejection

- The late public-Alakazam backup-line candidate changed five decisions in
  four of the twelve live Alakazam losses while leaving four sampled adjacent
  replays action-identical.
- Clean fixed evaluation over four Alakazam policies, both seats, and 100
  seeds per seat was negative: baseline `605-195` (`75.63%`), candidate
  `601-199` (`75.13%`), delta `-4/800` (`-0.50` points).
- Bucket deltas were Rmy `-2`, Majkel `-2`, digimagi Ant `0`, and digimagi
  Osel `0`. All four lost wins came from seat zero; seat one was unchanged.
- Archaludon mirror, Mega Lucario, Great Tusk/Crustle, and Marnie controls were
  exactly `315-85` for both policies. Duplicate mismatch, action error, and
  max-step counts were all zero.
- The evaluator's first output directory is invalid because two identical
  processes briefly wrote concurrently. The accepted clean evidence is
  `analysis_outputs/relicprobe_alakbackup_visible2_v1_comparison_20260712.json`
  and the two directories ending in `_clean`.
- Decision: reject the candidate. Do not package or submit it, and do not
  infer that extra Archaludon-line acquisition solves the dominant live loss
  pattern merely because it changes replay decisions.
- 11:56 JST live refresh added one Alakazam win, episode `85501576` versus
  PyJa. Submission `54570845` is now `35-33` over 68 public games at score
  `848.14`; no execution error occurred. This does not rescue the rejected
  local override, whose deterministic target panel remains negative.

### 2026-07-12 13:26 JST - Third Marnie Loss Applicability Check

- Submission `54570845` is now `35-34` over 69 public games at fetched score
  `844.143`. The only new episode is loss `85512671` versus Larry's
  `marnie_grimmsnarl` deck. Outputs are under
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/monitor_54570845_20260712_1326_new_summary`.
- The three retained p8 Marnie proposals do not provide a safe correction:
  - turn 12 had a 10-HP Active Archaludon ex and legal retreat, but every bench
    target was an unevolved Duraludon rather than a healthy energized attacker;
  - turn 18 allowed heal and attack, but 220 damage did not KO the visible
    290-HP Grimmsnarl, so healing before attacking was necessary protection;
  - the legal evolves were from bench or full-HP states, not the retained
    40-HP Active sacrifice state.
- Decision: fail closed. Do not generalize HP-only retreat, attack-before-heal,
  or delay-evolve rules from this replay. The loss reflects Larry's repeated
  attacker removal and our depleted replacement line, not a confirmed replay
  teacher trigger.

### 2026-07-12 14:26 JST - kkkk Great Tusk Deck-Out Loss

- Submission `54570845` is now `35-35` over 70 public games at fetched score
  `838.953`. The only new episode is loss `85520425` versus kkkk's
  `great_tusk_crustle` deck. Outputs are under
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/monitor_54570845_20260712_1426_new_summary`.
- This was a deck-out loss, not a prize, board-wipe, timeout, or execution
  failure. At terminal our deck was `1` versus the opponent's `22`, both sides
  still had all prizes, and our board remained Active plus four Bench Pokemon.
- Great Tusk/Dwebble was visible by turn 2, the first Crustle by turn 14, and
  two Crustles controlled turns 20-44. Existing matchup classification and
  deckguard conditions were therefore available; the replay is consistent
  with avoiding Archaludon ex and Relicanth under that guard.
- Relicanth was discarded without entering play, and both available Night
  Stretchers were also discarded. The episode does not support blaming the
  Relicanth-for-third-Stretcher swap: a third Stretcher would not replenish the
  deck and no missing recovery target explains the loss. Existing paired
  evidence for the exact swap remains `+4` in Great Tusk and `+15/672` overall.
- Decision: no candidate change. The failure is a proactive prize-race gap
  against a stronger control policy, not evidence for undoing the swap or
  broadly loosening deckguard.

### 2026-07-12 14:56 JST - Alakazam and Dragapult Loss Refresh

- Submission `54570845` now has `73` public games, record `36-37`, fetched
  score `833.982` and latest CLI score `830.1`. The three new games are loss
  `85523408` versus konaito Alakazam, win `85525297` versus yuuri
  Starmie/Froslass, and loss `85525378` versus SkySell Dragapult. Full summary:
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/loss_summary_20260712_1456_all/submission_54570845_73eps_archetype_summary.csv`.
- Current major buckets are Alakazam `6-13`, Archaludon mirror `8-8`, Great
  Tusk/Crustle `3-4`, Mega Lucario `8-2`, Dragapult `2-2`, and Marnie `0-3`.
- Alakazam loss `85523408` repeats the known late setup collapse: two opposing
  Alakazam were established by turn 6, both Archaludon ex were removed by
  turns 9-11, and turn 12 left only a one-Energy Active Duraludon plus
  Relicanth with the opponent at one prize. The rejected visible-two backup
  rule changes only two early turn-4 multiselect prompts and not the decisive
  late states; its clean fixed panel remains `605/800 -> 601/800`.
- Dragapult loss `85525378` is a board-damage race, not evidence against
  Relicanth. Relicanth enabled a 340-damage Raging Hammer knockout and another
  Dragapult knockout, but spread damage left the replacement attacker at 40 HP
  for the final return KO. Suppressing Relicanth would remove the only proven
  320-plus damage line, and a third Night Stretcher is not implicated.
- Decision: no replacement candidate. The current and preceding mature
  submissions remain below 1000, so a justified probe is allowed, but neither
  replay supplies a predicate that improves its target bucket without a clear
  adjacent-bucket risk.

### 2026-07-12 15:26 JST - Okidogi and Alakazam Follow-Up Losses

- Submission `54570845` now has `75` public games, record `36-39`, and latest
  CLI score `826.9`. New losses are `85527810` versus Okidogi/Barbaracle and
  `85528347` versus Alakazam. Outputs:
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/monitor_54570845_20260712_1526_episodes.csv`
  and
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/loss_summary_20260712_1526_all/submission_54570845_76eps_archetype_summary.csv`.
- Current major buckets are Alakazam `6-14`, Archaludon mirror `8-8`, Great
  Tusk/Crustle `3-4`, Mega Lucario `8-2`, Marnie `0-3`, and
  Okidogi/Barbaracle `0-2`.
- In `85527810`, turn-4 search benched Relicanth without immediate use. It was
  gusted and KO'd before contributing, after which repeated 340-HP attackers
  removed the two Archaludon-line boards. The prior Okidogi loss repeats board
  exhaustion but not the Relicanth sequence. Only one of the two available
  Night Stretchers was played, so this does not support restoring a third
  Stretcher. A future no-idle-Relicanth guard would require at least `+2/24`
  paired Okidogi games with no lost baseline win before implementation.
- In `85528347`, our turn-8 KO faced two already visible backup Alakazam. The
  replacements then KO'd Archaludon ex, Cinderace, and the Cape Archaludon ex
  in sequence. This is the known late-tempo multi-Alakazam failure and does
  not demonstrate a better legal continuation; the related visible-backup
  override remains rejected at `605/800 -> 601/800`.
- Decision: no candidate implementation and no competition submission. Both
  losses refine evaluation slices, but neither satisfies the requirement for
  a positive paired target delta with adjacent-bucket preservation.

### 2026-07-12 15:56 JST - Rocket Mewtwo Recovery Win

- Submission `54570845` added win `85531622` versus Rocket
  Mewtwo/Spidops. It now has `76` public games, record `37-39`, and fetched
  score `831.810`. Episode and refreshed summaries are under
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/20260712_1556_episodes.csv`
  and
  `analysis_outputs/kaggle_live/submission_54570845_relicprobe/20260712_1556_archetype_summary.csv`.
- No new loss bucket or execution error appeared. Decision: keep the current
  submission running and spend no competition slot without a locally valid
  candidate.

### 2026-07-12 16:29 JST - Stretcher4 Exploratory Probe Precommit

- User direction now prioritizes using otherwise-idle daily slots for
  informative live probes; the latest competition submission is about 19
  hours old. Select the strongest packaged but not yet live-tested deck
  alternative:
  `submission_archaludon_rl_agentlast_stretcher4_cutice2_20260711.tar.gz`,
  SHA256
  `2A371AA8399487DD46776C61F43297F0CC2AF82636247B95435D468CE1F9AEA3`.
- Complete deck delta from the live Relicanth incumbent: remove Relicanth `57`
  and one Jumbo Ice Cream `1147`; add two Night Stretcher `1097`. Final counts
  are Stretcher `4`, Ice `2`, Relicanth `0`, and `60` total cards.
- Direct frozen-policy comparison against the live Relicanth deck was only
  `+5/1008` over three seed windows. This is below the normal promotion gate
  and had seat-one plus several policy regressions, so the archive remains an
  exploratory factorial probe rather than a promoted candidate.
- Hypothesis: extra recovery and removal of an idle one-prize Relicanth may
  improve repeated-attacker board exhaustion, especially the live Alakazam,
  Marnie, and Okidogi buckets. Known risk is losing valid Raging Hammer lines,
  reducing Ice recovery, and repeating seat-sensitive mirror/Alakazam losses.
- Archive revalidation passed: 22 members, callable `agent`, Python compile,
  and exact 60-card deck. Monitor validation immediately, then collect at
  least 20 public games unless score falls near/below 700 with a clear loss
  pattern. Rollback is
  `submission_archaludon_rl_agentlast_relic1_cutstretcher_20260711.tar.gz`.
- Submitted successfully as Kaggle submission `54599496` at `16:29:46` JST.
  The CLI uploaded the archive and then raised a Windows CP932 display error
  on the accented competition name; a fresh submission-list query confirmed
  that no retry was needed and prevented a duplicate slot use.
- Kaggle validation completed without an execution error at score `600.0`.
  Validation episode `85537748` completed normally; target-side reward was
  `-1` in the self-validation game, which is not an execution failure. Initial
  monitor output:
  `analysis_outputs/kaggle_live/submission_54599496_stretcher4probe/monitor_54599496_20260712_1633_episodes.csv`.

### 2026-07-12 16:58 JST - Stretcher4 Early Live Diagnosis

- The first six public games are `3-3`; fetched score recovered from `573.565`
  after three games to `651.135`. The latest three-game window was `2-1`, so
  the submission is below 700 but actively recovering and is not replaced yet.
- Initial losses were mirror episode `85538778` and Alakazam episode
  `85539271`. The next window added one Mega Lucario loss, one Mega Lucario
  win, and one mirror win (`85540710`).
- Mirror loss `85538778` is the only initial result that plausibly implicates
  the deck delta. Both Ice copies were exhausted by turn 11 while the opposing
  Ice4 list healed four times and won the attrition race. Extra Stretcher was
  used productively on turn 13, and absent Relicanth had no demonstrated role.
  This supports an Ice-capacity risk, not a full rollback conclusion.
- Alakazam loss `85539271` used Stretcher productively on turns 10 and 14 but
  lost the final tempo exchange after the rebuilt Archaludon ex fell. Ice was
  ineffective against the knockout line and Relicanth absence was irrelevant.
  The prior visible-backup override remains rejected at `605/800 -> 601/800`.
- A requested exact seeded local rollback comparison produced no games:
  Windows `cg.dll` does not export `BattleStartSeeded`, while the seeded Linux
  `libcg.so` cannot load on Windows. No unseeded numbers were substituted and
  no invalid win-rate claim is recorded. Evidence:
  `analysis_outputs/mirror_eval_20260712_001/evaluation_blocked.md`.
- Decision: continue to the next meaningful public checkpoint. Replace early
  only if the recovery reverses and a locally justified candidate exists;
  do not duplicate-submit the Relicanth rollback while it is already the
  preceding active submission.

### 2026-07-12 17:10 JST - Historical Silver Revalidation Precommit

- Fresh public leaderboard snapshot:
  `analysis_outputs/leaderboard_current_2026_07_12_1710/`.
  There are `4,853` teams; rank 20 / gold boundary is `1083.6`, while rank
  100 / silver lower boundary is approximately `991.2`.
- Known Archaludon teams Xander and daiki_H are currently rank `194` at
  `952.2` and rank `310` at `915.5`, outside silver. ShumpeiNomura is rank
  `20` at `1083.6`; public-safe team submission lookup identified current
  submission `54588240`, and all `81` fetched episodes classify the acting
  team as the same Archaludon deck. The team's second active score is `998.1`,
  also inside silver. Public episode `85543431` confirms that second submission
  `54588173` is Archaludon too; it changes the gold-boundary deck by
  `-1 Energy, -1 Full Metal Lab, +2 Switch`. Archaludon therefore exists in
  both the current gold-boundary and silver evidence, despite being absent
  from the `1250+` sample.
- Two historical own candidates are distinct:
  - highest transient score: old `gtmidguard`, browser range up to about
    `1072`, followed by a material decline;
  - strongest documented sustained Archaludon run:
    `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`,
    which reached `1045.58`, had a `12-1` public start, remained above 1000
    through multiple later checkpoints, and was `18-8` after 26 public games.
- Prefer the sustained `crustledeckguard` package for a publishability test.
  In the historical direct local comparison it scored `0.7604` on equal
  selected buckets versus old `gtmidguard` at `0.7361`, with better Alakazam
  and live-style Archaludon coverage.
- Exact archive revalidation: SHA256
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`,
  `2,008,160` bytes, `22` archive members, root `main.py`, callable `agent`,
  Python compile pass, and exactly `60` deck rows. Deck counts are Energy 12,
  Duraludon/Archaludon ex/Cinderace 4 each, non-ex Archaludon 2, Stretcher 3,
  Ice 3, Full Metal Lab 3, and the preserved trainer core.
- Live hypothesis: the historically sustained rules and deck can still clear
  the current silver boundary near `991`, despite the field's stronger
  Alakazam/Great Tusk concentration. Known risks are Alakazam late-board
  pressure, Marnie replacement-line exhaustion, and rating decline after the
  early high-score window.
- Publication gate: do not publish a Kaggle Code as a current silver agent
  merely from the historical peak. First require a fresh valid submission,
  no execution error, and a meaningful live silver observation. The Notebook
  must report the full score trajectory and known weaknesses, not only the
  peak.
- Submitted the sustained historical package as id `54600598` at
  `2026-07-12 17:14:53 JST` with message
  `Historical silver revalidation: sustained Archaludon crustle guard`.
  Validation completed without an execution error at score `600.0`; episode
  `85543018` was a normal self-validation loss for the target seat. No public
  game had completed at the first post-validation fetch.

### 2026-07-12 17:28 JST - Silver Revalidation And Private Code Draft

- Submission `54600598` opened with two public wins:
  - `85543567` versus Gronk Great Tusk/Crustle, `600 -> 759.08`;
  - `85544028` versus TA Alakazam, `759.08 -> 838.17`.
- Public record is `2-0`, not `0-2`; the first automated collector summary
  inverted the prose label, while its episode CSV and archetype summary both
  correctly record target reward `+1` and `2-0`. The CSV is authoritative:
  `analysis_outputs/kaggle_live/submission_54600598_historical_silver_revalidation/20260712_172637_episodes.csv`.
- This is a favorable start against the two dominant high-score archetypes,
  but `838.17` is still about `153` points below the current silver boundary
  near `991.2`. Do not publish the agent as current-silver evidence yet.
- Built local private Notebook draft:
  `notebook_output/ptcg-archaludon-rule-agent-silver-recheck/notebook.ipynb`.
  It contains the full rule source, the named 60-card deck, transparent
  historical-score caveats, official-engine discovery, clean archive build,
  and structural verification.
- Pushed private Kaggle Code version 1:
  `rurururumi/ptcg-archaludon-rule-agent-silver-recheck`. It completed without
  an execution error and generated a clean 13-member archive with SHA256
  `45ac500420acde056c0209104fb81de0d2a4bbb47fee93152ecd1daf596f9580`.
  Generated `main.py`, `deck.csv`, and `requirements.txt` are byte-identical
  to the historically submitted package; bytecode caches are excluded.
- Publication gate remains unchanged: keep the Code private until fresh live
  evidence reaches silver with a meaningful number of public games, then add
  the complete trajectory and matchup record before changing visibility.
- Private Notebook version 2 adds an actual Linux import of the generated
  package after copying the official engine. Kaggle completed it and printed
  `agent entrypoint import: OK`. The archive remains clean at `13` members;
  post-import bytecode caches are working-directory outputs and are not inside
  the archive. Version-2 archive SHA256 is
  `0c05eb2ffbad6299b3eea677bab7bae39671dafebcba4f901af0833ea1e01813`.
- Two additional public games changed the live path to
  `600 -> 759.08 -> 838.17 -> 912.22 -> 812.08`. The new Iono/Bellibolt game
  `85544493` was a win; Mega Lucario episode `85544979` was the first loss.
  Public record is `3-1`. A single loss after only four public games is not a
  silver failure verdict, but the draft remains private because the current
  score is well below `991.2` and the trajectory is highly volatile.

### 2026-07-12 17:40 JST - Historical Peak-Rule A/B Precommit

- `54600598` added Iono/Bellibolt loss `85545458` after the Mega Lucario loss.
  It is `3-2` over five public games at `750.82`; the same Iono/Bellibolt
  archetype also produced win `85544493`, so this is not yet a deterministic
  matchup collapse.
- Both active submissions are now around or below the early replacement band.
  Use a third daily slot for a clean historical rule-policy A/B rather than a
  new deck mutation.
- Candidate:
  `submission_archaludon_gtdeckguard_iono_alaklive_line4markers_gtstrict58_gtmidguard.tar.gz`.
  It uses the exact same `deck.csv` as `crustledeckguard` (SHA256
  `08421ae98d080a1ee3ba28f93da0a99c79287a2bc6f57529fda2e4ca56cc7c6a`)
  and changes only the rule source. This isolates policy from deck power.
- Historical evidence:
  - highest observed score panel about `1072`, followed by decline;
  - direct local selected-bucket score `0.7361` versus `crustledeckguard`
    `0.7604`;
  - stronger historical Great Tusk (`45/48` vs `41/48`), Lucario (`45/48`
    vs `44/48`), and Marnie (`42/48` vs `41/48`) rows, but weaker Alakazam
    and live-style mirror rows.
- Hypothesis: the older peak rule balance may better cover the immediate
  Lucario/control pressure than the sustained package, while the identical
  deck makes live differences attributable to rules. Known risk is repeating
  the historical Alakazam/mirror decline.
- Archive validation: SHA256
  `C8D3D6F810A9293C961A1595DE0DB15D49C28741B1D325AEF8896156DFAFABC7`,
  `1,991,738` bytes, `13` clean members, exact 60-card deck, compile pass,
  source-extraction equality, and callable `agent`.
- Publication rule: the private Code currently contains the sustained
  `crustledeckguard` source. If this peak-rule policy is the one that freshly
  reaches silver, regenerate and re-execute the Notebook from this archive
  before publication; never publish a source that differs from the scored
  submission.
- Submitted the peak-rule A/B as id `54601378` at `17:40:40 JST` with message
  `Historical peak-rule A/B: same Archaludon deck, alternate policy`.
  Initial status is `PENDING`; monitor validation before interpreting score or
  spending another slot.

### 2026-07-12 17:50 JST - Current Silver Evidence And A/B Opening

- Fresh leaderboard snapshot:
  `analysis_outputs/leaderboard_current_2026_07_12_1746/`. It contains `4,855`
  teams; rank 20 is `1083.5` and rank 100 is `991.5`.
- ShumpeiNomura moved from rank 20 / `1083.6` in the 17:10 snapshot to rank 21
  / `1076.1`. This is current high-silver evidence, not a claim that the deck
  remains continuously in gold. Submission `54588240` now has 83 fetched
  episodes and last fetched score `1076.19`.
- Shumpei's second Archaludon submission `54588173` has 67 episodes and last
  fetched score `993.80`, still narrowly above the current silver lower
  boundary. Both active deck versions therefore independently support the
  claim that Archaludon is currently silver-capable.
- Own sustained submission `54600598` is `5-3` in public games and `809.57`.
  Wins are Great Tusk/Crustle, Alakazam, Iono/Bellibolt, Dragapult, and
  Starmie/Froslass; losses are Mega Lucario twice and Iono/Bellibolt. It has
  not freshly reached silver.
- Same-deck peak-rule submission `54601378` completed validation without an
  execution error. Its first two public games, episodes `85546377` and
  `85546844`, were both wins over Starmie/Froslass, moving
  `600 -> 721.22 -> 821.14`. This is a useful positive opening but not yet a
  broad-meta or silver verdict because both opponents share one archetype.
- Keep the prepared Kaggle Code private. Publish only after one exact source
  version reaches silver over a meaningful public trajectory; if `54601378`
  wins the A/B, rebuild the Notebook from that exact policy before publishing.

### 2026-07-12 18:28 JST - A/B Recovery And Lucario Diagnosis

- Fresh leaderboard snapshot:
  `analysis_outputs/leaderboard_current_2026_07_12_1825/`. It contains `4,856`
  teams; rank 20 is `1090.4`, rank 100 is `988.8`, and team `rurumi` is rank
  503 at `876.9` in that snapshot. ShumpeiNomura remains high silver at rank
  22 / `1076.5`.
- Sustained submission `54600598` has 17 public games, record `11-6`, and last
  fetched score `872.91`. Its main weak buckets are Mega Lucario `1-3`,
  Archaludon mirror `2-2`, and Iono/Bellibolt `1-1`; it is `2-0` versus
  Alakazam and undefeated in five single-game buckets.
- Peak-rule submission `54601378` has 12 public games, record `9-3`, and last
  fetched score `897.97`. It is Starmie/Froslass `3-0`, Dragapult `2-0`, Hop
  `2-0`, Mega Lucario `1-2`, and Alakazam `1-1`. The recent sequence recovered
  from `650.56` after two Lucario losses to `897.97`, so replacing it now would
  violate the recovering-submission guard.
- Read-only replay diagnosis compared sustained Lucario losses `85544979`,
  `85546415`, `85549786` and peak-rule losses `85547319`, `85547804`. All five
  converge on repeated Mega Lucario knockouts followed by a single-attacker or
  empty-bench state. No replay exposes a clear missed Boss target or a
  cross-policy decision that demonstrably reverses the game.
- The shared weakness is insufficient protected follow-up attackers, mixed
  with setup variance. A Lucario-only rule that avoids further Cinderace
  investment when at least two Duraludon are already available is only a test
  hypothesis, not a promoted fix: one sustained replay has a viable Cinderace
  opening, so the broad rule risks adjacent fast-matchup regressions.
- Decision: no new candidate and no new submission. Keep both A/B policies
  running. Any Lucario guard must beat both policies on identical Lucario
  seeds and preserve Great Tusk, Starmie/Froslass, Alakazam, and Iono before it
  can consume a live slot. Keep the Kaggle Code private until one exact source
  reaches the current silver boundary over a meaningful trajectory.

### 2026-07-12 18:53 JST - Mature A/B Checkpoint Below Silver

- Fresh leaderboard snapshot:
  `analysis_outputs/leaderboard_current_2026_07_12_1853/`. It contains `4,857`
  teams; rank 20 is `1083.0`, rank 100 is `987.9`, and the snapshot placed team
  `rurumi` rank 255 at `932.2`. ShumpeiNomura remains high silver at rank 23 /
  `1075.0`.
- Peak-rule submission `54601378` has 19 public games, record `14-5`, and last
  fetched score `940.98`. Through the first 18 games its matchup record was
  Alakazam `2-2`, Mega Lucario
  `1-2`, Archaludon mirror `3-1`, Starmie/Froslass `3-0`, Dragapult `2-0`, and
  Hop/Trevenant `2-0`.
- Sustained submission `54600598` has 26 public games, record `18-8`, and last
  fetched score `919.56`. Its broad spread includes Archaludon mirror `2-3`,
  Mega Lucario `1-3`, Alakazam `3-1`, Iono/Bellibolt `1-1`, and undefeated
  records across eight additional archetypes.
- Neither submission has reached the current silver lower boundary, but both
  have positive mature records and have recently recovered through long win
  runs. They are not early failures around 700, and there is no locally
  promoted replacement candidate.
- The low-cost collector initially produced `missing` archetypes because its
  deck extraction output was empty. The root reran extraction with Python
  3.11 and regenerated the authoritative summaries under `decks_1853_fixed`
  and `loss_summary_1853_fixed`; no score or W-L result was affected.
- Decision: do not consume another submission slot. Continue the same-deck A/B
  until the silver gate is reached or the trajectories clearly plateau below
  1000. Keep the private Code unpublished; the exact-source requirement and
  silver evidence gate remain unchanged.

### 2026-07-12 19:23 JST - Near-Silver Peak Then Upper-Band Reversal

- Fresh leaderboard snapshot:
  `analysis_outputs/leaderboard_current_2026_07_12_1923/`. It contains `4,858`
  teams; rank 20 is `1082.2`, rank 100 is `989.0`, team `rurumi` is rank 304 /
  `918.2`, and ShumpeiNomura is rank 27 / `1066.6`.
- Peak-rule submission `54601378` reached `974.84`, only about 14 points below
  the current silver boundary, after wins over Great Tusk/Crustle, Dragapult,
  and an Archaludon mirror. It then lost four consecutive games to Alakazam,
  Alakazam, Dragapult, and Archaludon mirror, ending the fetch at `918.21`.
  Authoritative public record is `17-9`; the collector's `18-9` included the
  validation win.
- Sustained submission `54600598` ended at `892.10`, public record `21-12`.
  Its cumulative primary weak bucket is Archaludon mirror `4-6`, followed by
  Mega Lucario `1-3`; Alakazam is `3-2`. The collector's `21-13` similarly
  included validation and is not the public record.
- Peak-rule cumulative buckets are Alakazam `3-4`, Archaludon mirror `4-2`,
  Mega Lucario `1-2`, Dragapult `3-1`, and undefeated records into Starmie,
  Hop, and Great Tusk. The same-deck A/B therefore isolates a real rule-policy
  tradeoff: peak rules improve mirror behavior while giving back Alakazam.
- Re-evaluating the existing frozen 50/50 Alakazam residual (`top_n=3`, cap
  `0.12`) on the exact public observations from losses `85556459` and
  `85556933` changed `0/53` MAIN decisions. Those losses are multi-Alakazam
  board/backup-tempo failures, not decisions repaired by the existing
  residual.
- A local-only candidate was built at
  `tmp_compare_submissions/peak_gtmidguard_alakblend5050_cap012_20260712`, with
  archive `peak_gtmidguard_alakblend5050_cap012_20260712.tar.gz`, SHA256
  `D5F2FD3C7FC8A097D296F4E33EA49475BBC0BE1CE1FAE2766697BA8CB00C327B`.
  It hard-gates the residual to Alakazam and preserves the peak deck/rules for
  every other matchup. Structural checks pass: 60 cards, callable final
  `agent`, compile pass, source/package equality, and 14 archive members.
- Decision: do not submit this archive from replay plausibility. Run paired
  Alakazam policy/deck holdouts plus exact non-target controls first. Reject it
  if it has no reproducible target gain, loses any Alakazam opponent bucket,
  or changes any non-Alakazam history. Keep both live submissions until a
  replacement passes these gates.

### 2026-07-12 19:53 JST - Peak Alakazam Residual Rejected

- The first local package used a sibling residual module and failed the paired
  evaluator's file-path import. This was a packaging failure, not method
  evidence. The runtime and frozen weights were fully inlined, producing a
  corrected 13-member archive with SHA256
  `E34B6ADF49424B7EAE2DB174317405310D99DB71009EA1B5D6F9A5E8AD1A4DBA`.
- The corrected evaluation is valid and rejects the candidate:
  - seven Alakazam policies, both seats, 224 games: baseline and candidate both
    `186-38` (`83.04%`), every opponent bucket equal;
  - all 224 target-game summaries identical;
  - six non-Alakazam controls, 192 games: both `155-37`, with `192/192`
    complete trace histories byte-identical;
  - seven current peak-policy Alakazam replays: `0/349` action differences,
    including `0/60` in `85556459` and `0/48` in `85556933`;
  - zero import/action errors, zero max-step hits, and zero duplicate-control
    mismatches across 416 scheduled comparisons.
- Authoritative report:
  `analysis_outputs/peak_gtmidguard_alakblend5050_cap012_eval_20260712/fixed_inline/compact_report.md`.
  The old archive hash `D5F2...327B` is invalid because of the sibling import;
  the corrected `E34B...A4DBA` archive is behaviorally valid but still
  rejected for zero target gain. Neither may be submitted.
- Fresh live fetch after the evaluation: peak-rule `54601378` recovered to
  `22-11`, score `939.94`, while sustained `54600598` is `24-16`, score
  `872.82`. The peak submission remains below silver but is recovering again.
- Decision: spend no submission slot. The existing residual has no action
  support on the current peak policy, so the next candidate must expand the
  candidate action surface or address protected backup tempo rather than
  merely reusing these weights. Keep the private Code unpublished.

### 2026-07-12 - Gold Rule-base Ladder And Crustle Reclassification

- The rank-1-to-20 frozen catalog is now tracked as 15 exact deck hashes and
  16 policy tracks in `docs/gold_meta_rulebase_ladder.md` and
  `docs/gold_meta_rulebase_tracks.csv`. The extra policy track is the current
  Shumpei snapshot on the same Archaludon 60-card hash.
- The previous `great_tusk_crustle` aggregate was materially wrong. Both
  MPGaming Gold seats and the Alberto seat contain Mega Kangaskhan ex and
  Crustle, with zero Great Tusk. The three seats are now treated as two
  Kangaskhan/Crustle deck variants, not as a Great Tusk family.
- MPGaming's canonical deck SHA256 is
  `ed9cdddb866dbaf9add2600e04edcdc30b7679a623ec2fa1cd13b55d4ce545bf`.
  Its plan is anti-ex Crustle wall plus Ascension, Xerosic hand control,
  healing, and Kangaskhan bulk/finishing damage. It has no mill or energy
  denial plan.
- `tools/extract_episode_decks.py` now recognizes card `756` as
  `kangaskhan_crustle` and reserves `great_tusk_crustle` for card `58`.
  A direct classification check and replay `85023093` extraction classify
  MPGaming as Kangaskhan/Crustle and LiamK's separate list as Ogerpon toolbox.
- Track 1 remains the current Shumpei Archaludon policy. A new isolated v2
  agent has the exact 60 cards and current Articuno/Carmine/Judge rules; its
  first-pass implementation required a parent correction from choosing
  second to choosing first, matching 17/17 observed source choices. It is
  under replay-agreement and multi-bucket local evaluation and is not yet a
  submission candidate.

### 2026-07-12 - Shumpei Current v3 Live-Probe Decision

- v2 was rejected decisively: `43-89` against the old simple policy's
  `101-31` over 11 buckets. It had replaced route-aware evolution, Alloy,
  attachment, retreat, Boss, and select-context logic with shallow scores.
- v3 starts from the strong route-aware baseline and changes only the exact
  current 60-card deck plus choose-first and narrow Articuno/Carmine/Judge/
  Xerosic/second-Relicanth handling. Archive:
  `candidate_archaludon_shumpei_current_v3.tar.gz`, SHA256
  `5F0BE1ED0D556CCA5B8ABEF99598F7407DCE7072A161524EFF194769FBB7C633`.
- First 132-game directional suite: v3 `93-39`, baseline `93-39`, errors 0.
  The 12-game Third PTCG bucket was only `2-10`, but a larger targeted rerun
  produced `28-12` with choose-first and `30-10` with choose-second. The
  difference is small, so the source-consistent choose-first policy is kept.
  Mirror was `18-22` in both setup-order arms.
- Live hypothesis: preserving the proven route architecture while using the
  exact Gold Archaludon list should be materially safer than the failed
  rewrite and can reveal whether Shumpei's current card configuration transfers
  to our live opponent distribution. Primary observed buckets are Alakazam and
  Archaludon mirror; broad execution/regression is also monitored.
- Submission is justified because the current two mature live agents are both
  below 1000 (`855.1` and `885.1` at the pre-submit CLI check), three of five
  daily slots have been used, and this candidate has paired local evidence.
- The first v3 upload failed validation because the worker-built archive had
  only `main.py` and `deck.csv`. Successful competition packages also require
  `requirements.txt` and the bundled `cg/` runtime. This is a packaging error,
  not a policy result.
- Corrected archive:
  `candidate_archaludon_shumpei_current_v3_runtime.tar.gz`, SHA256
  `4878856943F14EC37DFFD9AAF49243BEC6F0D1C7BFC4FA4B275EA569754E5DD3`.
  It has the known-successful 13-member root structure. Compile, extracted
  import, exact 60-card read, and source/archive hash equality all pass.
- Corrected live submission is `54606772`, submitted at
  `2026-07-12 20:55:26 JST`. Kaggle validation completed successfully at the
  initial `600.0`; validation episode `85569535` is saved under
  `analysis_outputs/kaggle_live/submission_54606772_shumpei_v3/`. There are no
  public games yet, so medal-stage performance is unclassified.

### 2026-07-12 21:21 JST - Shumpei v3 First Bronze Checkpoint

- Submission `54606772` began `4-1` over its first five public games and
  reached `942.4`, leaderboard rank `227`.
- Fresh leaderboard snapshot:
  `analysis_outputs/leaderboard_current_20260712_2115/`. Current boundaries
  are rank 20 / `1076.4`, rank 100 / `990.5`, and rank 500 / `875.9`.
- This is bronze checkpoint 1 under the ladder definition, not a completed
  bronze promotion: the sample is only five public games and the rank must be
  maintained at later checkpoints.
- Wins: two Alakazam, one Mega Lucario, and one Ogerpon toolbox. The only loss
  is episode `85571108` against Gaurav Goswami's exact
  Mega Kangaskhan ex/Crustle list. Score recovered from `857.9` after that loss
  to `942.4` on the next win.
- Decision: keep the recovering submission. Do not use another slot. Analyze
  the single Crustle loss as low-confidence evidence and require repeated live
  or local support before changing the policy.
- Episode `85571108` action diagnosis found that the Crustle guard worked as
  intended: early detection from Dwebble, no Archaludon ex evolution,
  Relicanth suppression, full-HP Duraludon waiting into active Spiky Energy,
  Raging Hammer preference, KO-aware Boss, and second-Duraludon attachment all
  fired. The loss ended on turn 26 with 12 deck cards remaining, not deck-out.
- The opponent established a separate high-HP Crustle and won the damage
  exchange. No repeatable candidate blunder was identified. Treat this as
  opponent strength/draw-sequence variance until another live loss supports a
  specific rule. Do not implement the speculative early-disruption branch
  from one game.

### 2026-07-12 21:25 JST - Bronze Checkpoint Not Sustained

- Two additional public losses moved submission `54606772` from `4-1 / 942.4`
  to `4-3 / 850.0`. The first bronze checkpoint is therefore not sustained.
- New losses are distinct buckets: episode `85572067` versus AnSuSu's
  Archaludon/Cinderace list and episode `85572552` versus Oshbocker's
  Cynthia/Garchomp list. This is not a repeat of the earlier Crustle loss.
- Current wins remain Alakazam `2-0`, Mega Lucario `1-0`, and Ogerpon toolbox
  `1-0`. Losses are Kangaskhan/Crustle `0-1`, Archaludon `0-1`, and Cynthia
  `0-1`.
- Seven public games remain too few for replacement, and all daily slots are
  already consumed. Diagnose the mirror and Cynthia games independently;
  only build a candidate if a bounded rule explains one bucket without
  touching the three winning buckets.
- Mirror diagnosis found one concrete turn-11 search error in episode
  `85572067`: Ultra Ball chose backup Duraludon over Archaludon ex although
  the active Duraludon could use two discarded Metal for an Alloy recovery.
  Cynthia episode `85572552` contained no clear policy error; it was a forced
  Relicanth opening into a faster multi-Garchomp chain.
- A local-only v4 mirror search candidate changes exactly that turn-11 choice
  from Duraludon to Archaludon ex. Across all seven public replays it changes
  `1/392` decisions, with zero changes in the four wins, Crustle loss, and
  Cynthia loss. Archive:
  `candidate_archaludon_shumpei_current_v4_mirroralloysearch_runtime.tar.gz`,
  SHA256 `C85E4E4FA6976CDB4976EDCC26BDF3D5AC8F98DD6962377A9EF5680FC632893A`.
- Directional mirror panels do not prove aggregate gain. Against the Shumpei
  local policy, v3/v3 duplicate/v4 were `46/80`, `40/80`, `41/80`; against
  the exact AnSuSu deck, they were `29/80`, `22/80`, `29/80`. The duplicate
  spread is as large as the candidate delta because native shuffles are not
  seeded. Keep v4 as a plausible queued rule, but do not submit or promote it
  until another live mirror loss or stronger paired evidence supports it.

### 2026-07-12 21:39 JST - v3 Early Failure Signal, Mirror Repeats

- Submission `54606772` fell to `739.8` after 11 public games, record `5-6`.
  The new four-game window was `1-3`. This is now an early-failure signal,
  though all daily slots are exhausted and no replacement can be submitted.
- Corrected reclassification outputs are under
  `monitor_54606772_20260712_2139_decks_fixed` and
  `monitor_54606772_20260712_2139_summary_fixed`. The first collector summary
  with `missing` archetypes is invalid.
- Current buckets: Archaludon `0-2`, Kangaskhan/Crustle `0-1`, Cynthia `0-1`,
  Hop/Trevenant `0-1`, Alakazam `2-1`, Mega Lucario `1-0`, Ogerpon `1-0`, and
  Starmie/Froslass `1-0`.
- The second mirror loss `85573532` is distinct from v4's search state but
  repeats the broader attacker-chain failure: the opponent's Cinderace engine
  established two ex attackers while ours held an evolution-ready benched
  Duraludon because Metal discard was zero. A v5 mirror-only reserve-ex rule
  is being tested separately. Do not combine the unrelated Hop Boss idea into
  the same candidate.

### 2026-07-12 21:50 JST - v5 Mirror-chain Candidate And Seeded Gate

- Submission `54606772` now has 16 public games, record `7-9`, and latest
  score `748.0`. The current buckets are Alakazam `2-2`, Archaludon `1-2`,
  Mega Lucario `1-1`, Kangaskhan/Crustle `0-1`, Cynthia `0-1`,
  Hop/Trevenant `0-1`, Marnie/Grimmsnarl `0-1`, Starmie/Froslass `2-0`, and
  Ogerpon toolbox `1-0`. This remains a clear early-failure signal rather than
  a recovering bronze checkpoint.
- v5 extends v4 with one narrow mirror-chain rule: when our active Archaludon
  ex is already online and in the immediate pre-KO window, the opponent has a
  visible Cinderace plus a charged Archaludon ex, and an evolution-ready bench
  Duraludon is available before attachment, bank the reserve Archaludon ex
  even with zero Metal in discard.
- Replay attribution changes exactly one decision in loss `85573532` (turn 7,
  reserve bench evolution), preserves v4's turn-11 search correction in
  `85572067`, and changes zero decisions in the other ten then-current public
  replays.
- Runtime archive:
  `candidate_archaludon_shumpei_current_v5_mirrorchain_runtime.tar.gz`, SHA256
  `DCB6350A703D42BDD9C87C9208314D3D9349E963834BFD64E71FC19D80C1A2E7`.
  It has 60 cards, the known-successful 13-member layout, and passed compile,
  import, replay-comparison, and local smoke checks.
- Valid seeded mirror gate used
  `analysis_outputs/rl_policy_value/seeded_engine`: v4 and v5 both scored
  `78/200`, with zero baseline-duplicate mismatches. By opponent, both were
  `35/100` versus the public Archaludon policy and `43/100` versus the Shumpei
  policy. This proves reproducibility and no aggregate regression, but not an
  aggregate win-rate gain.
- Valid seeded non-target preservation gate was also exact: v4 and v5 both
  scored `250/400`, with zero duplicate mismatches. Per bucket both matched at
  Alakazam `69/100`, Mega Lucario `86/100`, Ogerpon `18/100`, and Starmie
  `77/100`.
- Decision: retain v5 as the best prepared next-reset probe because it fixes a
  repeated live mirror failure with zero measured adjacent regression. Do not
  claim local aggregate improvement. Before the next slot, incorporate another
  rule only if the new Alakazam or Marnie losses yield a similarly bounded,
  replay-supported change.

### 2026-07-12 22:10 JST - v6 Marnie Bench Guard Selected

- The latest five live games moved submission `54606772` to `7-9` and `748.0`.
  New losses were Alakazam `2-2`, Mega Lucario `1-1`, and
  Marnie/Grimmsnarl `0-1`; the complete 16-game summary is under
  `monitor_54606772_20260712_2150_summary`.
- The two Alakazam losses did not support one safe shared rule. Episode
  `85574337` exposed a plausible pre-KO backup-evolution error, but episode
  `85575486` was primarily opposing tempo and board strength. The broader
  Alakazam rule is deferred because it can consume the only Archaludon and
  regress the two existing live wins.
- Marnie loss `85575965` exposed a narrower error. At turn 4 the two-line core
  was already established and a core attack was available, but v5 benched the
  optional 110-HP Articuno. It provided no later utility and became a spread-
  damage prize liability before the opponent's final prize turn.
- v6 adds only a visible-information bench guard: with opponent card `646`,
  `647`, or `648` visible, two Duraludon/Archaludon lines established, and a
  core attack route available, skip optional Articuno. Replay attribution on
  `85575965` changes exactly `PLAY 414` to `ATTACK 253`; the other 15 comparable
  public replays have `0/801` decision changes.
- Runtime archive:
  `candidate_archaludon_shumpei_current_v6_marniebenchguard_runtime.tar.gz`,
  SHA256 `801F8416D52AA0217EF93B03383E8AFDBA27E1FEE9B5960BBC9F52D0C569E69B`.
  It contains the exact 60-card deck and 13 required runtime members; compile,
  import, smoke, and package checks pass.
- Valid seeded Marnie panel over four policy styles improved from `319/400` to
  `320/400`, with the single gain in the Gonsaku bucket and zero duplicate
  mismatches. Valid non-target preservation was exact at `111/160` for both
  v5 and v6 over Archaludon, Alakazam, Mega Lucario, and Starmie.
- Decision: v6 supersedes v5 as the first next-reset submission probe. The
  evidence is deliberately characterized as a small, non-regressing targeted
  improvement, not a broad solution to the track's `748.0` live weakness.
  Today's five slots are exhausted, so retain the archive until quota reset.

### 2026-07-12 23:35 JST - Win-plan Pivot And MPGaming Local Baseline

- Submission `54606772` reached 20 public games at `9-11`, latest score
  `733.0`. The updated buckets are Alakazam `2-4`, Archaludon `1-2`, Mega
  Lucario `1-1`, Kangaskhan/Crustle `0-1`, Cynthia `0-1`, Hop/Trevenant
  `0-1`, Marnie `0-1`, Starmie `3-0`, Mega Abomasnow/Kyogre `1-0`, and
  Ogerpon `1-0`. This is a mature early-failure signal; no daily slot remains
  before the next reset.
- A Sol Ultra audit corrected the prior Alakazam diagnosis. Across all six
  Alakazam replays, the submitted v3 and prepared v6 matched all `280/280`
  recorded decisions. Episode `85575486` did evolve both the active and bench
  Duraludon at steps 95 and 102. The proposed Articuno re-promotion guard then
  regressed seeded Alakazam from `148/200` to `144/200`, so no Alakazam patch
  is retained.
- The MPGaming Track uses the exact Gold 60-card list: four Mega Kangaskhan
  ex, four Dwebble, four Crustle, one Shaymin, 13 Energy, and the documented
  wall/control trainer package. Nineteen exact-deck Gold replays were measured
  separately as ten wins and nine losses.
- Positive Gold measurements disproved the assumed one-wall/one-Kang board.
  Seven of ten wins reached at least three Dwebble/Crustle-line bodies. First
  attacks were Combo `5/10`, Ascension `3/10`, and Scissors `2/10`; all five
  first-Scissors observations had zero Kangaskhan Energy. At first prize, nine
  winning games averaged `3.89` bodies, `2.11` line bodies, and only `1.78`
  Kangaskhan Energy. No loss took a prize.
- Six proactive implementations were tested rather than stopping at the first
  failure. Seeded six-bucket results against the same exact-deck v0 baseline:
  v0 `374/600`, v1 stateless route `354/600`, v2 five-phase state machine
  `307/600`, v3 Gold-positive broad board `342/600`, v5 Kang-finish overlay
  `369/600`, and v6 guarded finish `370/600`. All runs were valid with zero
  duplicate mismatches and no action/max-step errors.
- The broad v1-v3 policies overrode already-correct setup, bench, and supporter
  sequencing. Action audit showed v0 already matched all `46/46` Gold attack
  decisions. v3 improved win attachment agreement but reduced total winning
  action agreement from `286/303` exact/coarse to `272/292` and lost 32 seeded
  wins.
- The narrow Kang-before-Hilda overlays also failed causality. Playing Hilda
  first does not consume the turn's Energy attachment, so matching the raw
  order did not improve the resulting line. v5 and v6 remained five and four
  wins below v0, mainly in Alakazam and Marnie.
- Decision: promote exact-deck v0 as the current MPGaming local baseline and
  reject v1-v6. This is not a claim that v0 is silver-ready; it is the strongest
  measured same-deck policy and is suitable for a Kaggle Bronze probe. Runtime
  archive `candidate_kangaskhan_crustle_mpgaming_v0_exact_simple_runtime.tar.gz`
  has 13 members, imports with 60 cards, and SHA256
  `62ECD53F3486E47F9BF9BFE0B9DB4362BFD16E6AAED6794D3635A323CEB69B50`.
- Next-reset priority is the MPGaming v0 live probe rather than another small
  Archaludon patch: the live Archaludon is stalled near 733, the exact Gold
  Kangaskhan deck provides a new high-power family, and the local policy has a
  reproducible `374/600` broad-panel result. Archaludon v6 remains the second
  prepared slot if the new probe fails early.

### 2026-07-13 00:35 JST - Proactive Win-plan Gate And Final Archaludon Read

- A fresh complete fetch moved submission `54606772` to `687.1` after 37
  public games, record `15-22`. The main buckets were Alakazam `2-8`, Mega
  Lucario `5-5`, Archaludon `1-2`, Kangaskhan/Crustle `1-2`, and Starmie
  `3-1`. This is a mature weak result, not a recovering submission.
- The 2026-07-13 00:36 JST leaderboard snapshot put rank 500 at `874.9`, rank
  100 at `989.7`, and rank 20 at `1081.2`. These remain the working Bronze,
  Silver, and Gold gates for the rule-base ladder.
- The development method is now explicitly proactive. Gold wins are analyzed
  as setup-to-board-to-attack-to-prize transitions. Loss-specific rules are
  retained only as narrow safety guards after the deck's positive route has
  been established and measured.
- `tools/summarize_local_traces.py` now extracts first attack/evolution/prize
  turns, the first-prize board, and maximum board size for both players. This
  allows local candidates to be compared on route completion and attack tempo,
  not only terminal wins. A focused regression test covers cumulative logs and
  milestone extraction.
- Alakazam variant A v1 improved the independent variant-B panel by `+5/100`
  but lost `-7/100` into Kangaskhan/Crustle because it delayed nonlethal
  Powerful Hand for generic development. v2 restored v0 opening bench behavior
  and suppressed development-before-attack only when a visible Crustle wall
  was present, except for one fully public damaged-wall state.
- The valid 700-game v2 gate scored baseline `285/700` and candidate `283/700`,
  with zero duplicate mismatch or action/max-step errors. It repaired Kang from
  v1's `20/100` to `29/100` and won all eleven targeted flip seeds, but remained
  `-4/100` into Archaludon and `-1/100` in the variant-A mirror. v2 therefore
  fails promotion, while the remaining Arch/mirror divergence is being
  diagnosed before deciding whether a v3 guard is defensible.
- Alakazam v3 then gated Shaymin on visible Alakazam access. It recovered one
  targeted Arch loss while retaining the two critical Kang gains, but the full
  valid panel fell to `282/700`: Arch `31`, mirror `47`, Marnie `28`, and total
  `-3` versus baseline. v3 is rejected; v2 remains the best engineflow
  experiment but is also below the local promotion gate.
- MPGaming v7 isolated one proactive transition: after at least three visible
  Dwebble/Crustle-line bodies are established, prefer Xerosic before the legal
  Energy-to-Ascension turn, while preserving every v0 attack and target
  ranking. This exact intervention was not isolated by rejected broad v1-v3 or
  Kang-finish v5-v6 policies.
- The valid 600-game v7 gate scored `375/600` versus v0 `374/600`, with zero
  duplicate mismatch or action/max-step errors. It gained mirror `+2` and Arch
  `+1`, held Cynthia/Marnie/Okidogi, but lost Alakazam `-2`. Nine paired
  outcomes changed. Because the predeclared safety gate required no Alakazam
  or Marnie loss, v7 is not promoted yet; its visible Xerosic-state features
  are being inspected for a causal narrowing rather than accepting the small
  aggregate gain.
- MPGaming v8 narrowed the same proactive Xerosic transition to turn 2 after
  the opponent had visibly committed at least one Energy. The valid panel
  improved to `379/600` versus v0 `374/600`: mirror `+3`, Arch `+1`, Alakazam
  `+1`, and zero change in Cynthia, Marnie, and Okidogi. All five outcome flips
  were gains, with zero losses or execution anomalies. Because the narrowing
  was derived from the original panel, an untouched external-seed 600-game
  holdout is required before v8 supersedes v0 for the next live probe.
- The untouched `2026093xx` holdout passed: v8 `380/600` versus v0 `378/600`,
  with mirror `+1`, Arch `+1`, and exact equality in Alakazam, Cynthia, Marnie,
  and Okidogi. Both outcome flips were gains, and duplicate mismatch,
  action-error, and max-step counts were zero. Across development plus holdout,
  v8 is `+7/1200` with no bucket regression.
- A second blind population panel covered eleven distinct Gold deck/policy
  proxies, including three Alakazam and three Marnie styles, Cynthia, Okidogi,
  Alberto Kangaskhan/Crustle, Shumpei Archaludon, and the MP mirror. v8 scored
  `152/220` versus v0 `151/220`; every policy was equal except MP mirror `+1`.
  The Alakazam aggregate remained `45/60` and Marnie `53/60`. Total evidence is
  therefore v8 `+8/1420` with no measured policy or family regression.
- v8 therefore superseded v0 as the first next-reset live probe. Its proactive
  Xerosic/Ascension evidence remains `+8/1420` with no policy regression.
- A proposed "charge bench Kangaskhan before Scissors" extension was rejected
  from authoritative Gold evidence. Among 17 qualifying winning states, Gold
  attached before Scissors seven times, but only one target was Kangaskhan and
  that state had an immediate KO. The nonlethal targets were reserve Crustle or
  Dwebble, so a Kang finish override would extrapolate against the observed
  route.
- The corrected proactive hypothesis is reserve-line continuity. Four
  nonlethal Gold states across three episodes attached to an established bench
  Dwebble/Crustle before Scissors while the active Crustle remained online.
  v9 is under evaluation with an immediate-KO exclusion and no Kangaskhan
  target: prefer a one-Energy reserve Crustle, then zero-Energy Dwebble, then
  zero-Energy Crustle, before a nonlethal Scissors.
- v9 reproduced the four intended Gold decisions and, after fixing a latent
  `minCount` selection bug, completed a valid 600-game panel at `381/600`
  versus v8 `379/600`. It nevertheless caused five deterministic losses among
  twelve flips, including Archaludon and Cynthia regressions. No simple public
  predicate both preserved the Gold coverage and removed all losses, so the
  reserve-line strategy is rejected and v8 remains selected.
- The v9 failure exposed a separate legality defect inherited from v0-v8: a
  required multi-select could return fewer than `minCount` when required cards
  had negative scores. A legality-only v8 successor now fills the required
  count while excluding only optional negative choices. Its strategy is
  otherwise identical to v8 and is undergoing a 1200-game equality/safety
  panel before replacing the current archive.
- The legality-only successor passed. It matched v8 exactly over the combined
  development/holdout panel (`759/1200` each, zero outcome flips) and the
  eleven-policy Gold population (`152/220` each, zero decision-count
  differences). Both panels had zero duplicate mismatch, action error, or
  max-step events. This is a safety promotion, not a claimed win-rate gain.
- Final next-reset archive:
  `candidate_kangaskhan_crustle_mpgaming_v8_legalfix_runtime.tar.gz`, SHA256
  `ED6D772CCF4FAB2B929190013D25144029FAE5762290E9B4366B8D2CF4D0CDA4`.
  It contains the exact Gold 60 cards and 13 expected runtime members.
- The next quota reset remains expected around 09:00 JST. Unless later local
  evidence supersedes it, MPGaming v8 legality-fix is the first live Bronze probe because
  today's Archaludon is mature below 700 and all recent submissions remain
  below 1000. Submission hypothesis: an exact Gold deck plus the validated
  multi-line/Xerosic/Ascension opening route should outperform the failed
  Archaludon track, especially into Archaludon, Alakazam, and the mirror.

### 2026-07-13 02:20 JST - Exact Track Audit And Win-plan Contract

- `docs/gold_meta_rulebase_local_agents.csv` now maps all 16 distinct Gold
  policy tracks to a source team/episode/seat, canonical source deck SHA, and
  one local agent directory. Every mapped `deck.csv` has exactly 60 cards and
  matches the source multiset SHA.
- `tools/verify_gold_meta_agent_manifest.py` makes that audit reproducible.
  The current check reports `OK` for all 16 tracks.
- Several older local directory names retain obsolete classifications or
  episode labels: btk is stored under an `ogerpon` name, Alberto under a
  `great_tusk` name, and THIRD PTCG A under an older episode name. The manifest
  is authoritative; these are naming discrepancies, not deck mismatches.
- `docs/gold_meta_win_plan_specs.md` separates exact deck copy, rule-policy
  maturity, and measured win-plan maturity. A copied deck with a `simple_only`
  policy is not considered developed.
- Rule development now starts from setup, development, first-attack, midgame,
  prize, recovery, and endgame contracts. Loss-derived changes are accepted
  only as safety guards after the positive route is measured.
- A read-only re-audit of MPGaming Gold wins confirmed that v8 implements only
  the first validated proactive transition, not a complete win plan. The next
  high-value gap is post-first-prize multi-line continuity before committing
  to Kangaskhan. The rejected v9 pre-Scissors attachment rule must not be
  revived; any successor must preserve all 46 measured Gold attack decisions
  and pass 600 development, 600 untouched holdout, and 220 Gold-population
  games without family regression.

### 2026-07-13 02:35 JST - Win-plan Trace Instrumentation

- `tools/summarize_local_traces.py` now accepts `--line-card-id`,
  `--focus-attach-card-id`, `--recovery-card-id`, and `--game-summary`.
  It records first-prize line count, minimum post-prize line count, first
  attachment to the focus attacker, attack gaps, and recovery-to-attack.
- The implementation also fixed a pre-existing parser defect. Local engine
  traces normally contain per-step delta logs, while the old parser treated
  log length as globally cumulative and could skip attacks. The parser now
  detects cumulative traces and otherwise consumes every delta log. A terminal
  game summary supplies result/final state when the trace ends before terminal
  bookkeeping. Eight focused tests pass.
- A 20-game two-seat v8 legality-fix mirror smoke produced 11 wins and 9 losses.
  Wins: first attack mean turn `3.91`, first prize `11/11`, mean first-prize
  line count `2.91`, first Kangaskhan attach in `2/11`. Losses: first attack
  mean turn `8.88`, first prize `2/9`, mean first-prize line count `1.50`, first
  Kangaskhan attach in `8/9`.
- First attacks in wins were Ascension `8`, Scissors `2`, Smash Kick `1`;
  losses were Combo `6`, Ascension `2`, no attack `1`. This is strong route
  evidence but not yet causal evidence for an attachment guard. A bounded
  option-level audit must determine whether line attachment alternatives were
  legal before any policy change.
- Smoke outputs:
  `analysis_outputs/mpgaming_v8_winplan_smoke/p0_winplan.csv` and
  `analysis_outputs/mpgaming_v8_winplan_smoke/p1_winplan.csv`.

### 2026-07-13 03:05 JST - Opening Line Attachment Counterfactual

- `tools/run_local_battle.py --trace-options` now records compact identities
  for every legal option, including attachment target coordinates. Nine focused
  parser/trace tests pass.
- Corrected option-level audit: ten first Kangaskhan attachments contained
  seven states with a legal Dwebble/Crustle alternative. Their outcomes were
  two wins and five losses. The turn-one Dwebble-available subset was one win
  and four losses. No state had a legal immediate attack in the same selection.
- v10 isolated only this proactive transition: at 6-6 prizes, turn <=2, Active
  Kangaskhan, no legal attack, and a Bench line target, score Dwebble attach
  `7200`, Crustle `7100`, Kangaskhan `7000`. Poffin `8500`, Hilda `8000`, and
  evolve `9000` remain ahead, so setup action order is unchanged.
- The first evaluation stopped on seed `202608338`, but reproduction proved
  the illegal action came from opponent v0: it returned seven indices for
  `minCount=8`. `meta_agents/kangaskhan_crustle_mpgaming_v0_legalfix` preserves
  v0 strategy and fixes only required selection count. The failed seed then
  completed with zero errors.
- Valid rerun against legality-fixed mirror and unchanged external conditions:
  development `379/600 -> 372/600`, holdout `380/600 -> 379/600`, Gold
  population `152/220 -> 155/220`; aggregate `911/1420 -> 906/1420` with one
  unchanged non-win result. There were 23 gains and 28 regressions, no action
  errors and no max-step events.
- Family deltas: Alakazam `-6`, Archaludon `0`, Cynthia `+2`, Alberto `+1`,
  Marnie `+4`, MP mirror `+1`, Okidogi `-7`. v10 fails promotion and must not
  replace v8. Its mixed signal is being narrowed by first-divergence public
  state analysis rather than abandoned after the first failure.
- Evidence:
  `analysis_outputs/mpgaming_v8_vs_v10_evaluation_v0legal_20260713/evaluation_summary.json`,
  `paired_flips.jsonl`, and `smoke_decision_changes.jsonl`.

### 2026-07-13 03:35 JST - Visible Guard And Untouched Rejection

- v11 kept v10's proactive Dwebble attachment but reverted to active
  Kangaskhan attachment when public opponent markers showed Alakazam (`305` or
  `741`) or the safely separable Okidogi subset (`675` visible or Active `116`).
- On the reused 1420-game analysis set, v11 recovered all six Alakazam and all
  seven marked Okidogi regressions, preserved all 23 v10 gains, and scored
  `919/1420` versus v8 `911/1420`. Family deltas were Alakazam/Archaludon/
  Okidogi `0`, Cynthia `+2`, Alberto `+1`, Marnie `+4`, mirror `+1`.
- This was not a blind result because the predicates came from those outcomes.
  Two untouched panels used preflight-clean seed ranges and frozen manifests.
- Fresh broad 600: v8 `379`, v11 `374`, with Archaludon `-3`, Marnie `-2`,
  mirror `-1`, Okidogi `-1`, Alakazam `+1`, Cynthia `+1`.
- Fresh exact 16-track Gold panel 320: v8 `226`, v11 `231`; no net-negative
  family/style, with MPGaming `+2`, Sota `+1`, tw_shin `+1`, Alberto `+1`.
- Combined blind 920 was exactly tied `605-605`, with 15 gains and 15
  regressions. v11 fails promotion because the broad panel regressed across
  several styles. v8 legality-fix remains the submission candidate.
- Evidence:
  `analysis_outputs/mpgaming_v8_vs_v11_blind_validation_202614_202615/evaluation_summary.json`
  and `paired_flips.jsonl`.

### 2026-07-13 04:25 JST - Backup-Kang Grow-Line Narrowing

- The broad visible-state gate did not remain safe across both ledgers. A
  simpler positive condition was isolated from two independent gain states:
  Active Kangaskhan, backup Bench Kangaskhan, Grow Grass Energy `18`, and a
  Bench Dwebble at 6-6 prizes before a legal attack.
- v12 changed 38/3260 paired games. Thirty-five were outcome-neutral, gains
  were holdout Marnie seed `202609339` and blind mirror seed `202614060`, and
  the only regression was fresh Sota Marnie seed `202616020`.
- Existing 2340 conditions: `+2`, zero regression. Untouched 920: `-1`, from
  the single Sota game; all 16 exact Gold tracks were unchanged. Combined
  3260 was `+1`, but v12 fails promotion because its fresh panel was negative.
- Both gains had own Bench `[756,344,344]`. The regression had
  `[756,344,344,344,344]`. v13 therefore requires exactly two Bench Dwebble;
  with four lines already established, it preserves active Kangaskhan pressure.
- v13 is undergoing full replay plus another untouched seed gate. v8 remains
  the live submission candidate until that completes.
- Evidence:
  `analysis_outputs/mpgaming_v8_vs_v12_combined_evaluation_20260713/combined_summary.json`
  and `decision_changes.jsonl`.

### 2026-07-13 04:58 JST - V13 Proactive Route Promotion

- v13 adds one board-saturation condition to v12: the Grow Grass-to-Dwebble
  route is legal only with exactly two Bench Dwebble. This preserves the two
  gain boards and disables the four-Dwebble Sota regression, where further
  line investment had no strategic need.
- Full paired evidence covers 4180 games per policy. v8 scored
  `2711-1458-11`; v13 scored `2715-1454-11`. There were four gains, zero
  regressions, and no negative family/style.
- Untouched `202620xxx` broad 600 added two wins; untouched exact 16-track
  `202621xxx` 320 was identical. Stage-2 preflight found no prior outcomes.
- Direct attribution: 39/4180 games changed, 35 neutral and four gains. Every
  change attached Grow Grass Energy `18` to Bench Dwebble instead of Active
  Kangaskhan at 6-6 on turn <=2 with backup Kangaskhan and exactly two Bench
  Dwebble. Zero changes were unattributed.
- Duplicate controls were exact `4180/4180`; action errors, max-step hits,
  failed starts, and command failures were zero.
- Final archive:
  `candidate_kangaskhan_crustle_mpgaming_v13_backupkang_two_growline_runtime.tar.gz`,
  SHA256 `D7435351E79EEA561DED6B924E092E2EA6072DFAAAD501C0EEE79EBDB54F130E`.
  It has 13 members, 60 cards, extracted import success, and a five-game
  packaged smoke with zero errors.
- v13 supersedes v8 as the next-reset Kaggle Bronze probe. Submission
  hypothesis: the exact Gold deck plus validated Xerosic-to-Ascension opening
  and saturated two-line Grow Grass investment will improve live route
  completion without weakening adjacent Gold styles.
- Evidence:
  `analysis_outputs/mpgaming_v8_vs_v13_combined_evaluation_20260713/combined_summary.json`
  and `decision_changes.jsonl`.

## 2026-07-13 - Live win-plan telemetry

- Added `tools/summarize_kaggle_winplan.py` so live submissions are evaluated
  by proactive route completion rather than score and loss buckets alone.
- It resolves the target seat from the submission id and records first evolve,
  first attack, first prize, line width at both milestones, focused attachment,
  board width, and attack continuity for each public replay.
- The parser handles cumulative, delta, and repeated inactive observation logs.
- Smoke on 38 Shumpei replays completed with no skipped seat. Six related tests
  pass. This is instrumentation evidence only; the Archaludon sample is not an
  MPGaming strategy estimate.
- For the v13 live probe, use line ids `344/345`, focus energy `18`, focus target
  `344`, and line threshold 3. Candidate iteration must explain both local paired
  outcomes and live route-completion movement.

## 2026-07-13 - MPGaming dual-route Gold evidence

- Gold replay `85023093` is the Crustle prize route: Ascension followed by six
  Superb Scissors mentions, ending with MPGaming at one prize.
- Gold replay `85023197` is a different stall/finisher route against Alakazam:
  repeated Xerosic, opponent deck reduced to zero, and energy accumulated on a
  Bench Kangaskhan before Rapid-Fire Combo on turns 16 and 18.
- Replay-action audit corrected the frame mapping. The action for an observation
  is stored on the following frame. At observation step 66, Gold first chooses
  Xerosic (`[7]` on the next frame), reducing opponent hand from 13 to 3. At
  observation step 68, Gold then chooses Spiky Energy `14` to the zero-energy
  Bench Kangaskhan (`[2]` on the next frame). v13 chooses Poffin in both states.
- The correct route is therefore Xerosic before recovery attach, not an immediate
  attach override. `tools/compare_replay_agent_actions.py` now reports each
  policy's recorded-action mismatches explicitly to prevent same-frame mistakes.

## 2026-07-13 - MPGaming recovery-rule ablation v14-v17

- v14 was based on the incorrect same-frame attach label and scored `-2/600` on fresh
  `202622xxx`. Direct trace attribution found two gains and four regressions.
- v15 used opponent field width or low deck as a public gate. It removed the
  four known regressions but was `-1/600` on blind `202623xxx`.
- v16 required an own Dwebble on the low-deck branch. It removed the v15 blind
  regression but was `-2/600` on blind `202624xxx`.
- v17 required own Dwebble for both branches and used either opponent deck
  `<=18` or opponent field `<=4` with hand `>=5`. It retained the two known
  gains and removed all seven known regressions.
- On completely unused `202625xxx`, v13 and v17 were both `353-247` over 600
  games with zero flips. v17 is safe but has no blind improvement evidence.
- Decision: reject v14-v17 for submission and keep v13. This ablation shows why
  one Gold action cannot be promoted solely by replay agreement: its value
  depends on future pressure/resource state not resolved by the current public
  features and local opponent policies.
- Evidence directories:
  `analysis_outputs/mpgaming_v13_vs_v14_fresh202622_evaluation`,
  `analysis_outputs/mpgaming_v13_vs_v15_blind202623_evaluation`,
  `analysis_outputs/mpgaming_v13_vs_v16_blind202624_evaluation`, and
  `analysis_outputs/mpgaming_v13_vs_v17_blind202625_evaluation`.

## 2026-07-13 - Corrected Xerosic-to-Kang deckout route

- Updated following-frame comparison shows v13 disagrees with Gold at both
  deckout-route observations: step 66 should play Xerosic; step 68 should attach
  Spiky Energy to the zero-energy Bench Kangaskhan.
- v18 implements the two-phase public state machine from v13: at prizes 6-5,
  attackless zero-energy Active Crustle, own Dwebble present, and opponent deck
  `<=18`, play Xerosic while opponent hand is at least 4, then prepare Bench
  Kangaskhan once opponent hand is at most 3.
- No opponent IDs or hidden zones are used. v14-v17 remain rejected and must not
  be submitted even though their local ablation evidence remains useful.
- v18 reduced recorded-action mismatches on `85023197` from 31 to 29, exactly at
  steps 66 and 68, and changed none of 67 decisions on `85023093`.
- Fresh `202626xxx` evaluation was exactly neutral: v13 and v18 both `354-246`
  over 600 games, all six opponent deltas zero, zero flips/errors/max-step hits.
- Decision: submit v13 first because it has measured paired gains. Retain v18 as
  the next safe hypothesis only if live MPGaming games expose the low-deck,
  large-hand Xerosic-to-Kang state.

## 2026-07-13 - MPGaming proactive heal route promotion

- Method changed from loss-first patching to Gold win-plan completion. Gold
  episodes `85023093` and `85023197` show healing as part of continued attack
  pressure, not merely emergency defense.
- v19 prioritized Jumbo Ice Cream before a legal attack when the Active was
  missing at least 80 HP. It gained `+15/600` on two independent broad panels
  and `+9/320` on the exact 16-track panel, but introduced three Archaludon
  tempo regressions.
- v20's broad prize/lethal guard fixed those regressions but erased nine of the
  twelve gains (`+3/320`). This is evidence that a generic "take the KO" rule
  is too coarse for the Kangaskhan tank route.
- v23 uses a public role-aware conversion: only a close prize race and a legal
  attack leaving the opponent at at most 10 HP can override healing; low-deck
  stall remains exempt; fragile attackers convert earlier; a 300-HP tank heals
  until missing HP drops below 160.
- Development exact-Gold panel: `209 -> 221/320`, twelve gains and zero
  regressions. Blind broad panel: `359 -> 375/600`. Blind exact-Gold panel:
  `221 -> 231/320`. All controls were deterministic and all error counts zero.
- The blind broad Marnie proxy was `-3/100`. A bench-width>=3 tempo patch v24
  improved only one of five targeted regressions and was rejected rather than
  promoted from a small correlated sample.
- Gold replay decisions for v19 and v23 are identical in both source wins, so
  the safety refinement preserves the measured proactive route.
- Final archive:
  `candidate_kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard_runtime.tar.gz`.
  SHA256 `6DC31311CE6E189BB2685367CB0FCF2EC843DC17EBCCBF2E1BBBF1DA80A9FC12`;
  13 runtime members, exact 60 cards, extracted import and five-game smoke pass.
- Evidence:
  `analysis_outputs/mpgaming_v13_vs_v23_goldtracks202629_evaluation`,
  `analysis_outputs/mpgaming_v13_vs_v23_fresh202630_evaluation`, and
  `analysis_outputs/mpgaming_v13_vs_v23_goldtracks202631_evaluation`.

### Pre-submit decision at 2026-07-13 07:09 JST

- Fresh Kaggle CLI shows current submission `54606772` COMPLETE at `698.5`.
  It is mature, below Bronze, and not recovering.
- Replacement hypothesis: the exact Gold MPGaming deck plus the measured
  Xerosic/Grow-line opening and proactive heal-to-attack continuity should
  complete its intended route more often than the weak Archaludon submission.
- Target field: the 16 exact Gold policy tracks, with particular local gains
  into Alakazam and mirror proxies. Known risk is Sota Marnie (`-3/100` on one
  blind broad panel); v24 did not provide a reliable fix.
- Rollback: retain v13 archive if live healing is clearly harmful, and retain
  the current Archaludon packages only as historical references.
- Do not submit before the expected daily reset around 09:00 JST. After reset,
  refresh quota/state, submit v23, check validation immediately, and collect
  route telemetry plus public replays.

### Blind flip win-plan attribution

- Replayed all 30 changed outcomes from the blind `202630xxx` panel at the
  exact seed and seat: 23 v23 gains and seven regressions.
- Every first divergence was Jumbo Ice Cream before an available action/attack.
  First evolution and first attack timing were unchanged in every flip.
- Gain games averaged 14.2 attacks under v23 versus 8.0 under v13. They ended
  in 15 board clears and eight opponent deckouts. Board and Crustle-line width
  were unchanged, so the measured mechanism is post-readiness attacker sustain.
- Alakazam supplied 11/11 gains; mirror supplied eight gains and one regression.
  Marnie seat 1 supplied five regressions and two gains, with v23 attack count
  falling to 8.9 versus v13 9.6.
- Live success signature: Jumbo-to-Kang before a ready attack, followed by more
  attacks and a board-clear/deckout conversion. Warning signature: the same
  early Jumbo in Marnie games without increased attacks, ending in board loss.
- Evidence: `analysis_outputs/mpgaming_v13_vs_v23_fresh202630_winplan_attribution`.

### Independent Marnie population gate

- Tested four distinct exact-Gold Marnie policy styles plus the Sota proxy on
  unused `202635xxx`, 500 paired games total.
- v13 scored `417-83`; v23 scored `423-77` (`+6`, +1.2 pp).
- Per style deltas were Gold06 `0`, Gold07 `+1`, Gold08 `+2`, Gold09 `+3`,
  and Sota `0`. Seat deltas were `+1/+5`.
- Controls were exact; action errors and max-step hits were zero.
- The earlier Sota `-3/100` does not reproduce and does not justify a narrow
  pre-submit Marnie patch. Keep v23 unchanged and use live telemetry to decide
  whether a real field-specific warning recurs.
- Evidence: `analysis_outputs/mpgaming_v13_vs_v23_marnie_population202635_evaluation`.

### Focus-play live telemetry

- `tools/summarize_kaggle_winplan.py` now accepts repeatable
  `--focus-play-id`; use `--focus-play-id 1147` for Jumbo Ice Cream.
- Episode output includes first focus-play turn, same-turn attack recovery,
  first later attack/delay, and attacks after the first focus play.
- Aggregate output compares focus/no-focus win rates and reports recovery rate,
  same-turn attack rate, and median attacks after the first focus play.
- Related tests: six passed, including cumulative-log dedup and later recovery.
- Gold calibration: episode `85023093` used one Jumbo then made five attacks;
  `85023197` used two Jumbo and made two attacks after the first. Both recovered
  to attack on a Jumbo turn. Aggregate recovery and same-turn rates are 1.0,
  with median 3.5 attacks after the first Jumbo.
- Calibration output: `analysis_outputs/mpgaming_gold_focusplay_telemetry_py311`.

## 2026-07-13 09:17 JST - MPGaming v25 validation recovery

- Submitted the proactive v23 package as `54625597`; validation failed after
  two steps with `Validation Episode failed.` Repacking with `main.py` first as
  `54625845` produced the same immediate failure, ruling out member order.
- Reproduced the validator-specific failure by executing `main.py` without
  `__file__`. The v23 `Path(__file__)` initialization raised before the agent
  could return its 60-card deck.
- v25 changes only runtime root discovery: use the archive directory when
  `__file__` exists and `/kaggle_simulations/agent` otherwise. The proactive
  heal, Xerosic/Ascension, Grow-line, and role-aware conversion policy is
  unchanged.
- Paired v23/v25 exact 16-track evaluation matched all 320 game tuples and both
  scored `208-112`; controls and error counts were zero. Normal import,
  no-`__file__` exec, extracted import, and five-game package smoke passed.
- Final archive:
  `candidate_kangaskhan_crustle_mpgaming_v25_runtime_root_compat_mainfirst.tar.gz`,
  SHA256 `D1207336819C9BE3362DE336EC0E7F596BA5ADF133E428E5287C7A4F42EC3EC4`.
- Submission `54626152` completed validation at `600.0`; validation episode is
  `85656851`. The first fetch contains validation only and is stored under
  `analysis_outputs/kaggle_live/submission_54626152_mpgaming_v25`.
- Do not spend another slot while public games are pending. Judge the agent by
  the existing win-plan telemetry: post-Jumbo attack continuation and
  board-clear/deckout are positive; early Jumbo without more attacks,
  especially into Marnie, is the primary warning.

## 2026-07-13 09:43 JST - MPGaming v25 initial public recovery

- The first five public games reached `2-3` and `445.7`, then four consecutive
  wins recovered submission `54626152` to `6-3` and `618.6`.
- Public wins so far cover two Starmie/Froslass opponents, Alakazam, Ogerpon
  toolbox, Hop/Trevenant, and Rocket Mewtwo/Spidops. Losses are
  Starmie/Froslass, a Crustle heal/disruption mirror, and Dragapult.
- The original focus-play telemetry incorrectly reported zero attacks after
  the mirror Jumbo. Attack logs that end a turn may appear only in the next
  opponent/terminal frame. The summarizer now reconstructs an all-seat event
  stream and assigns those attacks to the preceding turn; six tests pass.
- Corrected public telemetry: Jumbo in 3/9 games, `2-1` with Jumbo and `4-2`
  without it, recovery rate 1.0, same-turn attack rate 1.0, median six attacks
  after the first Jumbo. The intended sustain mechanism is present live.
- The mirror loss `85657918` exposed a narrower tactical gap: a nonlethal 120
  attack after healing left our Crustle at 110 after Spiky recoil, inside the
  opponent's public 120 retaliation. A v26 guard is being evaluated but has
  not yet reproduced a real replay decision change and is not promotable.
- Starmie loss `85657425` ended from a sole Crustle with no reserve. Dragapult
  loss `85658412` also began without Poffin or another Basic; solo Crustle was
  initially rational and took three prizes. Do not add broad width/Lillie
  patches from one replay each.
- Decision: keep v25 running while it is recovering and collect enough games
  to separate setup variance from repeated policy failure.

## 2026-07-13 10:15 JST - Balanced-method correction and v27 rejection

- Methodology correction: intended-route execution is one additional axis, not
  the sole objective. Continue evaluating legal-action quality, setup,
  resources, prize race, matchup handling, repeated failures, and broad
  non-regression as in the earlier Silver-range rule-base cycle.
- At 15 public games submission `54626152` was `9-6` around `629.1`.
  Mega Lucario was the only repeated weak bucket at `1-2`; both losses showed
  race pressure but no shared clearly dominated public-state action.
- The two Crustle-related losses lacked a Kangaskhan continuation route, but
  legal Poffin choices or observed draws did not expose a target-selection
  error. v26 changed neither replay and lost two wins over its 400-game mirror
  panel, so it is rejected.
- v27 tested a broader hypothesis from Gold action ordering: preserve
  Ascension and visible fixed-damage KOs, but perform qualifying evolution,
  backup attachment, or thin-board setup before a nonlethal attack.
- v27 failed decisively. Across deterministic duplicate-controlled panels,
  Mega Lucario fell `302/320 -> 164/320`; the broad panel fell
  `199/320 -> 135/320`; aggregate was `501/640 -> 299/640`. There were zero
  duplicate mismatches, action errors, or max-step hits.
- On 15 live replays, v27 changed 68 of 537 decisions, all on existing wins and
  none in the target loss states. This proves the candidate did not reach the
  observed failure mechanism and instead disrupted successful sequencing.
- Latest fetch contains 19 public games, record `11-8`, score `617.7`. Keep v25
  active because no valid replacement exists. New losses `85663563` and
  `85664207` remain for the next classification cycle.
- Evidence: `analysis_outputs/mpgaming_v25_vs_v27_pre_attack_20260713` and
  `analysis_outputs/kaggle_live/submission_54626152_mpgaming_v25`.

## 2026-07-13 - Cynthia Track 5 Champion's Call candidate

- MPGaming submission `54626152` reached 28 public games at `14-14` and
  `591.2`. Mega Lucario and Dragapult win/loss comparison found no repeated
  decision-level defect, and v13 rollback attribution changed only five games
  with a `3-2` record. No valid MPGaming replacement remained.
- Audited four exact-deck nasuo445 Cynthia/Garchomp Gold-rank replays. Baseline
  disagreed with recorded actions on 181/324 decisions. The repeated structural
  bug was Champion's Call: recorded policy used Gabite's free search before
  evolution in all four games, while baseline evolution score 25000 dominated
  ability score 9500 in 29 same-state cases.
- Broad v2 ability-first improved alignment to 147 mismatches but regressed
  Great Tusk `-2/200` and Mega Lucario `-8/40`; it is rejected.
- Narrow v3 only promotes Champion's Call when a legal Garchomp-ex evolution
  targets that same Gabite serial. It improved Gold mismatches `181 -> 161`.
- Paired evidence: targeted `121/400 -> 128/400`; broad
  `174/360 -> 193/360`; aggregate `+26/760`. Great Tusk was neutral and the
  only negative broad cell was TW Shin Marnie `-1/40`. Duplicate controls were
  exact and all error/max-step counts were zero.
- Runtime archive:
  `candidate_cynthia_garchomp_nasuo445_v3_champions_call_runtime_20260713.tar.gz`,
  SHA256 `B05C3386C7F6F92534967A3542405FCB03DE692FAFCF176BACD01DE2E8889342`.
  It has 13 members, exact 60 cards, main-first order, and passed extracted
  import, no-`__file__` exec, py_compile, and five-game smoke.
- Pre-submit hypothesis: this narrow free-ability sequencing fix restores the
  deck's intended setup engine while preserving existing tactical choices.
  Target is broad live improvement over the mature MPGaming 591 plateau; risk
  is the small 1-3 Gold replay sample and remaining local/live policy mismatch.
- Submission is justified because the current and preceding mature agents are
  below 1000, MPGaming is clearly below 700 after 28 games, and Cynthia v3 has
  paired positive evidence. Check validation immediately, then collect public
  replays before any further replacement.
- Submitted Cynthia v3 as Kaggle submission `54628744` at 2026-07-13 10:55
  JST. Validation episode `85668666` completed successfully at `600.0`; the
  first fetch contains validation only under
  `analysis_outputs/kaggle_live/submission_54628744_cynthia_v3`.
- Runtime is confirmed. Do not replace before public evidence. Evaluate the
  full policy: Champion's Call sequencing, Garchomp/Roserade board formation,
  energy and tool allocation, first attack/prize, prize race, matchup results,
  and errors. Ability-use telemetry is one axis, not the sole objective.

## 2026-07-13 - Cynthia initial live feedback and rejected follow-ups

- Submission `54628744` reached eight public games at `4-4`, score `538.2`.
  Loss buckets were Kangaskhan/Crustle, an Alakazam single-active donk, Mega
  Abomasnow/Kyogre, and Starmie/Froslass. The spread does not justify a broad
  one-matchup rewrite.
- In Alakazam loss `85669685`, Cynthia had a lone Gible, empty bench, no basic
  Pokemon in hand, and two Lillie cards. The policy used Hilda for evolution
  and energy before Lillie and was knocked out on turn 5 without a bench.
- v4 reserved a bench slot after the main line became ready. It scored
  targeted `128 -> 127` and broad `180 -> 179`, and activated in none of the
  audited Gold/live replays. Rejected.
- v5 prioritized Lillie in every lone-board/no-basic state. It improved one
  Alakazam policy family but produced `-2/40` in both Archaludon and Mega
  Lucario broad buckets. Rejected as unsafe generalization.
- v6 restricted the rescue to a visible Abra/Kadabra/Alakazam board. It was
  exactly neutral over all non-Alakazam broad cells, but the focused 300-game
  Alakazam panel regressed `179 -> 177`, including seat-1 `-4`; 10 gains and
  12 losses show that fixing the exact live action did not improve the
  adjacent policy population. Rejected.
- There is no valid replacement for the current v3 despite its sub-700 early
  score. Keep collecting live games rather than spending the final daily slot
  on v4-v6. Evidence directories:
  `analysis_outputs/cynthia_v3_vs_v4_reserve_bench_20260713`,
  `analysis_outputs/cynthia_v3_vs_v5_single_active_lillie_retry_20260713`, and
  `analysis_outputs/cynthia_v3_vs_v6_alak_single_lillie_20260713`.

## 2026-07-13 - Cynthia Gabite-width candidate v9

- Cynthia v3 matured to 15 public games at `7-8`, about `486`, and later CLI
  showed `471.1`. It is a valid sub-700 replacement case.
- A semantic audit of four Gold replays found 160/324 v3 mismatches. All four
  showed the same proactive route: use Champion's Call to build multiple
  Gabites before searching Garchomp ex. This is a board-formation policy, not
  a patch for one loss.
- v7 reduced Gold mismatches `160 -> 153` and improved `364 -> 374/960`, but
  regressed Great Tusk by four and Alakazam by three. v8's initial safety IDs
  did not recognize the Crustle board early enough and retained the Great Tusk
  regression.
- v9 adds visible Dwebble/Crustle IDs to the safety set. The full fixed-seed
  suite scored `379/960` versus v3 `364/960`, delta `+15`, with zero errors or
  max-step games. Every matchup aggregate was within `-1` of baseline or
  better.
- The reported expanded-Starmie `-4` was one seat, not the matchup aggregate.
  Direct v8/v9 comparison across all 240 Starmie games was identical in seed,
  result, and steps. Expanded Starmie is `+5` across both seats; standard
  Starmie is `-1`.
- Pre-submit target: improve Cynthia's intended multi-Gabite setup and later
  Garchomp continuity while reverting to the established matchup policy after
  visible Alakazam or Great Tusk/Crustle identification. Main risk is that
  early hidden turns can still trigger before identification.
- Evidence:
  `analysis_outputs/cynthia_v3_vs_v9_full_candidate_20260713`,
  `analysis_outputs/cynthia_v3_vs_v9_crustle_safety_retry_20260713`, and
  `analysis_outputs/cynthia_v7_gold_semantic_mismatch_audit_20260713`.
- Packaged
  `candidate_cynthia_garchomp_nasuo445_v9_gabite_width_crustle_safety_20260713.tar.gz`,
  SHA256 `A4B1CD4AE145A84FBF5436B12BCE4176C939894E97C5469490D35529A685A30A`.
  It has 13 main-first members, exact 60-card rows, source/package equality,
  normal import, no-`__file__` exec, py_compile, and a five-game smoke with
  zero action errors and max-step hits.
- Submitted as Kaggle submission `54630859` at 2026-07-13 12:16 JST.
  Validation episode `85678496` completed at `600.0`; the first fetch has
  validation only and is stored under
  `analysis_outputs/kaggle_live/submission_54630859_cynthia_v9`.
- Package/live attribution passed on the validation replay. Across both seats,
  v3 and v9 differed on one of 124 decisions. At turn 5 Champion's Call, v3
  searched Garchomp ex `381`, while submitted v9 searched Gabite `380`;
  v9 exactly matched the recorded Kaggle action. The other 123 decisions were
  unchanged. Outputs are `validation_v3_vs_v9_seat0.json` and
  `validation_v3_vs_v9_seat1.json` in the submission directory.

## 2026-07-13 - Cynthia v9 first public losses

- First three public games are 0-3, score 414.28: Ogerpon toolbox episode
  85678570, Starmie/Froslass 85679036, and Archaludon 85679525.
- Ogerpon and Starmie replays have zero v3/v9 action differences. Ogerpon was a
  functioning two-Garchomp setup that lost the one-prize Crustle versus
  two-prize Garchomp exchange. Starmie established Mega Starmie before Cynthia
  evolved and cleared multiple 70-HP basics with repeated spread attacks.
- Archaludon had one v3/v9 difference, and it was materially beneficial. v9
  searched Gabite before Garchomp on turn 3, built two Gabite that turn, then
  evolved both to Garchomp on turn 5. v3's premature Garchomp search would not
  create the second line. The loss came after strong opposing Cinderace,
  Duraludon/Cape/Boss, and Archaludon tempo.
- No loss supports reverting v9 or adding a one-replay matchup patch.
- v10 tested proactive Night Stretcher continuity recovery. It scored 247/520
  versus v9 246/520, with Ogerpon neutral, Starmie +3, and Alakazam +1, but
  Cynthia mirror regressed 117 -> 114. Reject v10 under matchup non-regression.
  Evidence: analysis_outputs/cynthia_v9_vs_v10_stretcher_continuity_20260713.
- Public game four, 85680045, was a win over Mega Abomasnow/Kyogre. The live
  record recovered to 1-3 and 470.93. Its 22 target decisions were also exactly
  equal between v3 and v9. Across the first four public games, v9 changed only
  the beneficial Archaludon setup decision described above.
- Public game five, 85680524, was a Starmie/Froslass win, recovering to 2-3
  and 521.68. Its sole v3/v9 difference was again the intended turn-3 Gabite
  search over premature Garchomp, and v9 matched the recorded action.
- In the expanded 200-game Starmie panel, wins established Gabite/Garchomp and
  early Power Weight more often than losses. Losses attacked and prized
  slightly earlier, so faster attacking is not the successful route. Board
  clear/no-active occurred in 36/139 losses and zero wins. The proposed
  Gabite-before-Garchomp rule is already v9 behavior; no new patch is needed.
- Public game six, 85680994, was a second Mega Abomasnow/Kyogre win. v9
  recovered from 0-3 to 3-3 and 544.08 with three consecutive wins. One of 51
  decisions differed from v3 and the submitted v9 action matched the Kaggle
  recording. Keep the recovering submission active.

## 2026-07-13 - Cynthia v11 Poffin role selection

- Public games seven and eight were wins over Marnie/Grimmsnarl and Alakazam.
  v9 reached `5-3`, `617.33`, with five consecutive wins. The Marnie win had
  two v3/v9 differences; both were the intended Gabite-width search and both
  matched the recorded live action. Both wins established Garchomp and
  Roserade, attached Power Weight, and maintained attack continuity.
- The Gold semantic audit exposed a structural gap: after Buddy-Buddy Poffin,
  v9's `TO_BENCH` choices all received the same fallback score. v11 changes
  only this selection context, prioritizing Gible width below three copies,
  then Roselia support below two copies, then the first Spiritomb.
- Development evaluation: `338 -> 365/720`, `+27`; both seats improved,
  duplicate controls were exact, and errors/max-step were zero.
- Independent seed-`202653000` holdout: `225 -> 245/480`, `+20`; each seat
  gained ten wins. Combined Starmie improved `28 -> 32/80`, exact Cynthia
  mirror `23 -> 26/40`, and Alakazam `17 -> 23/40`. Archaludon regressed by
  three and Great Tusk/Crustle by two, so these remain explicit live risks.
- Across 1200 games the aggregate gain is `+47`. Evidence is in
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713` and
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_holdout_20260713`.
- Public games nine and ten then lost to Starmie/Froslass and Ogerpon toolbox,
  leaving v9 at `5-5`, `551.68`. v11 changes two Poffin decisions in the
  Starmie loss but zero of 126 decisions in the Ogerpon loss. This is not an
  Ogerpon loss patch; it is a broad board-formation candidate.
- Packaged
  `candidate_cynthia_garchomp_nasuo445_v11_poffin_role_selection_20260714.tar.gz`,
  SHA256 `E7F2FF3080DA20352BCFECF793B025357771F33C9FE0F285AA346162C98E4228`.
  It has 13 main-first members, 60 deck rows, passes py_compile, normal import,
  no-`__file__` execution, and a 12-game archive smoke with zero errors.
- All five July 13 slots are used. If submitted v9 remains below 700 and does
  not resume a sustained recovery by the next reset, v11 is the first queued
  evidence-backed probe. Monitor Archaludon and Great Tusk/Crustle explicitly.

## 2026-07-13 - Cynthia v12 support pivot and live recovery

- Submission 54630859 reached 12 public games, 7-5, score 617.35. New wins
  85683375 (Dragapult) and 85683851 (Mega Lucario) formed both the Garchomp
  main line and Roserade support before closing the game.
- A Gold mismatch pattern suggested changing search role after the main line
  is wide enough. v12 keeps v11's Poffin setup and changes only TO_HAND:
  after at least two Gible/Gabite/Garchomp-ex bodies, prefer Roserade if an
  in-play Roselia can evolve, else Roselia while support width is below two.
- Root review caught and removed unintended propagation into LOOK, TO_DECK,
  and TO_DECK_BOTTOM before evaluation.
- Development seed 202643000: v11 365 -> v12 373/720 (+8). Unused holdout seed
  202663000: 240 -> 240/480 (neutral). Controls were exact with zero action
  errors and zero max-step games.
- Combined bucket deltas included Archaludon +6, Dragapult +3, Mega Lucario
  +2, exact Cynthia -4, Great Tusk/Crustle -2, and Ogerpon -2. Exact Cynthia
  was neutral on blind holdout; the two -2 buckets were -1 in each seed.
- Four changed decisions in Gold episodes 85023189 and 85023194 matched the
  recorded action; 85023208 was unchanged. Evidence is under
  `analysis_outputs/cynthia_v12_evaluation`.
- Packaged
  `candidate_cynthia_garchomp_nasuo445_v12_support_pivot_20260714.tar.gz`,
  SHA256 `B52DA76B3860299A3F34F4DCFB2E400FC287C33E0776E507BF8EC46559E17B65`.
  It has 13 main-first members, 60 deck rows, normal import, no-`__file__`
  execution, and a 10-game archive smoke with zero errors.
- v12 replaces v11 as the queued candidate, but v9 is recovering and must not
  be replaced immediately. At the next reset, refresh live maturity first and
  monitor exact Cynthia, Great Tusk/Crustle, and Ogerpon if v12 is submitted.

## 2026-07-13 - Cynthia v13 development-before-Corkscrew

- Submission 54630859 reached 21 public games at 9-12 and 549.44. After the
  prior Marnie/Mega-Lucario/Alakazam/Hop window, the latest five went 1-4:
  loss Mega Lucario 85686228, win Mega Lucario 85686715, loss unknown
  85687191, loss Dragapult 85687662, and loss Starmie 85688147. Execution
  remained COMPLETE, so this is a mature weak gameplay result, not an error.
- Replay attribution showed v11/v12 already repair Poffin setup in the
  Alakazam and Hop losses. All 45 Marnie decisions are unchanged, so this
  window supports the queued setup changes but no new matchup patch.
- Gold replay analysis found 11 states across 85023189 and 85023194 where v12
  selected turn-ending Corkscrew Dive before a positive development action.
  v13 orders PLAY/EVOLVE/ATTACH/ABILITY/RETREAT before Corkscrew only with
  active Garchomp ex, Roserade online, and no final-prize Corkscrew KO.
- Development seed 202643000: 373 -> 402/720 (+29). Untouched blind seed
  202683000: 261 -> 276/480 (+15). Combined +44/1200; both seats positive,
  duplicate controls exact, action errors and max-step games zero.
- Bucket deltas included exact Cynthia +11, Alakazam +7, combined Starmie
  +23, Mega Lucario +4, Great Tusk -2, and Ogerpon -2. Marnie and Archaludon
  varied by seed and remain live watch items.
- Independent Python-3.11 trace panel: v12 84 -> v13 95/160. First evolution,
  first attack, and first prize were earlier, first-attack line was wider,
  Corkscrew Dive fell 1335 -> 1028, and Draconic Buster rose 282 -> 453.
  The failed system-Python trace directory without `_py311` is invalid.
- Packaged
  `candidate_cynthia_garchomp_nasuo445_v13_corkscrew_development_order_20260714.tar.gz`,
  SHA256 `97E9092DC7387BABE564E5573DBA2DEB18183D608C683113B5AE769A18B659C7`.
  It has 13 main-first members, 60 cards, normal import, no-`__file__` exec,
  and a 10-game archive smoke with zero errors.
- v13 supersedes v12 as the next-reset candidate. Pre-submit target is broad
  conversion into complete Garchomp/Roserade boards and Draconic Buster, not
  one live loss. Monitor Great Tusk, Ogerpon, Marnie, and Archaludon. At the
  next reset, submit unless a final fresh check materially overturns v9's
  21-game mature weak diagnosis.

## 2026-07-13 - Cynthia v13 paired flip audit

- The full negative set contains 39 flips. In 38, v13 first differs at the
  new Corkscrew ordering guard; 19 postpone an immediately available KO.
  Candidate terminal losses were 23 prize losses, 14 deck-outs, and two other
  or pre-divergent cases. Great Tusk losses were predominantly deck-out races.
- A separate positive retrace covered eleven representative gains. Six also
  postponed an immediate KO, then won after a development action. This makes
  a blanket "take every KO" rollback unsafe despite its clean explanation of
  many losses.
- No matchup, board width, hand size, or visible prize condition separated the
  positive and negative immediate-KO deferrals reliably. The evidence supports
  timing attribution but not a safe v14 rule.
- Decision: freeze v13 and spend no implementation/evaluation cycle on an
  ungrounded exception. Its live probe must be judged on broad rule quality as
  well as intended-board formation: setup, resources, attack and prize tempo,
  continuity, matchup spread, and repeated decision errors. Great Tusk,
  Marnie, Archaludon, and Ogerpon remain explicit regression watch buckets.

## 2026-07-13 - Cynthia v13 live Kangaskhan adjacency

- v9 reached 24 public games at 11-13 and 566.996. New games were loss
  85688629 versus Kangaskhan/Crustle, then wins 85689113 versus Hop/Trevenant
  and 85689595 versus Cynthia/Garchomp. The score remains mature weak.
- The Kangaskhan loss formed a six-body board and attacked 19 times, but
  missed six attack turns after first attack. v13 changes nine recorded
  choices and repeatedly defers late Corkscrew while the deck approaches
  zero. This is a timing warning rather than a deck-formation failure.
- Unused-seed Dung holdout: v12 296 -> v13 299/400. DapperOctopus exact public
  deck plus Dung policy: 146 -> 155/240, both seats positive, duplicate
  controls exact, no errors. Evidence:
  `analysis_outputs/cynthia_v13_kangaskhan_holdout_202703000` and
  `analysis_outputs/cynthia_v13_dapper_exactdeck_holdout_202713000_seeded`.
- All 122 gain/loss flips were re-audited for late public-state gates. No
  turn, deck-count, full-bench, KO, prize, or action-kind separator removed
  the live behavior without touching documented gains. Do not build v14.
- The archive was rechecked at SHA256
  `97E9092DC7387BABE564E5573DBA2DEB18183D608C683113B5AE769A18B659C7`:
  main-first, 13 members/12 files, 60 cards, source-identical, compile/import
  clean, and runtime smoke clean. v13 remains the next-reset submission.

## 2026-07-13 - Cynthia v13 full live exposure audit

- v9 reached 27 public games, 12-15, score 561.229. The latest sequence was a
  Mega Lucario win and losses to Alakazam and Mega Lucario. It remains a
  mature below-Bronze submission.
- Replaying v13 on all 27 public observations changed 86/1,674 decisions in
  22 games, for 94.86% action agreement. Changes are broad but bounded:
  MAIN 44, TO_BENCH 25, TO_HAND 17; early/mid/late 20/24/42.
- Exposure by matchup: Cynthia 24 mismatches in 8/10 games, Mega Lucario 12
  in 4/5, Hop 13 in 2/2, Ogerpon 13 in 2/2, Alakazam 5 in 2/2, Starmie 2 in
  1/2, Kangaskhan 9 in 1/1. Marnie has zero changes. Alakazam has no
  Corkscrew deferral, while Ogerpon/Hop/Lucario/Kang are timing watch buckets.
- Current 27-game process baseline is stored in
  `analysis_outputs/kaggle_live/submission_54630859_cynthia_v9/winplan_20260713_1408`.
  Wide first attack occurs in 77.8%, first-prize wide line in 63.0%, Power
  Weight-to-Garchomp in 63.0%, Poffin use in 70.4%, and median missed attacks
  after first attack is zero. Wide starts win 47.6% versus 33.3% for thin.
- Detailed exposure outputs are under
  `analysis_outputs/kaggle_live/submission_54630859_cynthia_v9/v13_exposure_audit_20260713_public`.
  These metrics fix the post-submit attribution plan before live outcomes are
  known and prevent judging only win-plan formation or only loss suppression.

## 2026-07-13 - Cynthia deck-theory audit

- The live v9 result is now 14-19 over 33 public games at 549.2219. Execution
  is COMPLETE, the final sequence is loss/win/win/loss, and no later public
  game was available at the refresh. This remains a mature below-Bronze result.
- External strategy references, the local card engine, and four exact nasuo445
  Gold replays were reconciled before another candidate was selected. The
  stable plan is wide Gible/Roselia setup, preserved Gabite Champion's Call
  engines, Garchomp plus Roserade midgame, Corkscrew tempo, durable main-lane
  resource allocation, a preloaded backup, and selective Buster conversion.
- v13 covers setup/search and development ordering, but scores Basic and Rock
  Fighting identically, lacks active/backup attachment roles, and gives Buster
  a constant high score. These are policy gaps rather than deck-list gaps.
- Corkscrew thresholds 5,000/4,000 lost on development. Threshold 3,000 was
  +4/720 development but -5/480 blind, with six gains and eleven losses, so all
  three threshold variants are rejected.
- The next experiment changes only Rock-Energy and backup-attacker allocation.
  It must pass the same 720-game development and 480-game blind gates before it
  can replace the already packaged v13 next-reset fallback.

## 2026-07-13 - Cynthia v17 resource-allocation promotion

- v17 distinguishes Rock from Basic Fighting, completes an unready active
  Garchomp first, then preloads the next bench Garchomp/Gabite/Gible. It does
  not change the 60-card list, attack scoring, setup/search, matchup guards,
  Power Weight, or Spiritomb.
- Gold replay mismatch count improved 145 -> 141/324. The four fixes were the
  intended Rock search/attachment actions in 85023167, 85023189, and 85023194;
  no previous Gold agreement was lost.
- Paired results versus v13 were +14/720 development, +6/480 blind, and +3/480
  unused holdout, total +23/1,680. Duplicate controls were exact and no action
  errors/max-step games occurred. Blind seat-0 -4 did not reproduce in the
  holdout, which was neutral for that seat.
- Mega Lucario is the only repeated adjacent warning: +1 development, -3
  blind, -2 holdout. Exact loss/gain flip attribution is in progress before a
  component ablation or matchup rule is considered.
- Packaged
  `candidate_cynthia_garchomp_nasuo445_v17_rock_backup_allocation_20260714.tar.gz`,
  SHA256 `3756036C39C79CD2C9ED483B94FF236FA0BE74FD1B939DB666AFB2DD71D41E80`.
  Archive checks: 13 main-first members, exact 60 cards, source/deck equality,
  compile/import/no-`__file__` clean, and 10-game Mega Lucario smoke clean.

## 2026-07-13 - Cynthia Rock ablation stopped; v17 retained

- Fresh live v9 state is 34 public games, 16-18, score 565.8767 after two
  wins. It remains mature below Bronze and does not justify retaining v9 at the
  next reset.
- v18 removed the bench-backup override and scored 102/140 against v13's 106
  in the fixed Mega Lucario gate. v19 also removed the active-completion
  override and reached 105/140. Both were rejected.
- v20-v21 used only public deck-theory readiness: prefer Rock when Garchomp is
  formed or immediately evolvable from hand, not for a damaged Active
  Garchomp. Both tied 106/140 but eliminated only two of four regressions.
- Full v21 results were +7/720 development, 0/480 blind, and -4/480 unused
  holdout, with repeated Archaludon -2/-2. Combined +3/1,680 is insufficient
  because the holdout and repeated-matchup gates failed.
- v17 remains selected at +14/+6/+3 across the same three panels, +23/1,680.
  v18-v21 must not be submitted. Next theory work is Buster KO/prize
  conversion and post-discard attack continuity, not another exact-loss Rock
  guard.

## 2026-07-13 - Cynthia v22 Buster conversion selected

- Engine behavior confirms Corkscrew is 100 plus draw-to-six, while Buster is
  260 plus discard-all-Energy. v17's fixed 18,500 Buster base caused Buster in
  40/41 audited dual-legal states, including 17 Corkscrew-also-KO and seven
  non-KO states. The three recorded Busters were all KOs.
- v22 approves only a Buster-only KO that finishes the game, takes multiple
  prizes, or preserves continuity through an energized bench Garchomp/Gabite/
  Gible. No matchup, turn, target id, or opponent identity condition exists.
- Exact replay gate: approved 13/13 Buster; rejected 0/28 Buster; 41/41 states
  reconstructed, zero errors. Gold agreement stays 141 mismatches/324.
- Versus v17, v22 scored +20/720 development, +26/480 blind, and +8/480
  unused holdout, total +54/1,680. Both seats improved in every panel and all
  combined matchup deltas were nonnegative. Controls exact, zero errors.
- Packaged archive SHA256
  `2644BD391D286A16414083244A4DE3E2F9B40A1D4D321B7C6009037F81C912C3`:
  13 main-first members, exact 60 cards/source, compile/import/no-file and
  10-game smoke clean. v22 is the next-reset probe; v17 is rollback.

## 2026-07-13 - Cynthia v22 independent confirmation

- Unused seed 202807131 reproduced the gain against the 12-opponent panel:
  v17 279 -> v22 302/480 (+23), with +11/+12 by seat, exact duplicate
  controls, and no invalid report. The only matchup negatives were Starmie
  expanded -1 and Marnie Sota -2.
- A separate 80-game trace showed why: v22 cut Buster 274->138, increased
  Corkscrew 335->504 and total attacks 799->836, reduced missed attack turns
  87->67, and improved wins 35->43 without materially changing first-attack
  timing or first-attack board width.
- Live v9 is 17-18/35 at 572.3024 after three consecutive wins. This is still
  below Bronze. The July 13 quota is exhausted, so v22 remains queued for the
  expected July 14 reset rather than replacing v9 immediately.

## 2026-07-13 - Cynthia v22 live-state gate audit

- Current 35-game matchup record: Mega Lucario 5-3, Alakazam 3-2, Starmie
  1-3, Ogerpon 0-3, Marnie 2-1, Dragapult 2-1, with smaller buckets making up
  the remaining games.
- v9 reproduces all 2,160 live decisions. v17 differs on 146 and v22 on 173.
  All 27 added v22 changes are Buster deferrals, not new matchup exceptions.
- `tools/audit_cynthia_buster_replays.py` classifies every dual-legal state.
  On this corpus v22 uses Buster in 13/13 approved states and 0/28 rejected
  states; unsafe Buster count is zero. Five rejected states use Corkscrew and
  23 finish useful development first.
- This audit is the frozen post-submit reference. Starmie and Ogerpon are
  watch buckets, but no pre-submit exact-loss patch is accepted.

## 2026-07-13 - Cynthia exact-live deck panel and classifier fix

- The old Ogerpon aggregate was false. Exact decks resolve to
  Crustle/Munkidori, Cubchoo/Articuno, Teal Ogerpon/Clefairy/Crustle, plus
  separately classified Kangaskhan/Crustle and pure Crustle games. Required
  shell signatures now replace partial-marker ties in the classifier.
- After reclassification, Starmie is the only repeated weak live family at
  1-3. The control-family losses are singletons and should not be merged into
  one matchup target.
- v17/v22 comparison on nine exact live 60-card lists, with fixed nearest
  public policy proxies, finished 305 -> 324/780 (+19). Every style is
  nonnegative after confirmation seeds. Pure Crustle's temporary -3/80 did
  not reproduce and finished 12-12/140.
- No new matchup patch is accepted. v22 remains the next-reset probe.

## 2026-07-13 - Cynthia v22 strong local-policy panel

- The earlier exact-deck safety panel was supplemented with six stronger
  runnable policies: historical Archaludon peak, Shumpei Archaludon,
  MPGaming Kangaskhan/Crustle v23, Tonakai and Kazuki Marnie, and v22 mirror.
- On seed 202857313, v17 scored 159 and v22 163/360 (+4). Per-style deltas
  were +4, -3, +2, +2, -1, and 0; controls were exact and reports valid.
- The two initial negative styles were independently repeated at seed
  202867313. Shumpei changed to +6 (18 -> 24/60), and Kazuki was neutral
  (38 -> 38/60), making the confirmation 56 -> 62/120.
- The initial negatives did not reproduce, so v22 stays frozen without a
  narrow patch. These policies are stronger local opponents, but they still
  do not reproduce the hidden decision policies of the live Kaggle agents.

## 2026-07-13 - Cynthia v23 theory-sequencing candidate

- v22's Gold mismatch taxonomy identified evolution/development order as the
  largest remaining class (54/141 mismatches). The reusable issue was not a
  single loss: free Champion's Calls on other Gabite were left unused before
  Garchomp evolution.
- v23 ranks every currently legal Champion's Call above only
  Garchomp-ex-on-Gabite evolution. Higher-scored unrelated actions remain
  ahead, so this is narrower than the rejected global Call-priority policy.
- Exact Gold mismatch improves 141 -> 133/324 without losing a prior exact
  match. Live-v9 exposure is 11/2,160 decisions, exclusively evolution ->
  Call.
- v22 -> v23 paired gates: broad 722 -> 721/1,200, strong policies 163 ->
  167/360, exact live decks 159 -> 160/360, historical Great Tusk/Lucario 99
  -> 100/480. Combined 1,143 -> 1,148/2,400; controls exact, zero errors.
- Selected archive:
  `candidate_cynthia_garchomp_nasuo445_v23_allcall_before_evolve_20260714.tar.gz`,
  SHA256 `C8AD5F9BA979EA7A28732DB516C8B0681D310E3924319D08379C67E0C628CCD1`.
  It is the next-reset live probe; v22 is rollback. The small local delta is
  documented explicitly and is not treated as evidence of Bronze/Silver.

## 2026-07-13 - Cynthia opening-width experiment stopped at v28

- Fresh live state for submission 54630859 is 37 public games, 17-20, score
  561.3526. The two newest losses are Dragapult episode 85711338 and
  Starmie/Froslass episode 85712701. This remains a mature weak baseline.
- v24 tested a deck-theory hypothesis rather than an exact-loss rule: on turns
  1-2, with fewer than two main-line bodies and no main-line Energy, play
  available width/search before the first Rock Fighting Energy or Power
  Weight. Basic Fighting and unrelated actions were unchanged.
- The rule improved exact Gold mismatch 133 -> 130/324. Paired results were
  +5/720 development, +1/360 strong, and +7/480 unused broad. The gain was
  concentrated in player 1, consistent with an opening-order effect.
- Safety failed on exact live lists: -2/360, then -1/240 when Dapper and pure
  Crustle were repeated. Direct traces isolated turn-2 Power Weight/Rock
  delays under visible Dwebble/Crustle pressure.
- v25-v27 tested evolved-Active, energized-Active, and Crustle-plus-Energy
  guards. v28 used visible Dwebble/Crustle as a matchup-level durability
  guard and restored the two known flip seeds, but fresh evaluation was
  broad 0/480, strong 0/360, exact Crustle -1/240, combined -1/1,080.
- v24-v28 are rejected and must not be submitted. The reusable finding is
  that opening width and early durability resource order cannot yet be
  separated safely from the available public state. v23 remains selected;
  archive SHA256 C8AD5F9BA979EA7A28732DB516C8B0681D310E3924319D08379C67E0C628CCD1.

## 2026-07-13 - Cynthia v35 reliable development selected

- Damaged-Active rotation variants v29-v31 were rejected. The best guarded
  version was only +1/1,080 and the KO veto removed its sole Archaludon gain;
  public state did not support a safe hand-written rotation threshold.
- Live Starmie/Froslass plan auditing showed all three losses lacked a charged
  backup, while the win built two Garchomp and two Roserade. Gold history was
  mixed, so the implementation was narrowed to guaranteed development before
  a non-immediate-KO attack from an Active one-Energy Garchomp with no ready
  backup.
- v35 permits only benched main-line attach/evolve, Night Stretcher recovery,
  and an empty-Bench midgame Fighting Gong at four or five prizes. It does not
  force direct Gible or Poffin and retains all v23 tactical and safety rules.
- Paired evidence is +9/1,920 on development gates and +2/1,080 blind, for
  +11/3,000 total. No opponent bucket regressed, both seats were stable, and
  controls/errors/max-step checks passed.
- Next-reset archive:
  `candidate_cynthia_garchomp_nasuo445_v35_reliable_development_before_attack_20260714.tar.gz`,
  SHA256 `E691A08AC140EC7D91733BC7D70D381D3064742F0ED41F19CB524071B9ED2FA7`.
  Exact 60 cards, 13 members, compile/import/no-file and two-seat smoke pass.
  Hypothesis: improve post-first-attack continuity and reduce board collapse.
  Risk: development may surrender tempo; v23 is the rollback if live follow-up
  attacks do not increase.
- Fresh submission 54630859 state at 20:30 JST is COMPLETE, score 559.1698,
  18-22 over 40 public games. The latest Hop/Trevenant loss is a singleton;
  Starmie/Froslass is the repeated severe bucket at 1-4. The submission is
  mature weak and v35 remains the evidence-backed reset replacement.
- Replay attribution: v35 changes one of 250 reconstructable decisions across
  the five Starmie games, episode 85682411 step 56, from non-KO Corkscrew to
  Night Stretcher for a discarded Gible. It changes none of 49 decisions in
  latest Hop loss 85732359. Therefore the live hypothesis is intentionally
  narrow: improve one class of backup sequencing, not guarantee a Starmie fix
  or patch a singleton Hop result.

## 2026-07-13 - Cynthia v36 same-turn Gible order rejected

- The remaining early Starmie failure exposed one turn-2 state where Rock
  Energy was attached before the second Gible was benched. The Gible was still
  benched later in the same main phase, so v36 tested causality rather than
  treating the snapshot mismatch as an error label.
- v36's visible-Starmie-only rule was +1/64 exact Starmie, exact on known and
  fresh Crustle checks, and neutral over a 480-game broad panel. Seven focused
  tests passed and the deck remained byte-identical.
- Blind confirmation rejected the apparent gain: 426 -> 425/600, no game flip
  or readiness difference; the negative bucket rerun was 71-71/120. This is
  neutral safety, not repeated improvement.
- Do not package or submit v36. The unresolved failure is later Gabite access
  and line survival, not the order of already-selected same-turn Gible and
  Energy actions. v35 remains the selected reset candidate.

## 2026-07-13 - Cynthia v37-v39 Poke Pad target research

- Gold search/support mismatches exposed a real public Poke Pad source marker
  and a repeated early Gible-target pattern. v37's combined Pad-first plus
  Gible-target rule was +23/1,440 across broad, strong, and exact-live panels.
- Ablation isolated the gain: v38 Pad-main-order-only was -3/1,440, while v39
  Gible-target-only was +22/1,440. The result shows that choosing the Basic line
  from Poke Pad mattered; merely playing Pad earlier did not.
- Persistence checks raised v39 to +32/2,400 overall, but Archaludon player 0
  repeated at -3/180 and finished -6/210 with the original cell. Six beneficial
  and nine harmful target shifts had no separable public board/hand/Energy/line
  feature. No safe guard exists from current evidence.
- Reject v37-v39 despite the aggregate gain. Do not hide a repeated adjacent
  regression behind the average. Roserade-before-Call was also not implemented
  because five of six examples came from losses and no public discriminator
  existed. v35 remains the reset submission candidate.

## 2026-07-13 - Cynthia v40-v41 early exposed-Gible route rejected

- Fresh live state reached 41 public games, 19-22, score 576.65 after Alakazam
  win 85746953. The submission remains mature below Bronze. Starmie/Froslass
  is 1-4 and the combined Crustle/control variants are 0-4.
- Starmie replay audit found two missed early Poke Pad-to-Gabite windows and
  one supporting win. Two other losses already reached turn-5 Garchomp, so the
  route is not a full matchup explanation.
- v40 used public `appearThisTurn` but fired in later Crustle states. v41 added
  `turn <= 3`, preserved three intended Starmie windows, and changed zero
  actions in Crustle episode 85678570.
- v41 scored +5/600 Starmie, +5/720 broad, +1/360 strong, -1/360 exact-live,
  and +5/3,000 overall. Archaludon independently regressed -4/420 and -2/420,
  pooled -6/840. Controls were exact and errors/max-step were zero.
- Reject v40-v41 and skip blind panels. This confirms that early Gible access
  can be a real local improvement while remaining unsafe for the adjacent
  Archaludon population. v35 remains the next-reset candidate.
- The four Crustle/control losses primarily reflect one-prize versus two-prize
  exchange structure. v35 already prevents the only repeated narrow policy
  leak, nonterminal one-prize Buster without a loaded backup. Do not add a
  blanket anti-Crustle prize-map rule.

## 2026-07-14 - Cynthia absolute audit invalidates the v35 reset probe

- Root re-ran/re-aggregated v9, v22, v23, and v35 on identical strong,
  exact-live9, and broad schedules. Totals were 584, 720, 728, and 734 wins out
  of 1,440. v35 was only 44.17% strong and 41.39% exact-live9, while its gain
  over v23 was six games (+0.42 percentage points).
- A deterministic evaluator incorrectly copied v35 `candidate_win` totals into
  v23. Raw `baseline_win` verification corrected v23 from 734 to 728. The
  runner schedules themselves were complete, unique, and error-free.
- The nine exact-list opponent proxies matched only 273/506 (53.95%) actions
  from their source live replays. Kangaskhan/Crustle was 32.43%; several
  Starmie/control proxies were below 60%. Exact deck reproduction was being
  mistaken for live policy reproduction.
- Gold agreement was v9 51.85%, v22 56.48%, and v23/v35 58.95%. v35 made no
  additional Gold agreement gain. It changed only 3/1,212 decisions relative
  to v23 across all 22 live losses.
- Suspend v35 submission. Remain on Cynthia, but rebuild separate
  Starmie/Froslass, Kangaskhan/Crustle, and control policy proxies before more
  local optimization. Full evidence is in
  `docs/cynthia_absolute_strength_audit_2026-07-14.md`.

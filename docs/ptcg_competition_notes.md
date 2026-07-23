# Pokemon TCG AI Battle Competition Notes

Last updated: 2026-07-12 JST

## Competition Mechanics

- Simulation competition slug: `pokemon-tcg-ai-battle`
- Submission format: `submission.tar.gz` with `main.py` at archive root, plus `deck.csv`; practical submissions also include the official `cg/` API directory.
- Daily limit: 5 submissions.
- Active submissions: latest 2 only. The best scoring active submission is shown on the leaderboard.
- Rating is Gaussian-style skill rating. New submissions start around `mu=600`; validation first plays the submission against itself.
- Games continue after the submission deadline for leaderboard convergence.

## Important Discussion Findings

- `Game Engine Source Code` says `ptcg_engine.zip` was added to the Data page. It is intended for local testing, verification, and training in this competition only.
- `Daily Top Episodes Datasets` says Kaggle publishes top episodes daily in `kaggle/pokemon-tcg-ai-battle-episodes-index`. Episodes are selected by highest average participant rating, so they are biased toward top competitors and useful for replay analysis, imitation learning, and meta scouting.
- `Differences Between the Official Pokemon TCG Rules and the Simulator Behavior` confirms simulator behavior is authoritative. Notable points:
  - Some attacks are not selectable if their effect cannot resolve, even if official rules might allow declaring them.
  - Certain simultaneous KO prize-taking orders differ.
  - Passive/continuous effects are automatic; explicit abilities only need selection when they appear in `Options[]`.
  - Optional setup benching can be skipped by returning `[]` when `minCount == 0`.
- `June 30 Update` changed the environment:
  - `cg` now includes macOS and Linux ARM64 binaries.
  - Step-limit draw behavior was changed so looping players should eventually lose by timeout.
  - Target match rate was raised to 48/day/submission.
  - Matchmaking now includes a 10% random-opponent probability, which rewards robust decks that do not only beat nearby high-rating opponents.
- `Reminder about the Kaggle Simulation Competition Format` clarifies there is no planned leaderboard reset; the latest two submissions at deadline are the ones calibrated in the final period.

## Code / Public Notebook Findings

- Official pinned samples:
  - Mega Lucario ex sample rule-based agent: public score around 600.
  - Dragapult ex sample rule-based agent: public score around 600.
  - Mega Abomasnow sample: around 509.6.
- Community matchup data for the four sample agents:
  - Mega Lucario ex: 60.4% overall.
  - Dragapult ex: 55.6% overall.
  - Iono: 43.8% overall.
  - Mega Abomasnow ex: 40.2% overall.
- `I have one REAR card` by Koushik Rudra:
  - Public score: 1072.3.
  - Strategy: Great Tusk + Crustle + Terrakion library-out/control.
  - Good evidence because it has a real public leaderboard score and a complete generated `submission.tar.gz`.
- `A Sample Archaludon: 75% WR vs my 1300+ Starmie` by tomatomato:
  - Claims 74.4% win rate over 1000 local games against the author's 1300+ Starmie/Froslass submission.
  - Strategy: Archaludon ex / Cinderace metal-tempo.
  - Important caveat: the result is specifically strong into Starmie/Froslass because Froslass is Metal-weak; it may not transfer equally to Cinderace-Starmie or Dusknoir Bomb Starmie.
  - The author did not submit it because of the latest-two-active-submissions rule, not because the idea was weak.

## Current Medal-Range Evidence - 2026-07-12 19:53 JST

- Fresh leaderboard snapshot has `4,858` teams.
- Rank 20 / gold boundary: `1082.2`.
- Rank 100 / silver lower boundary: approximately `989.0`.
- ShumpeiNomura is rank 27 at `1066.6`, inside high silver after being rank 20
  at `1083.6` in the 17:10 snapshot. Active submission `54588240` has
  83 fetched episodes and remains Archaludon. The team's second active
  submission is `993.8`, also inside silver. Public episode `85543431`
  confirms that second submission
  `54588173` is also Archaludon; it replaces one Energy and one Full Metal Lab
  from the gold-boundary list with two Switch.
- Current Shumpei deck core: Duraludon 4, Archaludon ex 4, Relicanth 2,
  Team Rocket's Articuno 1, Metal Energy 13, Night Stretcher 4, Carmine 4,
  Judge 2, Xerosic 1, Full Metal Lab 4.
- The daily top-40 samples above rating 1250 contained only Alakazam and Great
  Tusk/Crustle. That extreme-score slice must not be generalized to the whole
  medal range; Archaludon is demonstrably present at the live silver top and
  has recently touched the gold boundary.
- Our sustained historical Archaludon package is being revalidated as
  submission `54600598`. Its public record is `24-16` at `872.8`; it has not yet
  re-established silver. Same-deck alternate-policy submission `54601378` is
  `22-11` at `939.9`; it peaked at `974.8` but did not cross silver.

## Initial Strategy Decision (Historical)

For the first one-shot submission, the best risk/reward choice is the Archaludon ex / Cinderace public agent:

- It targets a high-rating Starmie/Froslass meta deck with a reported 74.4% local win rate over 1000 games.
- It is more recent and more meta-aware than the older sample decks.
- The latest matchmaking update adds 10% random opponents, but Archaludon is still a coherent tempo deck rather than a narrow exploit.
- The alternative Great Tusk/Crustle library-out submission has stronger leaderboard evidence at 1072.3 and is the fallback if Archaludon validation errors.

## Local Artifacts

- Chosen submission archive: `submission_archaludon.tar.gz`
- Source directory: `submission_archaludon/`
- Downloaded public notebook outputs:
  - `notebook_output/masamikobayashi_archaludon/`
  - `notebook_output/koushikrudra_i-have-one-rear-card/`

## Submitted Version

- Submitted via Kaggle Notebook because Chrome extension file-upload permissions blocked direct local archive upload.
- Notebook: `rurururumi/a-sample-archaludon-75-wr-vs-my-1300-sta-2e4200`
- Modification: changed the final deck cell to generate `submission.tar.gz` from `main.py` and `deck.csv`.
- Submitted version: Version 3.
- Kaggle Submissions status: `Error`.
- Detail shown by Kaggle: `Validation Episode failed.`
- Likely cause: the notebook-generated `submission.tar.gz` included `main.py` and `deck.csv`, but likely did not include the `cg/` API directory used by `main.py`.
- Submission description: `Notebook A Sample Archaludon: 75% WR vs my 1300+ Sta 2e4200 | Version 3`

## Local Verification

- `submission_archaludon/main.py` imports successfully with Python 3.12.
- `submission_archaludon/deck.csv` has 60 lines.
- `submission_archaludon.tar.gz` contains:
  - `main.py`
  - `deck.csv`
  - `requirements.txt`
  - `cg/`
- One local Archaludon self-play game completed without exception in 133 steps.

## Local Analysis Environment

- Local analysis scripts live in `tools/`.
- `docs/analysis_environment.md` explains how to:
  - dump card and attack metadata,
  - summarize deck lists,
  - run local games through the packaged `cg` engine,
  - summarize public episode JSON datasets,
  - and use the results to improve a rule-based agent.
- Official `ptcg_engine.zip` should be unpacked under `external/ptcg_engine/` if engine source inspection is needed.

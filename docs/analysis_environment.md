# Analysis Environment

This repository now has a small local analysis toolkit for the Pokemon TCG AI Battle competition.

It is designed for three loops:

1. Check engine behavior locally.
2. Run matchup tests between agents.
3. Summarize public episode JSON files to scout the meta.

## Official Engine Source

The official game engine source is provided on the Kaggle competition Data page as `ptcg_engine.zip`.
Download it manually from Kaggle and unpack it into:

```text
external/ptcg_engine/
```

After unpacking the current zip, the source root is:

```text
external/ptcg_engine/ptcgProgram 22/
```

The current scripts do not require the source tree to be present. They use the packaged `cg` API and native engine from:

```text
submission_archaludon/cg/
```

Use the source tree when you need to inspect simulator internals, confirm edge cases, or build faster training tooling. Use the packaged `cg` API when you only need faithful local games.

## Python

On this machine, use the Codex bundled Python:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" --version
```

The system `python` may be too old for the `cg` type annotations.

## Dump Card Metadata

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\dump_card_catalog.py
```

Outputs:

- `analysis_outputs/catalog/cards.csv`
- `analysis_outputs/catalog/attacks.csv`
- `analysis_outputs/catalog/cards.json`
- `analysis_outputs/catalog/attacks.json`

Use these files to map card IDs and attack IDs to names.

## Summarize A Deck

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\summarize_deck.py --deck submission_archaludon\deck.csv
```

Output:

- `analysis_outputs/deck_summary.csv`

This is the quick way to inspect a copied public deck or a new candidate deck.

## Import Public Agents

Import a public notebook output directory or a `submission.tar.gz` that contains `main.py` and `deck.csv`:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\import_public_agent.py notebook_output\masamikobayashi_archaludon --name archaludon_public --overwrite
```

Imported agents live under:

```text
meta_agents/
```

They do not need to contain `cg/`; the local test runner can use `submission_archaludon/cg/` as the engine/API provider.

## Run Local Games

Run one Archaludon mirror game:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\run_local_battle.py --games 1 --max-steps 1000
```

Run more games:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\run_local_battle.py --games 20 --max-steps 1000
```

Outputs:

- `analysis_outputs/local_battle_summary.jsonl`
- `analysis_outputs/traces/game_XXXX.jsonl`

Each trace records the acting player, selection context, option count, selected action, compact logs, and a small board snapshot.

## Run A Matchup Matrix

After importing multiple public agents:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\run_matchup_matrix.py `
  --agent archaludon=meta_agents\archaludon_public `
  --agent great_tusk=meta_agents\great_tusk_crustle_public `
  --games 4
```

Output:

- `analysis_outputs/matchup_matrix.csv`

Use this for quick screening. It is not a leaderboard replacement; small samples are noisy.

## Analyze Public Episodes

The index dataset is small and can be downloaded without Kaggle API credentials:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\download_episode_samples.py --date latest --count 3 --max-mb 20
```

This writes:

- `data/episodes_index/manifest.csv`
- `data/episodes/YYYY-MM-DD-sample/*.json`

Daily episode datasets are very large, often around 20 GiB, so download samples first.

After downloading public episode JSON files into `data/episodes/`, run:

```powershell
& "C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" tools\summarize_episode_json.py data\episodes
```

Outputs:

- `analysis_outputs/episode_meta/files.csv`
- `analysis_outputs/episode_meta/card_counts.csv`
- `analysis_outputs/episode_meta/attack_counts.csv`

This is a broad first pass. It counts visible card and attack mentions in public replays. Treat the output as a scouting signal, not as exact deck reconstruction.

## Beginner Improvement Loop

Start with a small loop:

1. Pick one candidate deck and agent.
2. Run local mirror games to ensure it does not crash.
3. Run games against one known public baseline.
4. Open traces and find repeated bad choices.
5. Add one narrow rule to `main.py`.
6. Re-run the same tests.
7. Keep the change only if it improves the target matchup without breaking validation.

Good first metrics:

- Validation success: no local exceptions.
- Average steps: very long games can indicate loops or weak closing.
- Prize progress: whether the agent actually takes prizes.
- Important context counts: setup, main choices, targets, attacks.
- Matchup win rate against a fixed baseline.

Avoid changing many rules at once. If two rules change at the same time, you cannot tell which one helped.

## Practical Score Strategy

For this competition, a practical path is:

1. Build or copy several coherent deck archetypes.
2. Make each one validate locally.
3. Run matchup tests against public baselines.
4. Use public episode data to identify common high-rating archetypes.
5. Add matchup-specific rules only for common opponents.
6. Submit only after local self-play and baseline tests pass.

Rule-based agents can be strong because the simulator exposes legal options. You do not need to generate every legal move yourself; you need to rank the options well.

Machine learning can help later, but it is not the first bottleneck. The first bottleneck is usually:

- choosing a strong deck,
- avoiding invalid or low-value actions,
- handling prize cards and hidden information,
- recognizing common opposing archetypes,
- and not timing out or looping.

## Download Limits

Competition Data files such as `ptcg_engine.zip` require Kaggle competition authentication.
This machine currently does not have `C:\Users\amuam\.kaggle\kaggle.json`, so CLI download of competition Data is not available yet.

Public Dataset files, such as the daily episode index and sampled replay JSON files, can be downloaded through Kaggle's public dataset API.

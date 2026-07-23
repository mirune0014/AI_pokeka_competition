# Kaggle public content ideas - 2026-07-04

## Already covered in current discussions

- Game engine source code: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/717141
- Daily top episodes datasets: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/709160
- Simulator / official rules differences: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/708586
- Leaderboard rating variance: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/712621
- Reproducible evaluation loop request: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/715251
- Public visible meta notes: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/709263
- Ogerpon anti-Archaludon deck discussion: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/716207

## Best next Discussion candidate

Title:

Replay triage template: turning public episodes into actionable loss buckets

Why this is worth posting:

- It is useful to other participants without publishing a decklist or exact agent rules.
- It complements existing rating-variance threads instead of repeating them.
- It can later be paired with a public notebook, which may help with Notebook medal visibility.
- It is beginner-friendly and frames analysis as a process, not a secret strategy.

Draft:

```markdown
I found that live score alone is a noisy signal for deciding whether an agent update is actually better, so I started treating public replays as qualitative debugging data rather than as a direct leaderboard proxy.

This is a small workflow that has been useful for me. It uses only publicly visible game history / replay information and avoids sharing full decklists or private agent code.

### 1. Let a submission collect enough games

If a submission is not obviously broken, I try not to replace it immediately after only a few games. A short run can be dominated by opening hands, seat order, matchup luck, and early matchmaking. Waiting longer makes the replay set more useful.

### 2. Classify losses before changing rules

For each public loss, I record a small row like this:

| field | example |
| --- | --- |
| episode_id | public replay id |
| opponent_bucket | broad archetype, not exact private code |
| seat | first / second |
| first_real_attacker_turn | when the first meaningful attacker started attacking |
| final_board | active + bench count at the end |
| loss_shape | setup miss / no second attacker / bench snipe / prize race / deck-out risk / other |
| likely_actionable | yes / no / unclear |

The key point is that one replay is often not enough. A single loss can be bad luck, but repeated losses with the same shape are much more useful.

### 3. Reproduce the bucket locally

After I see a repeated loss shape, I test a narrow candidate change against local public-agent approximations with fixed seeds. I prefer matched-seed A/B checks over comparing two unrelated random batches.

For example, I ask:

- Did the candidate improve the specific bucket it was designed for?
- Did it make a different important bucket worse?
- Is the improvement still visible when I rerun with a different seed range?

### 4. Keep the label simple

I found that simple labels are more useful than over-detailed replay notes. The labels I currently like are:

- setup miss
- tempo loss
- no backup attacker
- bench-snipe collapse
- wrong target priority
- resource exhaustion
- deck-out / low-deck risk
- probably variance

This helped me avoid changing rules after every individual loss. It also made it easier to decide when a change was too matchup-specific.

I am curious if others have better loss labels or replay triage templates. In particular, I would be interested in ways to summarize public replays without leaking exact private strategies.
```

## Notebook candidate

Notebook title:

PTCG replay triage starter: public episodes to loss buckets

Notebook shape:

1. Load public episode JSON files from the Kaggle daily episode dataset or uploaded replay files.
2. Extract episode id, rewards, public team names, final active / bench summaries, visible attack ids, and visible card ids.
3. Map visible card ids to broad archetype buckets.
4. Produce CSV tables:
   - episode summary
   - loss bucket summary
   - opponent archetype summary
   - attack usage summary
5. Keep all exact strategy notes manual and private.

Safe content boundary:

- OK: code for parsing public replay JSON and producing generic labels.
- OK: broad archetype labels and aggregate counts.
- Avoid: publishing current private decklists, exact rule weights, hidden API assumptions, or opponent-specific targeting rules.


# GPT PRO brief: Archaludon submitted histories

Collection stopped at the user's request after the current partial set was preserved.

- Selected by API metadata: **52** Archaludon-labelled submissions (plus historical `rule3v3` and the ambiguous `submission.tar.gz`).
- Fully processed before stop: **28** submissions.
- Unprocessed submission IDs: `54349636, 54448251, 54470098, 54485645, 54490333, 54491496, 54493893, 54495224, 54510332, 54526221, 54526456, 54526632, 54561161, 54561652, 54570077, 54570845, 54599496, 54600598, 54601378, 54606641, 54606772, 54697107, 54704652, 54707683`.
- Episode rows listed for processed submissions: **1585**; unique episode IDs: **1585**.
- Full replay JSONs downloaded: **1541**; total raw size: **5,024,048,193 bytes**.
- Listed episodes without a downloaded replay: **44**.

The complete raw set is under `replays/`. Per-submission raw `ListEpisodes` JSONs are under `submissions/`. The authoritative index and hashes are in `COLLECTION_MANIFEST.json` and `submission_overview.csv`.

## Interpretation guard

Do not treat an old high public score as proof that its policy is stronger: older submissions faced a different opponent pool, different time, and different sample size; some were exploratory or RL-labelled. Separate deck identity, opponent distribution, validation/public variance, and actual policy changes. The currently accepted Lillie safety fix is a rare safety repair, not evidence of a global win-rate gain.

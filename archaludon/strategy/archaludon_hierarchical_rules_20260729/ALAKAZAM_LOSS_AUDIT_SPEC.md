# Immutable qualitative audit specification: Alakazam loss bucket

- Submission: exact historical-Silver Archaludon `54927163`.
- Policy SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Episode CSV SHA-256:
  `A94A0754A9D2F84B88DB7D64BC126D4E8FA2855CC0769E799A031F6D4702F64E`.
- Extracted deck manifest SHA-256:
  `F347CB1D5B3DB5FB1D4D1CE2098C3C53CBED98A542A1AA015FE894E22445F1F8`.
- Bucket: the latest 24 public losses whose opponent deck was extracted as
  `alakazam_psychic`.
- Episode IDs, newest first:
  `88614404,88602602,88479736,88457867,88454146,88417236,88399026,88385224,88323824,88244115,88242194,88232035,88191793,88171291,88163977,88096405,88096059,87996118,87994013,87974582,87935410,87911107,87892692,87842092`.

Read the raw replay for every listed episode and the exact baseline source.
Diagnose only public-state strategic mistakes relevant to the agreed hierarchy:
terminal win/loss gates, harmful KO avoidance, prize route, non-KO/Active
constraint, Bench damage, one-to-two-turn visible threat reachability, known
access, probability from card counts, win/normal/comeback mode, winning outs,
and turn-plan commitment.

Do not imitate the opponent policy, infer hidden hands from Gold actions, write
source, or propose episode-specific rules. Identify exact reproducible states
and one or more narrow general certificates. Distinguish a rule that could
have changed a loss from an unrelated deck or variance loss. Write a compact
report under this strategy directory and return its path and SHA-256.


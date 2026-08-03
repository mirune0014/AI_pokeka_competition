# Immutable qualitative audit specification: adjacent matchup loss bucket

- Submission: exact historical-Silver Archaludon `54927163`.
- Policy SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Episode CSV SHA-256:
  `A94A0754A9D2F84B88DB7D64BC126D4E8FA2855CC0769E799A031F6D4702F64E`.
- Extracted deck manifest SHA-256:
  `F347CB1D5B3DB5FB1D4D1CE2098C3C53CBED98A542A1AA015FE894E22445F1F8`.
- Bucket: the latest 24 public losses among `marnie_grimmsnarl`,
  `mega_lucario`, and `archaludon_metal`.
- Episode IDs and extracted opponent archetypes, newest first:
  - `88660007` archaludon_metal
  - `88655752` archaludon_metal
  - `88643491` mega_lucario
  - `88584180` marnie_grimmsnarl
  - `88563380` marnie_grimmsnarl
  - `88509934` archaludon_metal
  - `88507294` archaludon_metal
  - `88411737` mega_lucario
  - `88391698` mega_lucario
  - `88389000` marnie_grimmsnarl
  - `88367994` marnie_grimmsnarl
  - `88356203` mega_lucario
  - `88338429` mega_lucario
  - `88272191` marnie_grimmsnarl
  - `88247531` marnie_grimmsnarl
  - `88225916` marnie_grimmsnarl
  - `88197270` marnie_grimmsnarl
  - `88134743` archaludon_metal
  - `88017509` mega_lucario
  - `87868636` marnie_grimmsnarl
  - `87825800` mega_lucario
  - `87709435` marnie_grimmsnarl
  - `87701753` marnie_grimmsnarl
  - `87690776` mega_lucario

Read every raw replay and the exact baseline source. Diagnose public-state
strategic mistakes relevant to the agreed hierarchy, with special attention
to current/next attacker continuity, harmful KO, visible one-to-two-turn
threat completion, prize exchange, Bench versus Active pressure, comeback
outs and turn-plan commitment.

Do not imitate opponent actions, use hidden-hand reconstruction, write source,
or propose opponent/episode-specific patches. Record exact reproducible states,
narrow general certificates, and whether each observed loss is plausibly
mechanism-addressable or unrelated. Write a compact report under this strategy
directory and return its path and SHA-256.

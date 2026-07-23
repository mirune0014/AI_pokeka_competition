# Root-verified current-39 evidence amendment

This evidence does not broaden the frozen rule. It adds a later live H0 state
that satisfies the already frozen initiation certificate.

At the 39-public checkpoint, new episode `87374791` is a target loss. The
submitted child and its direct integrated parent are action-identical on all
58 correct-seat callbacks, so the loss is not caused by the admissibility
repair.

Root directly checked semantic seat 1, public S109:

- ordinary MAIN, turn 9, `energyAttached=False`, visible hand exactly 9/9;
- Active Kadabra `742/s69`, no Energy;
- visible hand Energy: Basic Psychic `5/s116`, Basic Psychic `5/s117`, and
  Enriching `13/s122`;
- opposing Active Alakazam `743/s25`, 140 HP;
- recorded parent action option 16: Enriching `s122` to Bench Dudunsparce;
- frozen deterministic alternative option 10: lower-serial Basic Psychic
  `s116` to Active Kadabra, followed by Super Psy Bolt `1071` for a strictly
  positive 30-damage public outcome;
- at S117 the submitted policy reaches END with the Kadabra still unenergized.

The same replay also supplies parent-identical retention states:

- S57: Telepath Psychic to Kadabra; S58: Super Psy Bolt `1071`;
- S76: Telepath Psychic to Alakazam; S77: Powerful Hand `1072`.

Therefore the current-39 shadow must classify S109 as an H0 readiness commit
and reproduce both earlier attach-then-attack routes action-identically.
Whether the 30 damage changes the final result is unknown and is intentionally
left to the live probe; the evidence certifies resource conversion, not a
counterfactual win.

Evidence files:

- episode CSV SHA-256:
  `913A5D6962A6900C9BD4FE95F0B83C2C9A850E1D49FC275929A2B362EE5DD47B`;
- submitted-child raw SHA-256:
  `04621BE9865F97C1A6030CFB5955A12C38E3D1C963A1BE52404929660CE885F7`;
- direct-parent comparison SHA-256:
  `5E4B7F59B06453A54DA941B7FDAAEE0D46395C666A77D16CC79EEF3A5729400C`.

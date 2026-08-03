# Future loss memo — Explorer keep should preserve certified evolution access

Status: deferred; do not mix into the active search-aware or cumulative build.

## Evidence

- Live submission:
  `55083165`
- Episode:
  `88831792`
- Correct seat:
  `0`
- Replay SHA-256:
  `156C3351A85822D6F9997DDFEDA27AEBD8C731526993B6507E934C7775CB544E`
- Bounded analysis:
  `autonomous_gold_20260715/live/55083165/refresh_20260730_0211/ANALYSIS_88831792.md`
- Analysis SHA-256:
  `4C0B98E007F0933C80CE8FC6397AF8F3BDCAE1D9D9BA8FC8EB6F031915C3CC5B`
- Exact Hero-versus-Historical-Silver shadow:
  `28` correct-seat callbacks, `0` semantic differences, `0` invalid actions,
  `0` exceptions, and `0` Hero starts.

The loss is inherited from exact Historical-Silver. It is not attributable to
Hero's Cape or to the active search-aware terminal rule.

## Public-state hypothesis

At replay step 14, Explorer's Guidance forced a second keep after Duraludon.
Full Metal Lab, Pokegear, Poke Pad, Metal, and Ultra Ball all scored zero, so
option order kept the Stadium and discarded Ultra Ball. The Stadium was
replaced before the first damaging Shadow Bullet; the backup Duraludon
remained unevolved and unenergized, while all three manual Metal went to the
Active and were lost with it.

Narrow future rule to test:

> In the exact Explorer keep-two class, after a required Duraludon keep,
> prefer a uniquely legal Ultra Ball over a zero-score Stadium only when
> count-only Archaludon-ex access, next-turn evolution timing, and safe
> Ultra Ball payment are all certified.

## Required proof before implementation

- Reproduce step 14 from public state without opponent-hand inference.
- Prove a legal safe Ultra Ball payment and count-only evolution access.
- Run both seats, reordered/duplicated options, serial remaps, search miss,
  turn/reset, and collision tests.
- Compare against H3 v2 and the cumulative proposal resolver; unknown
  interaction fails closed to exact Historical-Silver.
- Treat causal conversion confidence as low until an exact-engine branch
  demonstrates improved board formation and attack continuity.


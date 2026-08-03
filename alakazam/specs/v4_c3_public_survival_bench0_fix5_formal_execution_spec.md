# v4 C3 公開最大打点・ベンチ0回避 fix5 正式評価仕様

日付: 2026-07-30

## 目的

C2の行動不変な次アタッカー距離解析を親として、公開情報から証明できる
最大打点により盤面全滅が起きる局面だけ、親の `ATTACK` / `END` の直前に
低コストBasicを1体出すC3候補を評価する。

勝敗はchecked paired runnerだけを根拠とする。metric suiteは行動・機構・
transaction・到達の検査専用であり、勝敗集計には使わない。

## 凍結入力

Baseline:

```text
alakazam_staged_20260729/eval_adapters/
  alakazam_newdeck_v3_exact_evolution_ko_fix2
```

- source closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- adapter main:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

Candidate:

```text
alakazam_staged_20260729/versions/
  alakazam_newdeck_v4_public_survival_bench0_fix5
alakazam_staged_20260729/eval_adapters/
  alakazam_newdeck_v4_public_survival_bench0_fix5
```

- parent closure:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- candidate closure:
  `5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134`
- `main.py`:
  `F10CD675F0FCF9DA89E2D80D26CA330B521E934685F492C69085457CD75CFB44`
- `planner_public_damage_continuity.py`:
  `AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201`
- `planner_public_survival_bench0.py`:
  `C9E86FFDBD054476E562313808DD08E35E05176F30BE083E1862A370229E3AEC`
- sidecar collector:
  `B156A3D321E1AF1F24A330EA69CC26D7D4A8D02105DA162604BDF6C72A3AC07F`
- adapter main:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

共通deckは60行で、SHA-256は次とする。

```text
F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94
```

正式実行後に上記production fileを変更しない。変更が必要なら既存出力を
混ぜず、新しいclosureとfresh outputで最初から実行する。

## 支配仕様

- umbrella contract:
  `B0657D0118847F2DDF7680E6D75AE28F2DF6CF42EE338B6355ADDC731F454783`
- C3 immutable behavior:
  `1585C9FC7BEB326E2F496AC8B35D99E5B75A976F0F69C7A8B7492671E7B73B5F`
- C2-C5 binding:
  `C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`
- Power Pro stacking amendment:
  `7C48B4D830D009BE9128DDA137FBAA25B2F5CDCE2022BB163ACA6F94E9979344`
- implementation receipt:
  `6174B2942F2BECAA6BF20A409155784F63BFCB3BFB1BCECF514BC5F367EF1EE0`

## checked runtime

- Python: `.venv-rl/Scripts/python.exe`
- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- paired runner:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- battle runner:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- combiner:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- metric runner:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- metric wrapper:
  `78A0BE6E87368939D7FCE590E1AA65B5DFFA228DE224FFB53AA42C8DE1EF295B`

## 固定対面

```text
marnie
  meta_agents/marnie_sota_live_85033057_simple
cynthia
  meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle
alakazam_mirror
  meta_agents/alakazam_oselcoun_live_85035844_simple
rocket_mewtwo_spidops_proxy
  meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple
kangaskhan_crustle
  meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline
historical_silver
  analysis_outputs/reference_agents/historical_silver_archaludon_54495224
direct_frozen
  alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
```

## paired 700局

- seed base:
  `202608500, 202608510, 202608520, 202608530, 202608540`
- policy seat: `0, 1`
- games per seat per panel: `10`
- actual seed: `seed_base + game_index`
- max steps: `1000`
- panel数: `35`
- baseline rows: `700`
- candidate rows: `700`

Fresh panel output:

```text
alakazam_staged_20260729/evaluations/
  v4_c3_public_survival_bench0_fix5_panels/
    <seed_base>_<opponent>/attempt_1/
```

Fresh combined output:

```text
alakazam_staged_20260729/evaluations/
  v4_c3_public_survival_bench0_fix5_combined_attempt1
```

### 非重複実行割当

Shard A:

```text
202608500: all 7 opponents
202608530: marnie, cynthia, alakazam_mirror,
           rocket_mewtwo_spidops_proxy, kangaskhan_crustle
```

Shard B:

```text
202608510: all 7 opponents
202608530: historical_silver, direct_frozen
202608540: marnie, cynthia, alakazam_mirror
```

Shard C:

```text
202608520: all 7 opponents
202608540: rocket_mewtwo_spidops_proxy, kangaskhan_crustle,
           historical_silver, direct_frozen
```

各runnerはcommand、exit code、raw output pathだけを返し、勝率・差・採否を
解釈しない。

## C3 metric trace

Candidateだけを、pairedと同じ5 seed base・両seat・10 gamesで実行する。

```text
Shard A: marnie, cynthia, alakazam_mirror
  output: metrics/formal_v4_c3_public_survival_bench0_fix5_trace_a
Shard B: rocket_mewtwo_spidops_proxy, kangaskhan_crustle
  output: metrics/formal_v4_c3_public_survival_bench0_fix5_trace_b
Shard C: historical_silver, direct_frozen
  output: metrics/formal_v4_c3_public_survival_bench0_fix5_trace_c
```

合計は70 block、700 gameとする。

## Mega Lucario補助到達パネル

Power Pro stackとFighting familyの到達確認だけに使い、固定700局の勝敗には
混ぜない。

```text
mega_lucario_aib4
  meta_agents/mega_lucario_aib4_live_84983544_simple
  deck: 2A541D7BF3D9E6B36037123F53F4DFEF6348223F79FD27095DAFC602A5357C19
mega_lucario_fujiborozoukin
  meta_agents/mega_lucario_fujiborozoukin_live_85033862_simple
  deck: D6B1417B848C75991BCF1EA5FE96E65A2B8A56FEC27DCD95DDC51005A6C1E90E
```

- seed base:
  `202609500, 202609510, 202609520, 202609530, 202609540`
- both seats
- 10 games per block
- max steps: `1000`
- expected: 20 blocks / 200 games
- fresh output:
  `metrics/formal_v4_c3_public_survival_bench0_fix5_megalucario_reach1`

## raw完全性

rootとSol-Ultra numerical evaluatorが別々に次を検査する。

- 35 paired panel、各first-valid attempt 1個
- baseline/candidate各700 unique
  `(opponent, policy_seat, seed)` keys
- baseline/candidateのschedule完全一致
- nonzero exit、timeout、unstarted、action error、max-step、
  invalid result、missing、duplicateがすべて0
- raw panelとcombinedの差0
- metric 90 blocks / 900 games、全block complete
- sidecar `CALL_START == CALL_END`
- closure・rule・decision linkage一致
- unsupported action change、transaction fault、stale abort、
  metric exception、wrapper exception、structural invalidがすべて0

## 機構到達条件

- supported threat state 30 unique states以上
- promotion/removal context 10件以上
- continuity:
  `REPEATABLE_READY`, `RECHARGE_REQUIRED`, `NO_READY_ATTACK`, `UNKNOWN`
  の4classすべて
- 両seat
- 3 opponents以上、非mirror 2以上
- `FLOOR_BOARDOUT_AVOIDANCE` と
  `CAP_LOW_COST_BOARDOUT_AVOIDANCE` の両方

到達不足は `INSUFFICIENT_EVIDENCE` とし、推定で補わない。

## 数値採用条件

すべて必要。

- candidate wins `>= 452/700`
- overall paired deltaが正
- Historical Silver `>= +3/100`
- Historical Silver両seatが非負
- Historical Silverの20-game seed block 5個中2個以上が正
- adjacent 6 opponents合計 `>= -2/600`
- 各opponent `>= -2/100`
- 各opponent-seat `>= -2/50`
- one-sided 95% paired lower bound:
  - overall / adjacent `>= -1pp`
  - Historical Silver `>= -3pp`
- 機構到達条件
- raw完全性

C3行動変更が不採用でも、pure damage/continuity analyzerは、
unsupported action change 0、raw完全性、静的監査を通った場合に限り、
C4 shadowへ解析部品として渡してよい。

# v4 B0 fix2 絶対基準 root 検証

## 結論

候補結果を参照する前に、`v3_exact_evolution_ko_fix2` の固定700局を完走し、root が raw summary から独立再集計した。

```text
ABS_FLOOR = 452 wins / 700 games
losses    = 248
```

以後の行動変更候補は、少なくとも452勝を維持し、かつ固定された追加採用条件をすべて満たさなければならない。

## 固定対象

- version:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- policy closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- execution spec:
  `E9297C2FAAF5A630ED65F07ED3A06B62B29AC022DE5D3A30FA9AF4320CAB7678`
- checked engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`

## 実行物

- output:
  `alakazam_staged_20260729/metrics/formal_v4_b0_fix2_7opp_50seed`
- suite manifest:
  `CC1AB21DA182DB16DB5CF2150C6EBA3B79468CE7C95B72C633DF6FE3ED441260`
- block ledger:
  `478FAE57A3A6705828D69D7ACBD6A07423FC5D787DE654D4F8347657D08B0128`
- execution summary:
  `1CBBF58C5A9EBCCB255F55DA3C8D96F9227078E06DEFD4F18C637BA089CB75C4`
- 70 summary file tree:
  `B8BD3D84281FEB50499BDE3BF2890AEFDA62EC00C794433460DECD77C638B138`

summary tree hash は、output rootからの相対pathで昇順に並べた次のUTF-8レコード列のSHA-256である。

```text
<summary file sha256><two spaces><relative path>\n
```

## root 再集計

| opponent | games | wins | losses |
|---|---:|---:|---:|
| alakazam_mirror | 100 | 81 | 19 |
| cynthia | 100 | 73 | 27 |
| direct_frozen | 100 | 64 | 36 |
| historical_silver | 100 | 56 | 44 |
| kangaskhan_crustle | 100 | 71 | 29 |
| marnie | 100 | 69 | 31 |
| rocket_mewtwo_spidops_proxy | 100 | 38 | 62 |
| **total** | **700** | **452** | **248** |

| policy seat | games | wins | losses |
|---|---:|---:|---:|
| 0 / agent A | 350 | 235 | 115 |
| 1 / agent B | 350 | 217 | 133 |

| seed base | games | wins | losses |
|---|---:|---:|---:|
| 202608500 | 140 | 96 | 44 |
| 202608510 | 140 | 81 | 59 |
| 202608520 | 140 | 94 | 46 |
| 202608530 | 140 | 90 | 50 |
| 202608540 | 140 | 91 | 49 |

policy win は、ledgerで policy が agent A にある `seat=0` では `result==0`、agent B にある `seat=1` では `result==1` として再計算した。

summary の `your_index` はゲーム終了直前に記録された callback のプレイヤーを表す場合があり、固定 policy seat の証明には使用していない。policy seat は70件すべての実行commandにおける `--agent-a` / `--agent-b` の位置から検証した。

## 完全性

- summary files: 70
- raw rows: 700
- unique `(opponent, seat, seed)`: 700
- 70 cells × 10 games
- 各cellのgame index: `0..9`
- `seed == seed_base + game`: 全700件
- JSON parse error: 0
- duplicate key: 0
- missing row: 0
- unstarted: 0
- action error rows: 0
- action error total: 0
- max-step hits: 0
- invalid winner: 0
- ledger rows: 70
- nonzero exits: 0
- timeout: 0
- partial block: 0
- command/schema mismatch: 0

70件すべてで `.venv-rl`、checked battle runner、`--engine-seed`、10 games、`max_steps=1000`、固定したagent位置を確認した。

## 凍結

この文書の作成時点で C1 の固定700局候補結果は未実行・未参照である。

`ABS_FLOOR=452` は、採用済みのより強い候補が現れるまで変更しない。

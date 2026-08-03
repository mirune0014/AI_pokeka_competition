# v4 ポフィン対面差・ベンチ0敗因解析契約

日付: 2026-07-31

## 目的

次の二点を、固定済みrawから分離して検証する。

1. ポフィンの役割・選択枚数変更が、マーニー／シロナで改善し、
   ロケット団／Historical Silverで悪化した差が、再現性のある機構か偶然か。
2. C3正式900試合のうち、ベンチ0が実際の敗因となり、公開最大打点・
   ベンチ0回避を発火させるべきだった自然局面がどれか。

この段階では方策を変更しない。リプレイは行動ラベルではなく、盤面・資源・
Prize交換・攻撃継続の診断証拠として使う。

## C1固定入力

Paired CSV:

`alakazam_staged_20260729/evaluations/v4_c1_poffin_fix3_combined_attempt2/combined_paired_results.csv`

SHA-256:

`BAFA80721A1095E3033B8AA82D344936A5438243EB98698838175B4EFCAF6394`

Combined manifest:

`alakazam_staged_20260729/evaluations/v4_c1_poffin_fix3_combined_attempt2/combined_manifest.jsonl`

SHA-256:

`DC62231788A9308087D6A40401BF063BD6E6FC58C413052516D5786583D8AA60`

Expected schedule:

- 700 unique `(opponent, seat, seed_base, game, seed)`
- 7 opponents
- both seats
- seed bases:
  `202608500, 202608510, 202608520, 202608530, 202608540`
- 10 games per opponent／seat／seed base
- baseline A/B duplicate mismatch 0

Baseline:

- `versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`

Candidate:

- `versions/alakazam_newdeck_v4_poffin_role_cardinality_fix3`
- closure:
  `DE7FCD20A1B3362E845B8573DC6178E32B13F250EA8AC8619B7BA0AA704D271D`

Checked engine:

- `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- tree hash:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`

## C3固定入力

C3 callback rows:

`alakazam_staged_20260729/metrics/formal_v4_c3_public_survival_bench0_fix5_union_audit/c3_callback_audit_rows.jsonl`

SHA-256:

`D191973FD7967F1E48E2773C8BC51FE1834E0D51122247E9C88F4619784933BE`

C3 summary:

`alakazam_staged_20260729/metrics/formal_v4_c3_public_survival_bench0_fix5_union_audit/c3_mechanical_summary.json`

SHA-256:

`95155FE090A6CFCF8A5DD3FBA79505E10A368BD051F8A02AC3B3B2D191C15E97`

Raw input manifest:

`3FB626031AF16A0F61098DAFC38A7554AEBE9F7C69DC0F0E223DA6F57A3B02E6`

Expected raw:

- 4 accepted suite roots
- 900 sidecars
- 111,028 JSONL rows
- 55,514 exactly paired live callbacks

Existing independent reach audit:

- script:
  `analysis_outputs/v4_c3_bench0_reach_audit_20260731/audit_c3_bench0_reach.js`
- script SHA-256:
  `257484F14DFB443664F42CDDC354703732C932BA712D6D77225D8AB6E47D9705`
- result:
  `analysis_outputs/v4_c3_bench0_reach_audit_20260731/audit_results.json`
- result SHA-256:
  `5D7305310ED1DD3A4E0C7D089970C0E0D585D085BE448CBBEEB76D72692AAC2A`

## 数値解析

### ポフィン

raw 700行から次を独立再計算する。

- opponent／seat／seed base別のbaseline win、candidate win、gain、loss、tie
- discordant pair数とexact paired binomial検定
- seed-baseをclusterとする差分分布
- leave-one-seed-base-outの差と符号
- 改善・悪化が特定seatまたは1 seed blockだけに依存するか
- Marnie＋Cynthia、Rocket＋Silverを事後的に結合した値は、
  探索的集計として明示し、事前仮説の検定として扱わない

「再現性あり」は、最低でも複数seed block、両seat、複数の独立リプレイで
同じ公開盤面機構が反復することを要求する。単一の100局差やp値だけで
メタルールを採用しない。

### ベンチ0

C3の900試合から、次の漏斗をrawで再構成する。

- Activeあり・Bench 0・通常MAIN
- 合法Basic PLAYあり
- C3独立価値Basicあり
- 公開damage cap／floorでActiveがKOされ得る
- 親actionがATTACK／END、または別transactionにより上書き
- その後、Benchを作る前にActiveが倒れる
- board-outまたは攻撃継続喪失
- 最終的にpolicyが敗北

敗戦候補は次に分類する。

- `STRONG_BENCH0_CAUSAL`:
  合法Basicを出せ、現在の確定KOを失わず、Active喪失が直接board-out敗北。
- `PLAUSIBLE_BENCH0_CONTRIBUTOR`:
  board-outではないが、唯一の後続・攻撃継続を失い、その後回復できない。
- `BENCH0_NOT_CAUSAL`:
  Basicを出せない、出すと確定KO／終局を失う、相手に別の確定勝ち筋がある、
  または後に安全にBenchを作っている。
- `UNKNOWN`:
  公開情報だけで反実仮想を確定できない。

hidden hand、deck順、prize内容を反実仮想の確定証拠に使わない。

## リプレイ診断

ポフィンは、改善側と悪化側を別々に読む。

- 改善側:
  Marnie、Cynthiaのgain／loss両方
- 悪化側:
  Rocket、Historical Silverのgain／loss両方

各リプレイで次を記録する。

- 最初の親／候補action差
- ポフィン使用有無と0／1／2枚選択
- 選択したAbra／Dunsparceの役割
- 1、2ターン後のAbra系統数、Dunsparce系統数、Bench枠
- 最初の攻撃ターンと手札枚数
- Powerful Hand打点差
- 次アタッカー距離
- 相手のgust、bench pressure、spread、Prize速度
- 勝敗を変えた機構か、単なる後続乱数差か

## メタルール候補の制約

対面名またはagent名を直接参照しない。

メタルールにする場合は、公開盤面から判定できる次のような特徴へ落とす。

- 相手の初動Prize速度
- benchへの圧力、gust、spread
- 自分の手札打点20点損失の許容幅
- Abraの1本目／2本目の必要性
- Dunsparceを壁・draw engineとして使える期限
- 空きBench枠
- 次アタッカー距離

対面固有分岐が必要な場合も、公開されたデッキカードまたは場のカードから
アーキタイプを裏付け、誤分類時は親行動へ戻す。

## 出力

解析成果物は次へ新規保存する。

`analysis_outputs/v4_poffin_bench0_causal_analysis_20260731`

最低限:

- `poffin_numeric_audit.json`
- `poffin_discordant_pairs.csv`
- `bench0_loss_candidates.csv`
- `BENCH0_AND_POFFIN_ANALYSIS.md`

raw、source、deck、既存scheduleは変更しない。

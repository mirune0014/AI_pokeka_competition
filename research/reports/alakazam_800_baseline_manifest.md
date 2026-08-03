# フーディン既存版の凍結マニフェスト

## 結論

`alakazam_800_frozen` は、Kaggle submission `54906455` の提出アーカイブと、同じ内容を保持するリポジトリ内ソースをハッシュで固定した版である。

本資料ではユーザー指定に合わせて「既存800版」と呼ぶが、保存済みKaggle API行で確認できる提出直後のpublic scoreは、1公開試合後の`509.6`である。

後日の`800`相当の得点を裏付けるKaggle APIスナップショットは、現在のリポジトリ内にはない。

この呼称差は、提出物の同一性や以後のローカル比較には影響しない。

## 提出物の同一性

| 項目 | 固定値 |
| --- | --- |
| submission ID | `54906455` |
| submission名 | `Active Dudunsparce Run Away KO v4` |
| Kaggle説明 | `Alakazam Active Dudunsparce Run Away KO v4; fail-closed no-effect envelope` |
| 提出日時 | `2026-07-23 00:23:38.830 JST` |
| normalized deck hash | `f2e179fb82cb91504ccd207d707ca5e7be8afc7228df26a7b287c6205064507c` |
| raw `deck.csv` SHA-256 | `A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529` |
| 提出アーカイブ | `submission_alakazam_active_dudunsparce_run_away_ko_transaction_v4_20260722.tar.gz` |
| アーカイブサイズ | `2,080,300 bytes` |
| アーカイブ SHA-256 | `D1A7DF3B39F6E4CDA9FBB312863867CCD15E73F8040C40F0D1384BC2F1FF7194` |
| package manifest SHA-256 | `24C1E8995FA0C7A64A8FEBFBEA9E422D8ACBFD5A8454A6D5F559881521978C57` |
| module-set SHA-256 | `8F4A643A59C005219063E4FD0CEA5564B99C6BCBD965DC1E899CFE9AE73CD540` |
| package verification SHA-256 | `D4A5EF9E861891D160B6EAB617258B4DE04425005DD8EDD42983FF1ED651B99E` |

凍結コピーは`alakazam_staged_20260729/versions/alakazam_800_frozen`に保存した。

凍結コピー内の32ソースファイルを提出時ソースのリポジトリ内コピーと再帰的に比較し、相対パスとSHA-256の差分が0件であることを確認した。

提出アーカイブ、package manifest、package build scriptも、凍結コピー内の`frozen_submission`へ複製した。

## Git証跡

提出時ソースの現在のリポジトリ内コピーを含むcommitは、`54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`である。

このcommitの元ブランチは`main`であり、段階的開発用ブランチは`codex/alakazam-staged-development`である。

対象ソースに対する`git diff --quiet HEAD -- <candidate>`は終了コード`0`であり、対象32ファイルは当該commitに対してcleanである。

ただし、Kaggleへの提出時刻はこのリポジトリの初回commit時刻より前であり、提出記録にもbranchとcommitは保存されていない。

したがって、提出時の一次証跡はアーカイブとソースのSHA-256であり、commitは後から同一内容が格納されたことを示す証跡として扱う。

## ソースとentry point

提出時ソースは`autonomous_gold_20260715/candidates/alakazam_active_dudunsparce_run_away_ko_transaction_v4`である。

Kaggleのentry pointは、提出アーカイブ直下の`main.py`である。

ローカル実行用entry pointは、候補ディレクトリ直下の`runtime/main.py`である。

`runtime/main.py`は候補ディレクトリを`sys.path`とcurrent working directoryへ設定し、候補直下の`main.py`から`agent`を公開する。

候補直下の`main.py`は、import時に整合性修正モジュールを適用した後、`planner_final_policy.agent(_parent, _parent.agent, obs_dict)`を唯一の実行経路として呼ぶ。

主要ファイルのSHA-256は次のとおりである。

| ファイル | SHA-256 |
| --- | --- |
| `main.py` | `93E2567F4352EE4C4FCEEB3D32B954119F3DC4E8F96DF5498317E781C5804086` |
| `runtime/main.py` | `9517A34C3619B935774A01AFD6C71AE033C44857639D8576834539794C9AC3F3` |
| `_cumulative_parent.py` | `65527AEE74AED600B94C4A555BE9464A48E53E118C9FD674DB6403208706325D` |
| `planner_final_policy.py` | `B89DCB6363CBD6ADF094115CF0CF5B93D6B9975A2505E1B976F387AAE8A198CD` |
| `planner_active_dudunsparce_ko.py` | `B70D7374E0D3C4613EBEC3CE0B8EBA931C641CB9423B8140817BCFCB7F996535` |

## 設定

提出アーカイブは42 member、41 file、30 local module closureで構成される。

抽出後に読み込まれるlocal moduleは29件であり、最後に公開されるcallableは`agent`である。

`requirements.txt`は第三者Python packageを要求しない。

提出物にはWindows、Linux x86-64、Linux arm64、macOS向けの`cg`実行ライブラリが同梱される。

提出時のpackaging smokeは両seatで終了コード`0`、action error `0`、max-step hit `0`であった。

## ローカル再現コマンド

保存済み提出時smokeの再現形は次のとおりである。

```powershell
py -3.11 tools\run_local_battle.py `
  --engine-dir analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine `
  --agent-a autonomous_gold_20260715\candidates\alakazam_active_dudunsparce_run_away_ko_transaction_v4\runtime `
  --agent-b autonomous_gold_20260715\baseline\historical_silver_archaludon_54495224 `
  --deck-a autonomous_gold_20260715\candidates\alakazam_active_dudunsparce_run_away_ko_transaction_v4\deck.csv `
  --deck-b autonomous_gold_20260715\baseline\historical_silver_archaludon_54495224\deck.csv `
  --games 1 `
  --max-steps 1000 `
  --trace-options `
  --seed-base 2026072201 `
  --engine-seed `
  --trace-dir <writable-trace-dir> `
  --summary <writable-summary.jsonl>
```

凍結確認時には、同じengineを用いてMarnie proxyとの1試合をseed `2026072900`で再実行した。

凍結側をseat 0とした試合は113 step、13 turn、result `0`、action error `0`、max-step hit `false`で完了した。

この1試合は再現動作のsmokeであり、強度推定には使用しない。

## 方策の優先構造

最上位の処理順は、placeholder/parity gate、duplicate cache、transaction continuation、既存親方策の1回呼出し、新規candidate arbitration、合法性検査、親actionへのfail-closed fallbackである。

目的関数は、即時勝利、公開情報上の強制敗北回避、現在アタッカーの致死維持、即時Prize、次攻撃維持、次々攻撃経路、短いPrize経路、予約資源、山札安全、Bench liability、安定tie-breakの順で辞書式に比較する。

v4固有ルールは、ダメージを受けたActive DudunsparceがRun Away Drawを使い、3枚のdrawと昇格を厳密に確認してから、1-PrizeのKadabraまたはAlakazamで即時KOするtransactionである。

証明条件が崩れた場合は、既に計算済みの親actionへ戻る。

## 利用上の制約

`alakazam_800_frozen`はsubmission identityと既存実装の不変anchorとして保存し、以後の版からimportして変更してはならない。

絶対強度の主要anchorには、完全実行可能なhistorical Silver Archaludonを用いる。

比較Aは51枚共通・9枠差分に加え、追加カードの合法処理に必要な移植差分も含むため、純粋なデッキ効果とは呼ばない。

提出直後の公開得点は1試合に依存し、ローカル評価は対戦相手agentの実装品質に依存する。

このため、採否は同一seed・同一seatの段階比較と、action error、攻撃継続、初回攻撃、対面別成績を併記して判断する。

# ワークスペース恒久名への移行（2026-08-04）

## 結論

開発開始日を含む一時名称が現行ワークスペース名として残っていたため、用途を
直接表す恒久名へ物理的に変更した。

| 旧名称 | 新名称 | 現在の役割 |
|---|---|---|
| `autonomous_gold_20260715/` | `archaludon/` | Archaludonの現行開発、基準、候補、検証記録 |
| `alakazam_staged_20260729/` | `alakazam/` | Alakazamの現行開発、候補、固定評価資産 |

基準commitは`0f22d49`である。日付は実験や提出の記録名に残し、現行製品・
デッキの入口には使用しない。

## 必要だった修正

- 約68GBのワークスペースをルート直下で物理移動した。
- PythonとPowerShellの実行パスを新名称へ移行した。
- `.gitignore`の生成物隔離規則を新名称へ移行した。
- `.gitattributes`の凍結成果物向け改行保護を新名称へ移行した。
- README、配置ガイド、再現手順、テスト手順、Windows手順を更新した。
- パス移行・残存検査スクリプトを新名称に対応させた。

## 変更しないもの

過去のMarkdown、JSON証拠、凍結仕様に記録された旧パスは、当時の実行環境を
示す証拠なので一括置換しない。旧配置は基準commit`0f22d49`をcheckoutすれば
再現できる。今回の残存検査では、実行コードと現行設定に旧パス参照がないことを
別途確認する。

## 不変性

Historical-Silver本体とデッキは移動だけを行い、内容を変更していない。

- `main.py`: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

現在の入口は次の通り。

- Archaludon: `archaludon/WORKSPACE.md`
- Historical-Silver: `archaludon/baseline/historical_silver_archaludon_54495224/`
- 正式Archaludon: `archaludon/final/archaludon_historical_silver_single_resolver_salvage_v1/`
- Alakazam: `alakazam/README.md`

## 移行後の検証

- 実行コード・現行設定に残る旧ワークスペース参照: 0件
- Python 3.11による追跡対象Python 3,270ファイルの構文エラー: 0件
- Alakazam正式C2系統の対象テスト: 7件＋22件成功
- `research/rl_ptcg/tests`の単体テスト: 729件成功
- `infrastructure/scripts/run_eval.py --help`: 成功
- 旧追跡ファイルと新配置の対応漏れ: 0件

移行処理を再実行した際に、単独のパス要素を見落とす境界条件と、既に移行済みの
親ディレクトリ名を重ねる可能性も発見した。移行スクリプトを修正し、一般変数名を
置換せず、同じ入力へ再適用してもパスを重複させないようにした。

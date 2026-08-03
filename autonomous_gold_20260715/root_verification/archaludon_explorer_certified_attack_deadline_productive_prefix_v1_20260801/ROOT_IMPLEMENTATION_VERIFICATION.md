# Explorer attack deadline conservative release v1 — Root implementation verification

## 結論

候補 `archaludon_explorer_certified_attack_deadline_productive_prefix_v1` は、固定対戦評価へ進める実装ゲートを通過した。

この判定は強度採用ではなく、破壊的な不備がないことと、比較対象を凍結できることの確認である。

## 凍結した入力

- direct behavioral parent: `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- parent SHA-256: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- candidate: `autonomous_gold_20260715/candidates/archaludon_explorer_certified_attack_deadline_productive_prefix_v1/main.py`
- candidate SHA-256: `E19A2CBF2C0F9626D8530263CB13750568F8C7B9739F4A3E9E43B9EDF4B44669`
- deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- primary strategy SHA-256: `71A2CBA1ED1E5048CBC55371A6DEFBF21808E4FED727AACEC304AE1730822822`
- productive-prefix amendment SHA-256: `0A5A78AAC0348376DF48FECA0A599DF367BC17F73325C30008FCC6A72F72425E`
- conservative-release amendment SHA-256: `6D497805F4252F6D69DBD3A975B6DBECD0E9EB1984173CC3E091DFA926419D21`

## Root による構造確認

- candidate `main.py` の先頭 `1,025,951` bytes は direct parent と byte-identical だった。
- candidate runtime は12ファイルだった。
- `main.py` 以外の11ファイルは direct parent と byte-identical だった。
- deck は合法な60枚で、ACE SPECは Hero's Cape 1枚だった。
- direct parent 呼び出しは追加suffix内で1か所だった。
- Kaggle loader が選ぶ最後の callable は candidate の `agent` だった。
- compile、import、deck request、loader-only、loader-last は通過した。
- candidate tree の `__pycache__`、`.pyc`、`.pyo` は0件だった。

Root は worker の validator を再実行し、上記を独立に再確認した。

## Focused fixtures

Root は凍結後の候補に対して focused test を再実行した。

結果は27/27 PASSだった。

対象には、両席のsafe prefix、進化から Assemble Alloy までのcallback、Duraludon配置、手貼り、RETREAT release、5件の未証明Ultra Ball release、2件のsaved-attacker evolve release、owner保持、END/cap、duplicate/reorder、alternative attackの同値・優越・比較不能境界を含む。

## 全履歴 shadow

207 replay files、209 target seats、387 Explorer usagesを二回のfresh processで走査した。

結果は以下のとおりだった。

- intentional terminal first differences: 12
- nonterminal first differences: 0
- deliberate parent releases: 20
- invalid actions: 0
- action errors: 0
- exceptions: 0
- stale: 0
- owner collisions: 0
- owner-preservation failures: 0
- reveal changes: 0
- resource substitutions: 0
- saved-attack losses: 0
- max-step hits: 0
- forced unsafe or unknown attacks: 0

二回の出力hashは一致した。

- `shadow_summary.json`: `6E649A7288FA46477B0D678A27951AC2EB71C5D6C5D76E9F4C43D79FBE09DBC7`
- `shadow_first_differences.csv`: `A4E0E60ED2BDEFF1524DB3E49A49ED0E88880208D5E214135ED3417969D419A6`
- `shadow_inventory.csv`: `37C9081393146C38C60D6D8F70469E958541B92DDF25985D7BC0447332DCBC9E`
- `shadow_source_manifest.json`: `4535EE804527364D1FDF7CF65C8E075961588A3E44753288200CBC42B7C99671`

Root は12件の最初の差分をすべて確認した。

12件はいずれも、親が検索、手貼り、または他のMAIN行動を続けようとした時点で、保存攻撃がその場でゲームを終わらせる局面だった。

過去に問題となった13 RETREAT、5 Ultra Ball、2 saved-attacker evolveの非終局20局面はすべて親と同じ行動へ戻った。

## Checked seeded-engine lifecycle

両席を含む11件のlifecycleを、それぞれfresh child processで二回実行した。

二つのcanonical output SHA-256は一致した。

- first: `85DB1BE50CF79A79D8F02EC796FB00BC81AC95AE88000204878D2697AD503968`
- repeat: `85DB1BE50CF79A79D8F02EC796FB00BC81AC95AE88000204878D2697AD503968`

11件には、safe attach、safe tool、完全なUltra Ball callback、bench evolution、Assemble Alloy、core Duraludon play、終局即攻撃、RETREAT release、saved-attacker evolve releaseを含む。

invalid action、exception、stale、owner collision、actual-state fallback、saved-attack loss、max-step hitは0だった。

## 固定評価へ渡す判定

候補は固定760戦へ進める。

比較baselineは exact direct parent `558EE5DB...22DB6` とする。

historical-Silver Archaludonを主anchor opponentとし、隣接する完全agent群をanti-overfitting populationとして使う。

両席、同一seed、同一scheduleで比較し、結果差分、seat floor、opponent floor、action error、max-step、trace duplicateを確認する。

Kaggle archiveは作成せず、外部提出もしない。

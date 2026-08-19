# メガルカリオexルールベースAgent

このディレクトリには、固定60枚のメガルカリオexデッキ向け決定論的Agentを収録する。
判断には公開盤面、自分の既知情報、合法手、固定カード台帳だけを使い、相手デッキ名やreplay由来の行動ラベルは使わない。

## 実装範囲

- Setup時のActive順位と役割別Bench形成
- Poké Pad、Fighting Gong、Ultra Ballの保証付き検索
- 先攻初手、後攻初手、中盤の手貼り
- Mega Lucario exとHariyamaの進化
- Aura Jab、Mega Brave、Wild Press、Cosmic Beam等の攻撃選択
- Aura JabのEnergy集中、Premium Power Proの最小必要枚数
- Lunar Cycle、Judge、Lillie's Determination
- Boss's Orders、Heave-Ho Catcher、Wally's Compassion
- Switch、Hero's Cape、昇格、retreat fallback
- physical serial単位のResource Ledger、transaction、単一resolver、fault containment
- 公開情報から導くex攻撃無効、one-prize主体、弱点、Bench damage、相手大手札等のflag

## 実行入口

提出時の入口は `main.py` の `agent(observation)` である。
初回呼び出しでは `deck.csv` と同一の固定60枚を返す。

```text
python -m pytest -q mega_lucario_rule_agent/tests
python -m ruff check mega_lucario_rule_agent
```

## 最小確認結果

実装commitは `8c8f43b1478d0d64239ed5190f50a04409dd6f61` である。
446件のテスト、Ruff check、Ruff format check、flat import、60枚deck読込が成功した。
runtime manifest SHA-256は `b629317a8acd2fd08f255918ba1351d3956575e1ef8e29dcf22a392a408fd422` である。

完成後に一度だけ実施した40局の小規模比較では、修正前commit `45af7fc` が0勝で、初動停止が見つかった。
その後、Fighting Gongの検索保証と中盤手貼りのresolver配線を修正した。
同一seedの代表1局では、GongからLunatoneを取得し、engine、Riolu、手貼り、攻撃へ進み、29手の盤面切れから116手・2 Prize取得まで改善した。
この1局は動作確認であり、強さの証明ではない。
ユーザー指示に従い、修正後の広い両席比較は行っていない。

## 関連文書

- `reports/REQUIREMENTS_TRACEABILITY.md`
- `reports/FOCUSED_FIXTURE_REPORT.md`
- `reports/COMPLETE_DECK_SMALL_PANEL_REPORT.md`
- `reports/IMPLEMENTATION_JUDGMENT_JA.md`
- `reports/PACKAGE_MANIFEST.json`

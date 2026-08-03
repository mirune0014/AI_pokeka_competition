# Explorer 攻撃期限の保守的な親解放

## 決定

採用する仮説は `EXPLORER_ATTACK_DEADLINE_CONSERVATIVE_PARENT_RELEASE_V1` である。

この文書は次の二文書を補足する。

- `STRATEGY_SELECTION_EXPLORER_CERTIFIED_ATTACK_DEADLINE_PRODUCTIVE_PREFIX_V1.md`
  - SHA-256: `71A2CBA1ED1E5048CBC55371A6DEFBF21808E4FED727AACEC304AE1730822822`
- `STRATEGY_AMENDMENT_EXPLORER_PRODUCTIVE_EVOLVE_AND_ATTACKER_ATTACH_V1.md`
  - SHA-256: `0A5A78AAC0348376DF48FECA0A599DF367BC17F73325C30008FCC6A72F72425E`

直接の挙動親は引き続き次のファイルに固定する。

- `archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- SHA-256: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`

途中候補 `944D592806C25EF39EAFCECF77D150C1BDFF431D008E712BCB8FE39DEE266861` は、機械的な実装部品としてだけ参照する。
このSHAを最終候補として固定しない。

## 根拠

途中候補を207リプレイ、209対象席、387回のExplorer使用でshadow実行した。

- `shadow_summary.json` SHA-256:
  `67D3787BC74955BA8601ECB8C2724C02001BC3DB25DC877E88FF1AE1D54D6C8C`
- `shadow_first_differences.csv` SHA-256:
  `35079169C63E3382C1BC9B5180AAA257043AFFF0124C060DD47998E0222FDBCE`
- 最初の差: 32件
- 終局即攻撃: 12件
- 非終局の逃げる: 13件
- 事前証明できなかったUltra Ball: 5件
- 保存した攻撃者自身の進化: 2件
- reveal変更、Assemble Alloy資源置換、invalid action、例外、stale、owner collision、saved attack loss: 0件

非終局20件では、「未対応または不明」という理由だけで保存攻撃を強制する優越性がなかった。
Ultra Ball 5件は、親がカード効果を完了した後も同じ確定KOと1 Prizeを取り、控えを形成した。
保存した攻撃者の進化2件は、非exのPrize壁とexの耐久・打点を比較しなければ一律判断できない。
逃げる13件も、少なくとも複数局面で親が同じPrizeを取りながら耐久または次攻撃を改善し、残りもshadowだけでは強制攻撃の優越を証明できなかった。

したがって、「不明なら攻撃」は廃止する。
不明な行動では、既に実行した安全なprefixをactual stateへ残し、Silver親の本物の行動とownerへ解放する。

## hard precedence

### 終局

保存した攻撃が対戦を終わらせる場合は、従来どおり前処理なしで直ちに攻撃する。

### nonterminal deadline

`DEADLINE_READY` で親が提案した行動を次の順で処理する。

1. 証明済みのproductive prefixなら、一つだけ実行し、全callback後に保存攻撃を再証明する。
2. 親が保存攻撃と同じ意味の攻撃を選んだなら、親の攻撃をそのまま返す。
3. 親が別の攻撃を選んだなら、両攻撃を同じ現在observationからexact certificate化する。
4. 保存攻撃が別攻撃を厳密に支配する場合だけ、保存攻撃を強制する。
5. 親がENDを選んだ場合、保存攻撃を再証明して強制する。
6. prefix上限へ達した場合、保存攻撃を再証明して強制する。
7. 逃げる、事前証明できないUltra Ball、保存した攻撃者自身の進化、その他unsafe/unknownでは、deadlineだけをclearして親へ解放する。

## 親へ解放する場合のstateとowner

親へ解放するときは次をすべて守る。

1. deadlineを `RELEASED_TO_PARENT_<CLASS>` としてfinalizeする。
2. wrapperのdeadline、productive、suspended-owner参照だけをclearする。
3. 今回の親呼び出し後の `owner_after`、CUM owner/meta、全親transaction carrierを一切変更しない。
4. 今回親が返したactionをそのまま返す。
5. 既に実行済みのproductive prefixはactual stateへ残す。
6. ownerをrestore、quarantine、clearしない。

allowed productive subtransaction中のcallbackが未証明になった場合も、実行済みカードや盤面を巻き戻さない。
親callbackと親ownerを維持したままdeadlineを解放する。

END、prefix cap、厳密に支配された別攻撃を上書きする場合だけ、今回の未実行親actionが作ったownerをexact `owner_before`へ戻す。
既存ownerは変更しない。

## 別攻撃との厳密比較

固定スコアは使わない。
保存攻撃と親の別攻撃を、同一の現在observationから共通のexact combat certificateで比較する。

保存攻撃が厳密に支配する条件は次のとおり。

- terminal、Prize数、KO、最終ダメージ、永続進捗、永続効果、自傷、捨てるEnergy、交代、加速などの公開結果で非劣化である。
- 少なくとも一項目で厳密に改善する。
- 異なる防御効果、Energy移動、交代、加速などは、effect registryが完全な包含関係を証明できなければ比較不能とする。

判定は次のとおり。

- 同じ意味の攻撃: 親を通す。
- 保存攻撃が厳密支配: 保存攻撃を強制する。
- 親攻撃が厳密支配、同値、比較不能、unknown: deadlineを解放して親を通す。
- 親攻撃が終局勝利: 親を直ちに通す。

## 必須fixtures

### 親へ解放し、非終局差を消す

- Ultra Ball:
  `87653119`, `87750669`, `88385224`, `88555397`, `88565866`
- 保存した攻撃者自身の進化:
  `88443760`, `88681773`
- 逃げる:
  nonterminal 13件すべて
- safe prefixを実行した後に上記行動へ到達した場合も、prefixを保持して親へ解放する。

### 攻撃強制を維持する

- 終局12件は前処理なしで即攻撃する。
- synthetic END。
- synthetic prefix cap。
- 保存攻撃が親の別攻撃をexact certificate上で厳密に支配するfixture。
- Innなどで保存攻撃が劣る場合は強制しない。

### ownerと重複

- 証明不能Ultra Ballが新しい親ownerを作る場合、解放後も同じowner/metaを保持する。
- ENDまたは厳密に支配された別攻撃が今回だけのownerを作る場合、上書き前にexact `owner_before`へ戻す。
- duplicateまたはoption reorderで二重finalize、二重action、二重counterを発生させない。

## telemetry

次を追加する。

- `deadline_release_retreat`
- `deadline_release_ultra_unproved`
- `deadline_release_saved_attacker_evolve`
- `deadline_release_unknown`
- `parent_owner_preserved_on_release`
- `release_after_prefix_count`
- `alternative_attack_same`
- `alternative_attack_saved_dominates`
- `alternative_attack_parent_dominates`
- `alternative_attack_incomparable`
- `alternative_attack_unknown`
- `forced_attack_on_dominated_attack`

自然shadowでは、`forced_attack_on_unsafe` と `forced_attack_on_unknown` を0とする。

## 受入条件

- 最終sourceは直接親 `558EE5...22DB6` のexact prefixである。
- 同じ207/209/387 shadowで、最初の差は終局12件だけである。
- 非終局の逃げる、Ultra Ball、保存攻撃者進化20件は親と同じ行動になる。
- 終局即攻撃は12/12である。
- Explorer reveal変更とAssemble Alloy資源置換は0である。
- Ultra Ball 5件は親の同じ確定KO・1 Prize・控え形成系列を維持する。
- 両席でEND、cap、同一攻撃、保存攻撃支配、親攻撃支配、比較不能、owner transfer、duplicateを確認する。
- invalid action、例外、stale、owner collision、max-step、非決定性、saved attack lossはすべて0である。

この候補ではRETREATや保存攻撃者進化そのものの最適化は行わない。
親へ安全に戻した後、別の独立bucketで公開Prize交換と返しを完全に比較できる場合だけ実装する。

# Explorer 攻撃期限内の進化・前衛手貼り・中核展開に関する修正

## 位置づけ

この文書は、次の固定戦略を変更せずに補足する。

- 元戦略: `STRATEGY_SELECTION_EXPLORER_CERTIFIED_ATTACK_DEADLINE_PRODUCTIVE_PREFIX_V1.md`
- 元戦略 SHA-256: `71A2CBA1ED1E5048CBC55371A6DEFBF21808E4FED727AACEC304AE1730822822`
- 直接の挙動親: `archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
- 親 SHA-256: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`

元戦略は、保存した攻撃者そのものの進化を禁止している。
これは、ベンチの別個体を安全に進化させることまで禁止する意味ではない。
また、保存した攻撃者への手貼りも、保存済み攻撃の支払いを壊さず別の攻撃を解禁するなら、生産的な同一ターン行動になり得る。

## 追加根拠

修正前の途中版を、207リプレイ、209対象席、387回のExplorer使用に対してshadow実行した。

- `shadow_summary.json` SHA-256: `95BDE8E2F50E7FAA56B41AFD2F88919CFFD54ADFECFA1E9E28A5B34E5F2A0674`
- `shadow_first_differences.csv` SHA-256: `AD86B4AB7104700165CCB2FB125452F72C34BA75842B56BF1527690C556A9331`
- 最初の行動差: 47件
- 親の行動型: 進化18件、手札からの使用16件、逃げる8件、手貼り5件
- reveal pair変更: 0件
- Assemble Alloyの資源置換: 0件
- invalid action、例外、owner collision: 0件

18件の進化は、すべてArchaludon exをDuraludonへ重ねる行動だった。
うち16件は非終局で、進化対象の物理serialは保存した攻撃者と異なった。
これらを一律に止めると、同じPrizeを取りながら次の攻撃者を形成できる局面でも攻撃を先に打つことになる。

非終局の4件では、親がDuraludonをベンチへ出そうとしたが、「現在の手札に進化札がある」または「鋼1枚で直ちに攻撃できる」という狭い条件を満たさないため止められた。
固定デッキにおけるDuraludonは、Archaludon exへの公開された中核進化元であり、将来役割は手札に現在見えている進化札だけでは決まらない。

`88443760` と `88681773` では、保存した攻撃者Duraludonへ鋼Energyを手貼りすると、現在のHammer InによるPrize取得を維持したまま、次のRaging Hammerを解禁できる。
保存した攻撃者への手貼りを一律に拒否するのは誤りである。

## 追加するhard条件

### 1. 保存した攻撃者とは別のDuraludonをArchaludon exへ進化

次をすべて満たす場合、親の進化とAssemble Alloyの全callbackを一つの生産的subtransactionとして許可する。

- 進化元は自分の場のDuraludonである。
- 進化先はArchaludon exである。
- 進化元serialは保存した攻撃者serialと異なる。
- 進化元は進化可能で、親の行動は現在合法である。
- 進化前に保存した攻撃の攻撃者、相手Active、攻撃ID、支払い、確定Prizeが変わらない。
- Assemble Alloyは既存の決定的effect registryと親transactionで解決する。
- callback中の選択をepisode固有値で上書きしない。
- 完全解決後に保存した攻撃を再証明する。

進化しただけで即攻撃せず、Assemble Alloyが発生した場合はその完了まで親ownerを保持する。
保存した攻撃者自身を進化させる行動は、従来どおり許可しない。

### 2. 中核Duraludonのベンチ展開

次をすべて満たす場合、親が選んだDuraludonのベンチ出しを生産的行動として許可する。

- 空きベンチがある。
- 保存した攻撃者と相手Activeを変えない。
- そのDuraludonは固定デッキのArchaludon ex進化元または次攻撃者候補である。
- 同名個体の過剰展開で必要な別役割の枠を消さない。
- 保存した攻撃の確定Prizeを壊さない。

「進化札が現在の手札に見えること」は必須にしない。
ただし、ベンチ満杯、同名中核個体が十分に準備済み、または別の確定した必要役割を圧迫する場合は許可しない。
単なるDuraludonの場の枚数を「十分に準備済み」の証明には使わない。
裸のDuraludon、次の相手ターンに確定で倒される個体、攻撃費用を満たさない個体は、準備済みbackupとして数えない。
別役割の枠を圧迫するという拒否も、その別役割と必要な物理Bench枠を公開情報で具体的に証明できる場合に限る。
この証明がない場合は、親が選んだ中核Duraludonの合法なベンチ出しを広く許可し、実戦で過剰発火が確認されてから狭める。

### 3. 保存した攻撃者への生産的手貼り

保存した攻撃者への手貼りも、次をすべて満たす場合は許可する。

- 保存した攻撃の支払いと確定combatを維持する。
- 手貼り前には払えなかった別の公開済み攻撃が、手貼り後に払えるようになる、または不足Energy数が厳密に減る。
- その改善が単なる同一Energyの重複ではなく、次ターンの攻撃継続へ具体的に寄与する。
- 手貼り後に保存した攻撃を再証明する。

必須positive fixtureは `88443760` と `88681773` のDuraludonへの鋼手貼りから、同じHammer In Prize取得までである。

## 変更しない範囲

- 終局勝利では、進化、ベンチ出し、手貼りを行わず即攻撃する。
- 保存した攻撃者自身の進化、別の攻撃者へ変える逃げる、switch、gustは自動許可しない。
- Ultra Ballの捨て札条件は広げない。
- ExplorerのrevealとAssemble Alloyの資源選択を置換しない。
- 既知episode ID、turn、serialをruntime条件に使わない。
- 進化・展開・手貼りを許可した後も、同一攻撃者、同一相手Active、同一攻撃、非悪化combat、同等以上のPrizeを再証明する。

## 追加検証

- 非終局のベンチArchaludon ex進化を両席で完走する。
- Assemble Alloyが発生する場合と発生しない場合の両方を確認する。
- Duraludonベンチ出しを両席で確認する。
- 保存したDuraludonへ鋼を貼り、Hammer Inを維持しながらRaging Hammerの不足Energyが減ることを確認する。
- 保存した攻撃者自身の進化、ベンチ満杯、過剰な中核展開、現在のPrizeを失う手貼りは拒否する。
- 207/209/387 shadowを最終sourceで再実行し、上記の早すぎる攻撃差が消えたことを確認する。
- 残るRETREATとUltra Ballの差は、別途全件を人間プレイとして監査する。

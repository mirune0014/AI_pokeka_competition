# Gold Meta Rule-base Win Plans

## 目的

各ルールベースを、負け試合への例外規則の集合ではなく、そのデッキが毎試合目指す
勝利経路として育成する。この文書では、公開Goldリプレイから測定できた事実、まだ
検証されていない仮説、現在の実装範囲を区別する。

正確な60枚とローカルagentの対応は
`docs/gold_meta_rulebase_local_agents.csv`を正本とする。デッキコピーが`exact`でも、
`win_plan_status=missing`のtrackは方策未完成である。

## 勝利設計の単位

各trackは次の順序で作る。

1. **Setup contract**: 初期Active、Bench最低数、優先して盤面へ置くlineを定義する。
2. **Development contract**: 最初の進化、Energy、Supporterの順序と目標ターンを定義する。
3. **First attack contract**: 最初に目指す攻撃、許容する代替攻撃、攻撃を遅らせてよい条件を定義する。
4. **Midgame contract**: Activeの役割、後続attacker、Energy sink、盤面維持を定義する。
5. **Prize contract**: 最初のサイドを取る盤面、Boss対象、サイド交換率を定義する。
6. **Recovery contract**: 気絶後の復旧、回収札、次のActive、必要な残存資源を定義する。
7. **Endgame contract**: 最終attacker、詰め、山札切れ回避、最後まで温存する札を定義する。
8. **Safety guards**: 上記の経路を壊さないことを確認してから、反復する負け筋だけを狭く防ぐ。

広いphase/state-machineで既存方策を置換しない。既存方策をpriorとして保持し、Goldの
勝利履歴で支持された一つの遷移だけを隔離して比較する。即時KO、合法な攻撃、必要な
選択数を壊す変更は候補にしない。

## 評価ゲート

終局勝敗に加えて、次を同一seedでbaselineと比較する。

- 目標Bench/line完成率
- 初進化ターン
- 初攻撃ターンと攻撃名
- 初サイドターンとその時点の盤面
- 最大盤面数
- 後続attacker準備率
- 攻撃が途切れたターン数
- recovery後に次の攻撃へ戻れた割合

`tools/summarize_local_traces.py`は、上記に加えて指定したline cardの初サイド時枚数と
初サイド後最小枚数、指定attackerへの最初のEnergy attach、攻撃間のmissed turn、
指定したrecovery cardが盤面を離れてから再攻撃するまでを抽出する。traceは終局直前で
止まる場合があるため、勝敗と最終盤面は`--game-summary`で補完する。

開発seedだけで改善した方策は昇格させない。独立seed holdoutと、異なるGold deck/policy
populationの双方で、対象指標と終局勝敗に再現性が必要である。

## Track 4: MPGaming Mega Kangaskhan ex / Crustle

### 測定済みGold事実

- exact Gold deckの公開リプレイは19戦で、勝ち10・負け9として分離して測定した。
- 勝ち10戦のうち7戦は、Dwebble/Crustle lineを盤面に3体以上置いた。
- 最初の攻撃はCombo 5戦、Ascension 3戦、Scissors 2戦だった。
- 最初がScissorsだった5観測では、KangaskhanにEnergyが付いていなかった。
- 最初にサイドを取った9戦では、盤面は平均3.89体、lineは平均2.11体、
  Kangaskhan Energyは平均1.78枚だった。
- 測定した負け9戦は一度もサイドを取れなかった。
- simple v0はGoldの攻撃選択46/46と一致していた。広いroute/state-machineは、
  正しいsetup、Bench、Supporter順序を上書きして悪化した。

### 現在の勝利経路

1. Dwebbleを優先して開始し、Kangaskhanも盤面へ確保する。
2. Dwebble/Crustle lineを複数本作り、単一Crustleが倒された後も壁と攻撃を継続できる形を目指す。
3. DwebbleからAscension、または既に成立したCrustleからScissorsへ入る。
4. 対exではCrustleをActiveに置き、Scissorsで相手のサイド進行を止めながらこちらの最初のサイドを取る。
5. Kangaskhanは序盤から存在させるが、Gold evidenceがない段階でEnergyを優先集中させない。

### 実装済みで昇格した遷移

v8は次を満たす場合だけ、通常のEnergy/Ascension準備よりXerosicを先にする。

- turn 2
- 双方サイド6
- 自分のDwebble/Crustle lineが3体以上
- ActiveがDwebble
- 現在はAscension/Combo/Scissorsが選択肢にない
- Energy attachが合法
- 相手手札4枚以上
- 相手がEnergyを1枚以上盤面へcommit済み

この遷移は開発600戦で`+5`、独立holdout 600戦で`+2`、11-policy Gold
population 220戦で`+1`、合計`+8/1420`で、測定したpolicy/family別の悪化はゼロだった。
提出候補は`meta_agents/kangaskhan_crustle_mpgaming_v8_legalfix`である。

v8はこの遷移以外にも、Dwebble優先の初期Active/Bench、Kangaskhanの副setup、
Crustle進化、対exでのCrustle昇格、Poffin/Hilda/Lillie/Pokegearのsetup優先を持つ。
既に合法なAscension/Scissors/Comboの順位は変更しない。

### 未実装・未検証

- **Reserve-line continuity**: Active Crustleが攻撃可能な間にBenchのDwebble/Crustleへ
  Energyを渡す仮説はGold勝利で観測されたが、v9は5つの決定的な敗北を生み棄却した。
- **Kangaskhan finisher**: Kangaskhanへ先にEnergyを集める広いoverlayはGold evidenceと
  整合せず棄却した。終盤へ切り替える公開状態の条件はまだ未確立である。
- **Recovery loop**: Crustle気絶後、どのBenchをActiveにし、何ターン以内にScissorsへ
  戻すべきかの成功率はまだ集計されていない。
- **Prize map**: Bossを使う対象と、Crustleで取るサイド/Kangaskhanで取るサイドの分担は
  未定義である。

次に検証する価値が最も高い仮説は、初サイド後も複数lineを維持してからKangaskhanへ
commitする遷移である。ただし、具体的なBench Energy強制はv9で反証されている。
候補化する場合は、即時攻撃・攻撃対象・46/46一致しているGold攻撃判断を一切変えない
公開状態predicateに限定する。

昇格には、v8 legality-fixと同一の開発600戦、untouched holdout 600戦、Gold population
220戦を使う。action/max-step error 0、既存Xerosic gateの保持、family別回帰0に加え、
開発+holdout 1200戦で少なくとも1つのpaired net gainを要求する。

したがってv8は完全な勝利方策ではなく、Gold deckの正確なコピーと、blind評価を通過した
最初の能動的なopening遷移である。Kaggle probeでは最終スコアだけでなく、上記の経路が
何戦で成立したかを測定する。

### Local win-plan instrumentation smoke

v8 legality-fixを同一デッキv0相手に両席10戦ずつ実行した。これは性能評価用のblind
panelではなく、計測器と次の仮説を確認する20戦smokeである。

- candidateは11-9だった。
- 勝ち11戦は全戦で攻撃と初サイドに到達し、初攻撃は平均turn 3.91、初サイド時lineは
  平均2.91体だった。最初にKangaskhanへEnergyを付けたゲームは2/11だった。
- 負け9戦は攻撃到達8/9、初サイド2/9、初攻撃は平均turn 8.88、初サイド時lineは
  平均1.50体だった。KangaskhanへのEnergy attachは8/9だった。
- 勝ちの最初の攻撃はAscension 8、Scissors 2、Smash Kick 1。負けはCombo 6、
  Ascension 2、無攻撃1だった。

この差は、複数lineと早いAscensionが勝利経路であり、早期Kangaskhan commitがbrickの
兆候である可能性を示す。ただし、attachが敗因なのか、lineへの合法な付け先がない悪い
drawの結果なのかは未確定である。各初回Kangaskhan attach時の合法optionを監査するまで、
抑制ルールは実装しない。

合法optionを保存して再実行すると、最初のKangaskhan attach 10件のうち7件には
Dwebble/Crustleへの合法な代替があり、内訳は勝ち2・負け5だった。turn 1かつDwebble
代替ありは勝ち1・負け4だったため、v10で「6-6、turn 1-2、Active Kangaskhan、攻撃不能、
Bench lineあり」の場合だけDwebbleへ付ける遷移を隔離した。

v10は合法性を修正したv0 mirrorを使う有効な1420戦で、v8 `911-508-1`に対して
`906-513-1`だった。Gold populationは`152/220 -> 155/220`と改善したが、Alakazam
`-6`、Okidogi `-7`、合計`-5`となったため昇格しない。Cynthia `+2`、Marnie `+4`、
mirror `+1`の改善は、仮説が一部局面では有効である証拠として保持する。現在はgainと
regressionの最初の分岐状態を比較し、公開情報だけで安全に狭められるかを検証中である。

初回評価で出た`IndexError`はv10ではなく、対戦相手v0が`minCount=8`に7枚しか返さない
既知の合法性バグだった。戦略を変えず選択数だけ修正した
`meta_agents/kangaskhan_crustle_mpgaming_v0_legalfix`で同seedを再現し、全1420戦を
action error 0、max-step 0で完了した。

v11は、v10のAlakazam 6回帰を公開`305/741`、Okidogi 7回帰を公開`675`または
Active `116`でv8へ戻した。元の23 gainsをすべて保持し、既存1420戦ではv8
`911/1420`に対してv11 `919/1420`、全family非悪化まで改善した。

しかし、このguardは同じ1420戦から導いたためblind証拠ではない。未使用`202614xxx`
広域600戦と、16 exact Gold policy trackを別々に保った未使用`202615xxx` 320戦で検証した。
広域は`379 -> 374`でArchaludon `-3`、Marnie `-2`、mirror `-1`、Okidogi `-1`、
Gold track panelは`226 -> 231`だった。合計920戦は`605 -> 605`で同率となり、広域の
複数style回帰が残るためv11も昇格しない。v8 legality-fixを提出候補として維持する。

v12はさらに単純化し、Active/BenchにKangaskhanを1体ずつ確保し、Grow Grass Energy
`18`とBench Dwebbleがある6-6、turn 1-2、攻撃不能のときだけDwebbleへ付けた。既知
2340戦では`+2`、回帰0だったが、完全未使用920戦でSota Marnieのseed `202616020`を
1つ悪化させた。全3260戦では2 gains・1 regression、総計`+1`に留まり、fresh panelが
`-1`なので昇格しない。

2 gainsの盤面はどちらもBench `Kangaskhan + Dwebble x2`、唯一のregressionはBench
`Kangaskhan + Dwebble x4`だった。4本成立済みなら追加line投資は不要という正の盤面
条件から、v13はBench Dwebbleがちょうど2体の場合だけv12を許可した。

v13は全4180戦でv8 `2711-1458-11`に対して`2715-1454-11`となり、4 gains・0
regressionsだった。完全未使用`202620xxx/202621xxx` 920戦でも`+2`、family/style
回帰0だった。39戦で直接行動が変わり、全件が6-6、turn 1-2、Active Kangaskhan、
Bench Kangaskhan 1体とDwebbleちょうど2体、Grow Grass Energy `18`からBench
Dwebbleへのattachだった。残る35件は結果中立である。

runtime archiveは
`candidate_kangaskhan_crustle_mpgaming_v13_backupkang_two_growline_runtime.tar.gz`、
SHA256 `D7435351E79EEA561DED6B924E092E2EA6072DFAAAD501C0EEE79EBDB54F130E`。
13 members、exact 60 cards、extracted import、5-game packaged smokeを通過した。v13を
次のquota reset後のlive Bronze probeへ昇格する。

## Track 1/16: Shumpei Archaludon

### 現在把握している経路

1. Duraludonを優先setupする。
2. Metal Energyをdiscardへ送り、Archaludon exのAlloyで加速する。
3. 2本目のDuraludon/Archaludonを維持し、攻撃を途切れさせない。
4. RelicanthをEnergy sinkまたは非ex攻撃経路として使う。
5. Night Stretcherを単なる回収ではなく、次のattacker成立へ使う。
6. Bossでサイド交換を短縮する。

route-aware helperは実装済みだが、最新CLI scoreは2026-07-13 05:23 JSTで703.4だった。
この結果は勝利経路が十分に完成していない証拠として扱う。今後Archaludonへ戻る場合は、
個別の敗戦guard追加ではなく、2本目のattacker成立率、初攻撃/初サイド、Stretcher後の
再攻撃率を先に測定する。

## 残りtrackの状態

Track 2はproactive Alakazam engine-flowを3版試したが、blind local gateを通過していない。
Track 3、5-15はexact 60-card copyと実行可能なsimple方策までで、専用の勝利設計は未完成である。
同じAlakazam/Marnie familyでも、deck hashまたはpolicy styleが違うtrackを平均化しない。

次の育成順は、まずTrack 4をKaggle Bronze/Silver gateで評価し、結果が成熟した後に、
別Gold familyの勝利リプレイから同じ形式の設計書を作る。負け試合だけから次の変更を
選ばない。

## Kaggle live win-plan evaluation

`tools/summarize_kaggle_winplan.py`を追加した。提出IDから自分のseatを解決し、公開リプレイを
1試合1行へ変換する。主な指標は初進化、初攻撃、初サイド、各時点の主力line数、最大盤面、
指定Energyから指定Pokemonへの初attach、攻撃間の空白turnである。勝敗と結合して、単なる
最終scoreではなく、狙った展開が成立した試合と成立しなかった試合の勝率を比較する。

観測logは差分、累積、inactive中の反復が混在するため、同一log反復を除外し、累積prefixから
新規suffixだけを抽出する。Shumpei提出38 replayでsmoke済み、synthetic regression testを含む
関連testは12件通過した。MPGaming v13提出後はline card `344/345`、Grow Grass Energy `18`、
target `344`、line threshold 3で集計する。今後の変更候補は、このlive成立率とlocal paired
結果の両方を満たす必要がある。

### MPGaming Gold route split and replay-action correction

2件のGold勝利は同一経路ではなかった。`85023093`はOgerpon toolboxに対し、Ascension後に
CrustleのSuperb Scissorsを連続使用して5サイドを取った。`85023197`はAlakazamに対し、
Xerosicを繰り返しながらCrustleを壁として使い、相手deckを0まで進めつつ、Bench
KangaskhanへEnergyを蓄えてturn 16からRapid-Fire Comboへ切り替えた。

後者のstep 66 observationでは、6-5で自分Activeが無Energy Crustle、Benchに無Energy
KangaskhanとDwebbleが存在し、攻撃不能だった。Kaggle replayはobservationに対する行動を
次frameへ保存する。正しいGold行動はfollowing-frame `[7]`のXerosicであり、同frame `[2]`は
直前selectionの行動だった。Xerosic後のstep 68 observationに対するfollowing-frame `[2]`が、
Spiky Energy `14`から無Energy Bench Kangaskhanへのattachである。v13は両状態でPoffinを選ぶ。

したがって正しい公開情報経路は、相手deck 18・hand 13でXerosicを先に使い、hand 3へ減らした
後にKangaskhanを加速する`Xerosic -> recovery attach`である。step 79でCrustleが盤面から消え、
準備したKangaskhanがActiveとなり、step 84で2枚目のEnergyを得ている。

### Post-prize recovery ablation result

v14からv17は、後続Kang attach自体の価値を1回で放棄せず段階的に検証した。ただし後の
frame対応auditにより、これらはGold step 66の記録行動を再現していなかったことが判明した。
以下のlocal paired結果は方策変更の反証として有効だが、「Gold教師一致」という主張は撤回する。

- v14は同frame `[2]`をattach教師と誤認して実装し、未使用`202622xxx` 600戦でv13
  `356-244`に対し`354-246`、Alakazamを中心に`-2`だった。
- 6 flipをtrace付きで再実行すると、v14は2改善・4悪化だった。2改善は相手fieldが4体以下、
  4悪化は5体以上だった。Goldはfield 5体だが相手deckが18枚だった。
- v15は`field <=4 or opponent deck <=18`へ限定し、既知2改善を保ち4悪化を除いたが、
  blind `202623xxx` 600戦で`362-238 -> 361-239`と`-1`だった。
- v16は低deck分岐へ自分Dwebble存在を追加し、v15のblind悪化を除いたが、blind
  `202624xxx` 600戦で`374-226 -> 372-228`と`-2`だった。
- v17は自分Dwebbleを共通条件とし、`opponent deck <=18`または
  `opponent field <=4 and hand >=5`だけに限定した。既知2改善を保ち、既知7悪化を
  除いた。完全未使用`202625xxx` 600戦ではv13/v17とも`353-247`、flip 0だった。

結論としてv14-v17は提出不可である。正しいGold経路はv18で、`opponent deck <=18`、6-5、
無Energy Active Crustle、自分Dwebbleあり、攻撃不能を共通状態とし、opponent hand >=4なら
Xerosic、Xerosic後のhand <=3ならSpikyを無Energy Bench Kangaskhanへattachする二段階方策として
検証する。相手archetype IDやhidden情報は使わない。

v18はGold `85023197`のrecorded mismatchを`31 -> 29`へ減らし、step 66のXerosicとstep 68の
Spiky-to-Kang attachだけを新たに一致させた。Ogerpon側Gold `85023093`の67判断はv13と完全一致
した。未使用`202626xxx` 600戦ではv13/v18とも`354-246`、全6対面差0、flip 0、error 0だった。
正しいGold経路を安全に表現しているがlocal改善作用は未確認であるため、最初のlive probeは
v13を維持する。v18はliveで同じ低deck/大hand/Xerosic状態が観測された場合の次候補とする。

## 2026-07-13 - MPGaming proactive recovery route v19-v24

Gold勝利`85023093`ではCrustleが30 HPからJumbo Ice Creamで回復してからScissorsを継続し、
`85023197`ではKangaskhanが100 -> 180 -> 260 HPと回復してからComboへ戻っていた。このため
v19では「攻撃可能かつActiveのmissing HPが80以上なら先に回復」を、対面IDやhidden情報を
使わない正の勝ち筋として実装した。v19は独立600戦で2回とも`+15`、exact Gold 320戦で`+9`
だった。これは個別の負け対策より大きく、回復を攻撃継続の一部として扱うことの有効性を示す。

一方、無条件回復は接戦での即時KOやnear-KOを遅らせ、Archaludon代理で3回帰を生んだ。
v20の広い「賞品先行またはlethalなら攻撃」は回帰を消したが、12利得中9件も消して`+3/320`
まで低下した。v21-v23では、次の公開情報による役割ベースの変換へ狭めた。

- 相手deckが3以下ならstall routeとして回復を維持する。
- 賞品差1以内で、合法な固定damage攻撃が相手Activeを残り10 HP以下にできる場合だけ検討する。
- 相手Activeが40 HP以下、または自分Activeのprinted HPが300未満なら攻撃へ変換する。
- 300 HP級の耐久役はmissing HPが160以上なら回復を続け、160未満で攻撃へ戻る。

最終v23は開発exact Gold 320戦で`209 -> 221`、完全未使用broad 600戦で`359 -> 375`、
完全未使用exact Gold 320戦で`221 -> 231`だった。全評価でduplicate mismatch、action error、
max-stepは0。Gold 2 replayではv19と全判断一致で、正の回復経路を保持した。blind broadの
Marnie代理だけは`-3/100`だったが、Alakazam 3種`+11`、mirror`+7`を含め全体`+16`だった。

相手bench 3体以上で攻撃を優先するv24も試したが、対象Marnie 5回帰のうち1件しか改善せず、
2既知利得を保持しただけだったため棄却した。小標本の盤面幅を安全ガードへ昇格させない。

提出候補は`candidate_kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard_runtime.tar.gz`。
SHA256は`6DC31311CE6E189BB2685367CB0FCF2EC843DC17EBCCBF2E1BBBF1DA80A9FC12`、13 members、
exact 60 cards、展開後importおよび5-game smokeを通過した。

### v23 blind flip route attribution

blind broad 600戦の全30 flipを同一seed・同一seatでtrace再生成した。23 gains・7 regressionsの
全件で最初の方策差はv23のJumbo Ice Creamだった。初進化turnと初攻撃turnは全flipで同一で、
改善はsetup高速化ではなくready後のattacker sustainである。

- gainsではv23の平均攻撃回数が`14.2`、v13が`8.0`だった。
- gain終局はboard clear 15件、deckout 8件だった。
- 最大盤面とCrustle line幅は実質同一で、deck construction/board width差ではない。
- Alakazamは11/11 gains、mirrorは8 gains/1 regression、Okidogiは2/3 gainsだった。
- Marnie seat 1だけは5 regressions/2 gainsで、v23の攻撃回数`8.9`はv13の`9.6`を下回った。

liveで期待する正のsignatureは、ready後の`Jumbo Ice Cream -> Mega Kangaskhan`から攻撃回数が
増え、board clearまたはopponent deckoutへ到達する流れである。警告signatureは、Marnie相手に
同じearly Jumboが発生しても攻撃回数が増えず、長期枯渇routeの成立前にboard lossする流れとする。
根拠は`analysis_outputs/mpgaming_v13_vs_v23_fresh202630_winplan_attribution`に保存した。

### Independent Marnie population confirmation

単一Sota panelの`-3/100`が一般化するかを、Gold 4 styleとSotaの5方策、完全未使用
`202635xxx` 500戦で再確認した。v13 `417-83`に対しv23 `423-77`で`+6`だった。
Gold style別は`0,+1,+2,+3`、Sotaは`80-20 -> 80-20`で中立、両seatは`+1,+5`だった。
duplicate mismatch、action error、max-stepは0。したがって単一panelのMarnie悪化は再現せず、
根拠の弱いMarnie専用patchを提出前に加えない。根拠は
`analysis_outputs/mpgaming_v13_vs_v23_marnie_population202635_evaluation`に保存した。

### Live focus-play telemetry

`tools/summarize_kaggle_winplan.py`にrepeatable `--focus-play-id`を追加した。v23では
`--focus-play-id 1147`を指定し、episodeごとのJumbo使用回数、初使用turn、同turn攻撃復帰、
初Jumbo後の初攻撃delay、初Jumbo後の攻撃回数を記録する。aggregateではJumbo使用率、
使用あり/なし勝率、攻撃復帰率、同turn攻撃率、回復後攻撃回数中央値を出す。累積log dedup、
同turn復帰、後turn復帰、未使用を含む関連6 testが通過した。

Gold 2勝へ適用すると、`85023093`はJumbo 1回、同turn攻撃復帰、Jumbo後5攻撃、
`85023197`はJumbo 2回、同turn攻撃復帰あり、Jumbo後2攻撃だった。2勝aggregateは
focus-play recovery rate `1.0`、same-turn attack rate `1.0`、Jumbo後攻撃中央値`3.5`である。
live v23はこのGold基準へ近づくかを比較する。出力は
`analysis_outputs/mpgaming_gold_focusplay_telemetry_py311`に保存した。

### Kaggle runtime validation and v25 promotion

2026-07-13 09:00 JST以降にv23を提出したが、`54625597`は2-step validationで即時ERRORになった。
tar member順を`main.py`先頭へ直した`54625845`も同じ即時ERRORであり、member順は原因ではなかった。
Kaggle validatorが`main.py`を`__file__`なしで`exec`する条件をローカル再現すると、v23の
`Path(__file__)`がimport時に失敗した。v25では`__file__`がない場合に
`/kaggle_simulations/agent`へfallbackするだけとし、方策本体は変更していない。

- v23/v25のexact 16-track比較は320/320 game tuple一致、双方`208-112`、error 0だった。
- v25は通常import、`__file__`なしexec、展開後5-game smokeのすべてを通過した。
- 最終archiveは`candidate_kangaskhan_crustle_mpgaming_v25_runtime_root_compat_mainfirst.tar.gz`、
  SHA256 `D1207336819C9BE3362DE336EC0E7F596BA5ADF133E428E5287C7A4F42EC3EC4`である。
- Kaggle submission `54626152`はvalidation episode `85656851`を完了し、`600.0`で
  `COMPLETE`になった。2026-07-13 09:17 JST時点ではpublic gameはまだない。

以後のlive判定はv23で定義した勝ち筋telemetryをそのまま使用する。validation成功だけでは
track昇格とせず、public戦でJumbo後の攻撃継続、board clear/deckout、対Marnie警告を確認する。

### Initial live route evidence and telemetry correction

最初の5 public戦では`2-3`、`445.7`まで低下したが、その後4連勝して09:43 JST時点で
`6-3`、`618.6`まで回復した。勝ちはStarmie/Froslass 2件、Alakazam、Ogerpon toolbox、
Hop/Trevenant、Rocket Mewtwo/Spidops。敗戦はStarmie/Froslass、Crustle耐久mirror、
Dragapultだった。回復中のため置換しない。

旧telemetryは、攻撃でturnが終了した場合のattack logが相手側またはterminal frameにのみ
現れることを扱えず、Crustle mirrorのJumbo後攻撃を0と誤集計した。全seatの観測から
event streamを復元し、次turn frameのattackを直前turnへ帰属させるよう修正した。
関連testは6件通過した。修正後の9 public戦では次の正のsignatureが確認できる。

- Jumbo使用は3/9戦、使用戦績`2-1`、未使用戦績`4-2`。
- Jumbo後の攻撃復帰率と同turn攻撃率はいずれも`1.0`。
- 初Jumbo後の攻撃回数中央値は`6`。
- 初回wide-line attackはまだ1/9戦であり、盤面幅の成立は引き続き弱い。

Crustle mirror敗戦`85657918`は、Jumbo後に120攻撃したが、非致死かつSpiky反動後110 HPとなり、
公開済み120 retaliationで倒された。v26として追加healを優先する狭い候補を作ったが、実replay
decision比較では未だ差を再現できていないため未昇格。Starmie敗戦`85657425`はsole Crustleで
reserveがなく、Dragapult敗戦`85658412`は初期Poffin/basic不在が主因だった。1 replayだけの
Lillie/盤面幅patchはまだ加えない。

### Balanced policy methodology and v27 rejection

勝ち筋telemetryは単独の最適化目標ではない。銀圏へ到達した従来の改善方法と同様に、合法手品質、
初動、資源管理、賞品レース、対面処理、反復する敗因、隣接分布の非劣化を維持し、その追加軸として
盤面形成とデッキ本来のroute成立を評価する。

15 public戦時点では`9-6`、Mega Lucarioが`1-2`だった。2件のLucario敗戦はrace/route変換が弱いが、
共通する明白な誤手はなく、Crustle系2敗もKangaskhan不在のcontinuity不足ではあるものの、Poffinの
合法候補にKangaskhanがないなどdraw varianceが強かった。v26は対象実replayで差0、mirror 400戦で
`-2`のため棄却した。

Gold 2勝ではv25が記録方策と`29/61`、`40/67`判断で異なり、攻撃前の進化・attach・setupが多かった。
この観測からv27で、公開固定damageのKOとAscensionを保護しつつ、必要な進化・後続attach・薄い盤面の
setupを非致死攻撃より先にした。しかし結果は明確な失敗だった。

- Mega Lucario 320戦: v25 `302`勝、v27 `164`勝、`-138`。
- broad 320戦: v25 `199`勝、v27 `135`勝、`-64`。
- 合計640戦: v25 `501`勝、v27 `299`勝、`-202`。duplicate mismatch/error/max-stepは0。
- 15 live replayの537判断中68件を変更したが、変更は既存勝利側だけで、狙った敗戦では発火しなかった。

したがって「Goldがsetupしたためsetupを先にする」という一般化は棄却する。次候補は実際の敗戦状態で
発火し、KO/既存勝利を維持し、複数対面のpaired評価を通ることを必須とする。根拠は
`analysis_outputs/mpgaming_v25_vs_v27_pre_attack_20260713`に保存した。

## Track 5: Cynthia/Garchomp Champion's Call sequencing

MPGaming v25は28 public戦で`14-14`、`591.2`となり、Bronze未満で停滞した。Mega Lucario 5戦と
Dragapult 3戦を勝敗比較したが、2敗以上に共通して勝ちにはない同一誤判断は確認できなかった。
v13 rollbackも20戦780判断中5戦8判断だけが変わり、変更戦績`3-2`、Jumbo使用勝率`60%`で、
既知のlocal利得を覆す根拠がなかった。

次のexact Gold trackであるnasuo445 Cynthia/Garchompは4 replay、324判断を持つ。既存代理は
181判断で記録方策と不一致だった。4 replay共通で、記録方策はGabiteのChampion's Callを先に使うが、
代理はGarchomp ex進化`25000`を能力`9500`より優先し、29局面で能力を失っていた。

全Champion's Callを常時最優先にしたv2は一致を`181 -> 147`へ改善したが、Great Tusk `-2/200`、
Mega Lucario `-8/40`で棄却した。v3は「そのGabiteを今からGarchomp exへ進化できる」場合だけ、
同一serialのChampion's Callを進化より1点高くする。既存のKO、Boss、Surfer、退却、攻撃選択は保持する。

- Gold recorded mismatch: `181 -> 161`。4 replayすべて改善。
- targeted 400戦: `121 -> 128`、Cynthia mirror `+7`、Great Tusk中立。
- broad 360戦: `174 -> 193`、合計`+19`。Kangaskhan/Marnie Sota中立、Arch/Alakazam/
  Mega Lucario/Starmie/Dragapult/Ogerpon改善、TW Shinのみ`-1/40`。
- duplicate control一致、action error/max-step 0。
- archive exact smokeは5/5完了、deck 60、normal import、`__file__`なしexec、py_compile通過。

提出archiveは`candidate_cynthia_garchomp_nasuo445_v3_champions_call_runtime_20260713.tar.gz`、
SHA256 `B05C3386C7F6F92534967A3542405FCB03DE692FAFCF176BACD01DE2E8889342`、13 members、`main.py`先頭。
提出仮説は、無料検索能力を進化前に回収する狭い修正がCynthiaの本来の展開を改善し、MPGamingの
591 plateauより高いlive競争力を示すこと。主なriskはGold履歴が1勝3敗と小さく、local相手方策が
liveを再現し切れないこと。validation error時は同slot内でruntimeだけを診断し、方策失敗時は
Cynthia v3を保持して次の反復へ進む。

Kaggle submission `54628744`として2026-07-13 10:55 JSTに提出した。validation episode
`85668666`を完了し、`COMPLETE / 600.0`となった。初回取得はvalidation 1件のみ。以後は
Champion's Call使用回数だけに限定せず、Garchomp進化速度、Roserade幅、energy/tool配分、
初攻撃・初賞品、賞品レース、対面別勝率、合法手errorを総合評価する。

### Cynthia initial live losses and v4-v6 rejection

公開8戦時点では`4-4`、`538.2`。勝ちはOgerpon toolboxを含む4件、敗戦は
Kangaskhan/Crustle、Alakazam、Mega Abomasnow/Kyogre、Starmie/Froslassで、単一対面への
集中ではない。Alakazam敗戦`85669685`は、単独Gible・空bench・Lillie 2枚の状態でHildaを先に使い、
進化札とenergyを得た一方でbench basicを引けず、turn 5に単騎KOされた。

Gold履歴で観測した早期bench飽和から、v4はGarchomp line成立後に任意basicを抑えて1枠を残した。
しかしtargeted 400戦は`128 -> 127`、broad 360戦は`180 -> 179`で、4 Gold replayと最初のlive敗戦では
発火0だったため棄却した。

v5は単独Active・空bench・手札basicなしでLillieを優先した。Alakazam 3方策・両席300戦の初回固定
評価では改善を確認したが、同じ条件がArchaludonとMega Lucarioで各`-2/40`を生み、一般ルールとしては
安全でなかった。v6は公開盤面にAbra/Kadabra/Alakazamが見える場合だけへ限定し、非Alakazam broad
360戦をbaselineと完全一致させた。しかし独立再評価のAlakazam 300戦は`179 -> 177`、seat 1で`-4`、
10 gains/12 lossesとなり、exact live判断を変えても隣接Alakazam分布を悪化させたため棄却した。

したがって残り提出枠は使わない。現行v3は700未満だが、回復中または有効候補なしの置換を避ける規則に
従い、次は新しい公開敗戦の反復パターンを待つ。根拠は
`analysis_outputs/cynthia_v3_vs_v4_reserve_bench_20260713`、
`analysis_outputs/cynthia_v3_vs_v5_single_active_lillie_retry_20260713`、
`analysis_outputs/cynthia_v3_vs_v6_alak_single_lillie_20260713`に保存した。

### Cynthia v7-v9: Gabite幅を作る展開方針と対面安全策

公開15戦時点でv3は`7-8`、約`486`まで低下し、その後CLI確認でも`471.1`だった。Gold 4 replayを
意味的に再監査すると、324判断中160件がv3と不一致で、4 replayすべてに「Garchomp exを先に取らず、
Champion's Callで複数のGabiteを先に揃える」反復パターンがあった。これは単発の敗因対策ではなく、
Cynthiaデッキが継続的にGarchomp exを供給するための盤面形成ルートである。

v7は、場のGabiteが3体未満ならGibleから取れるGabiteをGarchomp exより優先した。Gold不一致は
`160 -> 153`へ改善し、960戦で`364 -> 374`だったが、Great Tusk `-4`、Alakazam `-3`のため棄却した。
v8は公開Alakazam/Great Tusk識別後に元方策へ戻したが、Great Tuskの識別前に差が出て`376/960`、
Great Tusk `-4`が残った。

v9は安全IDへDwebble/Crustle `344/345`を加え、盤面から対面を識別できた後はGabite幅ルールを止める。
固定seed 960戦でv3 `364`に対してv9 `379`、`+15`、error/max-step 0。対面合計の最大悪化は`-1`で、
Cynthia `+3`、Dragapult `+1`、標準Starmie `-1`、拡張Starmie `+5`だった。Great Tusk/Alakazam/
Archaludon/Marnie Sotaは各`-1`以内、Kangaskhan、Marnie TW、Mega Lucario、Ogerponは中立だった。

評価担当が拡張Starmieの片側`-4`を全体差として報告したが、同一seedのv8/v9 240戦を直接比較すると、
result・stepsは全件一致した。拡張Starmieは反対席`+9`を含め合計`+5`であり、候補回帰ではなく集計解釈の
誤りだった。根拠は`analysis_outputs/cynthia_v3_vs_v9_full_candidate_20260713`と
`analysis_outputs/cynthia_v3_vs_v8_gabite_width_safety_sequential_20260713`に保存した。

提出仮説は、Champion's Callを単に一度使うだけでなく、複数Gabiteを先に作って次ターン以降の
Garchomp ex供給を安定させることがCynthia本来の勝つ盤面を形成すること。ただしGreat Tusk/Crustleと
Alakazamを公開盤面で識別した後は既存の対面処理へ戻し、局所的な展開優先が隣接分布を壊すのを防ぐ。
現行v3は十分な公開戦後も700未満で停滞し、v9にはpaired positive evidenceがあるため、残り1枠での
置換を正当化する。validation/runtime error時は方策を変えず梱包だけを診断し、liveで明確に失敗した場合は
Gabite幅の発火と初Garchomp攻撃、初賞品、後続攻撃継続を併せて分析する。

提出archiveは
`candidate_cynthia_garchomp_nasuo445_v9_gabite_width_crustle_safety_20260713.tar.gz`、
SHA256 `A4B1CD4AE145A84FBF5436B12BCE4176C939894E97C5469490D35529A685A30A`。13 members、
`main.py`先頭、deck 60行、source/package一致、Python 3.11でnormal import、`__file__`なしexec、
py_compile、5試合smoke（action error/max-step 0）を通過した。

Kaggle submission `54630859`として2026-07-13 12:16 JSTに提出した。validation episode
`85678496`は完走し、`COMPLETE / 600.0`。初回取得はvalidation 1件、公開戦0件で、出力は
`analysis_outputs/kaggle_live/submission_54630859_cynthia_v9`に保存した。公開戦開始後は対面別勝率に加え、
複数Gabite成立、初Garchomp ex攻撃、初賞品、Garchomp継続供給、既存の合法手・資源・賞品レースを総合評価する。

validation replayを両席でv3/v9比較したところ、124判断中の差はseat 0の1件だけだった。turn 5、
Champion's Callの検索でv3はGarchomp ex `381`を選ぶが、提出済みv9はGabite `380`を選び、Kaggle記録行動と
一致した。seat 1の54判断は差0。したがって、提出archiveでも狙ったGabite幅ルールが過剰発火せず、実際の
Kaggle実行状態で正しく動作したことを確認した。比較出力は
`analysis_outputs/kaggle_live/submission_54630859_cynthia_v9/validation_v3_vs_v9_seat0.json`と
`validation_v3_vs_v9_seat1.json`。

### Cynthia v9 first three public games and v10 rejection

最初の公開3戦は0-3、更新score 414.28。対面はOgerpon toolbox、Starmie/Froslass、
Archaludonで、単一対面への集中ではない。v3/v9 action attributionでは、Ogerponの76判断と
Starmieの32判断は完全一致し、新しいGabite幅ルールは敗因ではなかった。

Ogerpon戦85678570はturn 6に最初のGarchomp、turn 10に2体目まで成立し、初賞品も取ったが、
単賞品Crustleの240 damage連鎖に2賞品Garchompを繰り返し倒され、1対2交換で敗れた。初動、進化、
energy配分、攻撃対象に明白な代替手はなく、1試合からGarchomp温存ルールは追加しない。

Starmie戦85679036はGarchompへ1度も進化できず、Mega Starmie exの120 active + 50 benchが
turn 5/9に複数の70 HP basicを同時KOし、turn 13に盤面全滅した。Power Weightとenergy配分は
利用可能な範囲で妥当で、benchを狭める規則はno-active敗戦を増やすため追加しない。

Archaludon戦85679525では、v3/v9の50判断中1件だけが異なった。turn 3のChampion's Callでv3は
Garchomp exを取るが、v9はGabiteを取り、2体目のGibleを同turnにGabiteへ進化してから別のCallで
Garchomp exを確保した。結果、turn 5に2体のGarchomp exが成立したため、v9変更は敗因ではなく
明確に展開を改善した。敗戦は相手のCinderace、3-energy Duraludon、Cape、Boss、その後の
Archaludon exが連続したtempo/prize pressureによる。

GoldのNight Stretcher継続回収を公開状態で狭く実装したv10も評価した。discard Garchomp + 場Gabite、
discard Gabite + 場Gible、または空bench + discard Gibleの場合のみStretcherを18900へ上げた。
固定520戦はv9 246勝、v10 247勝で+1、Ogerpon中立、Starmie +3、Alakazam +1だったが、
Cynthia mirrorが117 -> 114、-3となったため棄却した。error/max-step 0、duplicate control一致。
根拠はanalysis_outputs/cynthia_v9_vs_v10_stretcher_continuity_20260713。

続く公開4戦目85680045はMega Abomasnow/Kyogreへの勝利で、戦績1-3、score 470.93へ回復した。
この勝利もv3/v9の22判断は完全一致。最初の4公開戦におけるv9変更はArchaludon敗戦の1判断だけで、
その判断は2体のturn-5 Garchomp成立を可能にした。したがって現時点の低scoreはv9変更の回帰を示さない。

公開5戦目85680524はStarmie/Froslassへの勝利で、戦績2-3、score 521.68へ回復した。v3/v9の65判断中
1件だけが異なり、turn 3にv3はGarchomp ex、v9はGabiteを検索した。v9は記録行動と一致し、first
evolution turn 3、Power Weight付きGarchomp、turn 9 Draconic Buster、turn 13初賞品へつながった。

expanded Starmie 200戦の勝敗比較では、勝ち61戦は両席ともGabite/Garchomp成立率と早期Power Weight率が
高く、敗戦139戦は初攻撃・初賞品がむしろ早かった。board-clear/no-activeは敗戦の36/139、勝利では0。
したがって単純な早期攻撃は勝ち筋ではなく、進化中間段階を確保してGarchomp routeを完成させることが
主要な成功指標である。提案された「Gabiteが未成立ならGarchompよりGabiteを取る」は既にv9が実装しており、
新規変更ではない。根拠はanalysis_outputs/cynthia_v3_vs_v9_full_candidate_20260713/expanded_starmieと
analysis_outputs/kaggle_live/submission_54630859_cynthia_v9/winplan_20260713_123831。

公開6戦目85680994もMega Abomasnow/Kyogreへの勝利で、0-3開始から3連勝し、戦績3-3、
score 544.08まで回復した。v3/v9の51判断中1件だけが異なり、turn 5の提出済みv9行動がKaggle記録と
一致した。現行は回復中であり、有効候補なしに置換しない。

### Cynthia v11: Poffin後の役割選択とblind holdout

公開7、8戦目はMarnie/GrimmsnarlとAlakazamへの連勝で、v9は0-3開始から5連勝し、
`5-3`、`617.33`まで回復した。Marnie戦ではv3/v9の108判断中2件が異なり、どちらもv9が
Garchomp exよりGabiteを検索してKaggle記録行動と一致した。両勝利ともGible、Gabite、
Garchomp ex、Roseradeを成立させ、Power Weight後も攻撃を継続した。これはGabite幅だけでなく、
主攻撃ラインとRoserade支援を両立する盤面が重要であることを示す。

Gold差分監査では、Buddy-Buddy Poffin使用後の`TO_BENCH`選択がv9では全候補同点になり、
Gible、Roselia、Spiritombの役割を評価していないことが判明した。v11はこの選択だけを変更し、
場のGibleが3体未満なら`9000 - 700 * count`、Roseliaが2体未満なら`6500`、Spiritombが
未成立なら`3800`として、Garchomp継続供給に必要なGible幅を優先する。他のv9方策は変更しない。

- 開発panel 720戦: v9 `338`勝、v11 `365`勝、`+27`。両席`+19/+8`、12対面中8対面改善、
  3対面中立、標準Starmieのみ`-3/60`。
- 未使用seed `202653000`のblind holdout 480戦: v9 `225`勝、v11 `245`勝、`+20`。
  両席とも`+10`。Starmie合算`28 -> 32/80`、Cynthia mirror `23 -> 26/40`、
  Alakazam `17 -> 23/40`。Archaludon `-3`、Great Tusk/Crustle `-2`は要監視。
- 合計1200戦は`+47`。duplicate controlは全件一致し、action error/max-stepは0。
- 根拠は`analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713`と
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_holdout_20260713`。

続く公開9、10戦目はStarmie/FroslassとOgerpon toolboxへの敗戦で、v9は`5-5`、
`551.68`へ反落した。Starmie敗戦ではv11がPoffinの2判断をGible幅側へ変更し得るが、
Ogerpon敗戦ではv9/v11の126判断が完全一致する。したがってv11はOgerpon単発敗戦のpatchではなく、
複数対面で再現した盤面形成改善として扱う。OgerponはGarchomp/Roserade成立後のdeck-out/control、
Starmieは初Garchompがturn 7、初賞品なしで攻撃継続を失った敗戦だった。

提出候補は`candidate_cynthia_garchomp_nasuo445_v11_poffin_role_selection_20260714.tar.gz`、
SHA256 `E7F2FF3080DA20352BCFECF793B025357771F33C9FE0F285AA346162C98E4228`。13 members、
`main.py`先頭、deck 60行、py_compile、normal import、`__file__`なしexec、12-game archive smokeを
通過した。2026-07-13の5枠は消化済みのため提出せず、次回reset時にv9が700未満で停滞または失速を
続ける場合の第一候補とする。ArchaludonとGreat Tusk/Crustleのholdout回帰をlive監視項目に含める。

### Cynthia v12: main-line to support-line search pivot

The live v9 submission recovered to 12 public games, 7-5, and 617.35. The two
latest wins were Dragapult and Mega Lucario. Both formed Garchomp plus
Roserade support, so the next change targets the intended board route rather
than one loss bucket.

v12 retains all v11 Poffin setup rules. Only `TO_HAND` selection changes: once
two Gible/Gabite/Garchomp-ex bodies are already in play, search prefers
Roserade when Roselia can evolve, otherwise Roselia while support width is
below two. `LOOK`, `TO_DECK`, and `TO_DECK_BOTTOM` explicitly keep v11 scores.

- Development seed 202643000: v11 365 -> v12 373/720, +8.
- Unused holdout seed 202663000: 240 -> 240/480, neutral.
- Combined: +8/1200; controls exact, action errors 0, max-step 0.
- Archaludon improved +6 combined, Dragapult +3, and Mega Lucario +2.
- Exact Cynthia was -4 in development and neutral in holdout. Great
  Tusk/Crustle and Ogerpon were each -2 combined and remain live watch items.
- Four changed decisions across Gold episodes 85023189 and 85023194 matched
  the recorded support-search action. Episode 85023208 was unchanged.

Evidence is under `analysis_outputs/cynthia_v12_evaluation`. The packaged
candidate is
`candidate_cynthia_garchomp_nasuo445_v12_support_pivot_20260714.tar.gz`,
SHA256 `B52DA76B3860299A3F34F4DCFB2E400FC287C33E0776E507BF8EC46559E17B65`.
It has 13 main-first members, 60 deck rows, normal import, no-`__file__`
execution, and a 10-game archive smoke with zero errors. Keep v9 active while
it is recovering; v12 is the next-reset candidate only if the mature live
score remains weak.

### Cynthia v13: finish development before Corkscrew

The live v9 submission later reached 21 public games at 9-12 and 549.44. An
earlier 1-3 window contained losses to Marnie, Alakazam, and Hop/Trevenant;
the latest five then went 1-4 against Mega Lucario twice, Starmie, Dragapult,
and an unknown deck. Execution remained COMPLETE. v11/v12 already change the
Poffin setup in the Alakazam and Hop losses; the Marnie loss is unchanged. No
new one-matchup patch was added.

The remaining repeated Gold mismatch is turn ordering. In 11 states across
episodes 85023189 and 85023194, v12 ends the turn with Corkscrew Dive before
positive PLAY, EVOLVE, ATTACH, ABILITY, or RETREAT actions. v13 retains every
v12 setup/search rule and, only with active Garchomp ex plus Roserade support,
orders the best positive development action ahead of non-final-prize
Corkscrew. Normal scoring resumes after the state update.

- Development seed 202643000: v12 373 -> v13 402/720, +29.
- Untouched blind seed 202683000: 261 -> 276/480, +15.
- Combined: +44/1200; gains/loss flips 83/39, both seats positive, duplicate
  controls exact, action errors 0, max-step 0.
- Exact Cynthia improved +11 combined, Alakazam +7, combined Starmie +23, and
  Mega Lucario +4. Great Tusk was -2 combined, Ogerpon -2, while Marnie and
  Archaludon effects changed sign across seeds and remain live watch items.
- An independent 160-game route trace scored v12 84 -> v13 95. v13 reached
  first evolution, attack, and prize earlier on average and had a wider line
  at first attack. Corkscrew use fell 1335 -> 1028 while Draconic Buster rose
  282 -> 453, supporting conversion from draw attack to completed main attack.

Evidence is under `analysis_outputs/cynthia_v13_evaluation` and
`analysis_outputs/cynthia_v13_route_trace_202693000_py311`. The initial trace
attempt using the system Python is invalid due to a Python-version error and
must not be cited.

Packaged candidate:
`candidate_cynthia_garchomp_nasuo445_v13_corkscrew_development_order_20260714.tar.gz`,
SHA256 `97E9092DC7387BABE564E5573DBA2DEB18183D608C683113B5AE769A18B659C7`.
It has 13 main-first members, 60 cards, normal import, no-`__file__` execution,
and a 10-game archive smoke with zero errors. The pre-submit hypothesis is
that completing the public board route before the turn-ending draw attack
improves Cynthia, Alakazam, Starmie, and Lucario conversion. Monitor Great
Tusk, Ogerpon, Marnie, and Archaludon. Submit only after the next quota reset
if a final fresh check does not materially overturn the now-mature weak result.

#### v13 gain/loss boundary

The paired flip audit does not support reducing this policy to "always set up
before attacking." The change wins and loses through the same visible
mechanism. Of 39 loss flips, 38 first diverged at the Corkscrew guard and 19
deferred an immediate KO. However, six of eleven representative gain retraces
also deferred an immediate KO. Those gains were distributed across multiple
matchups and development actions.

No v14 narrowing is accepted without a public-state separator that preserves
both broad-panel totals and the positive immediate-KO deferrals. In live
evaluation, measure the complete policy rather than only the win-plan metric:

- Gible/Gabite/Garchomp and Roselia/Roserade establishment;
- Power Weight, energy, hand, deck, and recovery-resource use;
- first attack, first prize, prize-race conversion, and attack continuity;
- Corkscrew versus Draconic Buster timing;
- Great Tusk deck-out pressure and Marnie prize pressure;
- matchup spread and repeated legal-choice errors.

v13 is frozen for the next reset. A later v14 must improve a repeated failure
condition without converting any established gain bucket into a regression.

#### Late low-deck audit after live Kangaskhan loss

Episode 85688629 exposes a genuine late-timing failure signature: with a full
board, v13 would defer the recorded Corkscrew at turns 31, 33, 35, 39, 41,
and 43 while the remaining deck falls to single digits. This does not justify
an exception by itself.

The exact-seed audit contains 1,483 v13 Corkscrew deferrals across all 83 gain
and 39 loss flips. A turn-31/full-bench/deck-at-most-eight gate touches one
gain and two losses, but has not counterfactually recovered either loss. The
live-aligned non-KO variant touches gains and no paired loss. Full bench and
immediate-KO rates are almost identical across gain-side and loss-side
decisions.

The adjacent matchup checks also reject a Kangaskhan-wide rollback:

- broad Dung policy/deck: v12 296 -> v13 299/400;
- Dung policy with exact DapperOctopus 60 cards: 146 -> 155/240;
- exact-deck seat deltas: +4 and +5, duplicate controls exact.

Keep v13 unchanged. A late gate requires zero touched gain flips, at least two
recovered paired losses, no complete-suite loss, and corrected live actions
without disturbing earlier development.

#### Pre-submit live exposure and comparison baseline

An audit of all 27 current v9 public games gives 1,674 agent decisions. v13
changes 86 decisions in 22 games, so it is not a low-exposure patch:

- MAIN: 44, all recorded Corkscrew decisions reordered to development;
- TO_BENCH: 25, primarily additional Gible width and Roselia support roles;
- TO_HAND: 17, main-line-to-support search pivots;
- early/mid/late: 20/24/42 changes.

Matchup exposure is intentionally asymmetric. Both Alakazam games change
setup/search but have zero Corkscrew deferrals. Marnie is completely
unchanged. Ogerpon has 10 deferrals over two games, Hop 11, Mega Lucario 8,
Cynthia 9, and Kangaskhan 6. These are attribution labels, not automatic
accept/reject rules.

The submitted v9 process baseline is:

- 21/27 games reach at least three tracked line bodies at first attack;
- 17/27 reach that width by first prize;
- Power Weight reaches Garchomp in 17/27;
- Poffin is used in 19/27 and has 52.6% win rate versus 25.0% without it;
- wide first attacks win 47.6%, thin first attacks 33.3%;
- median missed attack turns after first attack is zero.

Judge v13 on score and the complete rule policy. Desired evidence is wider or
no-worse setup, maintained resources and attack continuity, more conversion
to Draconic Buster, and no concentrated collapse in the timing-exposed
matchups. Do not promote it solely because board-width metrics rise, and do
not reject it solely because a single deferred Corkscrew loses.

### Cynthia human-strategy audit and resource-allocation hypothesis

The initial Cynthia iterations were derived mainly from the exact Gold
replays and local paired games. That recovered real sequencing rules, but it
did not begin from a systematic human deck-theory specification. A separate
audit now cross-checks three sources:

- the current Pokecardlab strategy guide
  (`https://pokecardlab.com/2026/06/27/2026062801/`);
- the Pokebeach Cynthia/Garchomp deck discussion
  (`https://www.pokebeach.com/2025/06/cynthias-garchomp-boom-or-bust`);
- the official example deck
  (`https://www.pokemon-card.com/deck/result.html/deckID/84cGDK-jbpBrY-848c8D`).

Only claims consistent with the local engine implementation and the four
exact nasuo445 Gold replays are promoted to agent requirements. The resulting
phase plan is:

1. Open with two or three Gible and one or two Roselia when legal. Keep Gabite
   as a repeatable Champion's Call engine instead of treating every copy as a
   disposable evolution step.
2. Form one Garchomp ex while retaining enough Gabite/Gible width for a second
   attacker. Bring Roserade online as both a damage-breakpoint support and a
   fallback attacker.
3. Use Corkscrew Dive as the normal midgame tempo/draw attack. Complete useful
   development before the turn-ending attack, but continue to judge setup,
   resources, prize tempo, and matchup safety together.
4. Allocate Power Weight and Rock Fighting Energy to the Garchomp lane that is
   expected to survive, and preload a bench Garchomp/Gabite before the active
   attacker falls.
5. Use Draconic Buster for a KO or prize-map conversion when discarding all
   attached Energy will not strand the board. It is not a default attack merely
   because two Energy are attached.

v13 implements steps 1-3 through Champion's Call ordering, Gabite width,
Poffin role selection, Roserade support pivot, and development before
Corkscrew. It does not yet implement steps 4-5 correctly: Basic Fighting and
Rock Fighting have identical attachment/search scores, Power Weight uses only
static card-class scores, attachment is not active/bench role-aware, and
Draconic Buster starts at a constant score of 18,500 even without a KO.

Three attempted Corkscrew score-threshold variants are rejected. Threshold
5,000 and 4,000 lost 9 and 10 wins respectively on the 720-game development
panel. Threshold 3,000 gained 4/720 in development but lost 5/480 on untouched
blind seed 202683000, with both seats negative and 11 regressions versus six
gains. The failure is evidence against further one-dimensional attack-score
tuning, not against the broader deck theory.

Submission 54630859 remains COMPLETE but mature weak at 33 public games,
14-19, score 549.2219. Its latest four games were loss, win, win, loss, so the
result is not recovering. All July 13 submission slots are already used.

The next isolated experiment is v17 resource allocation. It may distinguish
Rock from Basic Energy and prioritize an unready bench main-line attacker only
after the active Garchomp is attack-ready. It must not change deck contents,
attack scoring, setup/search rules, matchup guards, Power Weight, or Spiritomb.
Promotion requires no aggregate loss on both the 720-game development panel
and the 480-game blind panel, no meaningful seat or adjacent-bucket collapse,
exact duplicate controls, and zero action errors/max-step games. If v17 fails,
the next isolated theory test is a breakpoint-aware Draconic Buster conversion
gate rather than another Corkscrew threshold.

#### v17 Rock and backup allocation evaluation

v17 implements only the approved resource-allocation surface. Rock Fighting
gets a small same-lane tie-break when a Gible/Gabite/Garchomp lacks Rock. An
unready active Garchomp is completed before resources move to the bench; once
it has two Energy, the next unready bench Garchomp, Gabite, then Gible is
preferred. TO_HAND prefers Rock only when a visible main-line target lacks it
and a Basic-Energy route remains visible or already in hand.

The exact deck remains byte-identical at 60 cards. The four Gold replays have
324 decisions. v13 had 145 mismatches and v17 has 141. The four newly matched
actions are exactly the intended resource decisions: Rock attachment to Gible
in 85023167, Rock search and later active-Garchomp allocation in 85023189, and
Rock attachment to Gabite in 85023194. No previously matched Gold decision was
lost.

Fixed-seed evaluation against v13:

- development 202643000: 402 -> 416/720, +14, paired gains/losses 44/30;
- blind 202683000: 276 -> 282/480, +6, paired gains/losses 30/24;
- unused holdout 202733000: 272 -> 275/480, +3, paired gains/losses 24/21.

All three panels have exact duplicate controls and zero action errors or
max-step games. The combined result is +23/1,680. The blind seat-0 result was
-4, but the unused holdout was neutral for that seat, so the seat regression
did not reproduce. Mega Lucario remains a real watch bucket: +1 in development,
-3 blind, and -2 holdout. A bounded exact-seed diagnosis is required before
adding any matchup exception or removing a component.

Compared with the submitted v9 policy, v17 changes 45 of 1,942 decisions over
32 public replays: 29 newly different MAIN decisions, 13 TO_HAND decisions,
and three states where both policies already differed but chose different
actions. This is broad enough to evaluate as a policy probe, not a cosmetic
tie-break.

Packaged candidate:
`candidate_cynthia_garchomp_nasuo445_v17_rock_backup_allocation_20260714.tar.gz`,
SHA256 `3756036C39C79CD2C9ED483B94FF236FA0BE74FD1B939DB666AFB2DD71D41E80`.
It has 13 main-first members, exact extracted source/deck hashes, normal import,
no-`__file__` execution, and a 10-game Mega Lucario archive smoke with zero
errors/max-step games. v17 supersedes v13 as the provisional next-reset probe,
subject to the in-progress Mega Lucario component diagnosis.

#### v18-v21 Rock component ablation and final selection

The Mega Lucario warning was decomposed before accepting an exception. v18
removed only the active-ready bench override and fell from the v13 baseline of
106 to 102/140 on the fixed Mega Lucario gate. v19 also removed the
active-unready Garchomp completion override. It recovered two of three known
losses and retained all three known gains, but finished 105/140, one below
v13. These variants are rejected.

v20 and v21 replaced replay-shaped conditions with a deck-theory condition:
Rock is preferred only when Garchomp is already in play, or when a Gabite can
be evolved immediately by a Garchomp already in hand, and never when the
Active is a damaged Garchomp. v21 applied the same readiness gate to both
search and attachment. Both tied v13 at 106/140 in the targeted panel, but
only removed two of four known regressions.

The full v21 distribution test was 402 -> 409/720 development, 276 -> 276/480
blind, and 272 -> 268/480 unused holdout. The combined gain was only +3/1,680,
the holdout failed by four, and Archaludon repeated a -2 regression in both
blind and holdout. Gold disagreement moved only 145 -> 144/324 and live-v9
exposure was 110/1,942 decisions. v20-v21 therefore do not replace v17.

The live v9 submission later reached 34 public games at 16-18 and 565.8767
after two wins. This is still a mature below-Bronze result, not enough recovery
to overturn the next-reset replacement plan. v17 remains the selected probe:
it is the only resource candidate nonnegative on all three broad panels and is
+23/1,680 overall. The next isolated Cynthia theory experiment is a
breakpoint-aware Draconic Buster conversion rule using immediate KO/prize
value and post-discard attack continuity; do not add another Rock or
Mega-Lucario-specific patch first.

#### v22 Draconic Buster conversion promotion

The engine and 38 replay audit exposed a structural attack-scoring error.
Corkscrew Dive does 100 damage and may draw to six cards; Draconic Buster does
260 and discards every Energy from the Active. v17 nevertheless gave Buster a
constant 18,500 base score, so it selected Buster in 40 of 41 audited states
where both attacks were legal. Those states included all 17 where Corkscrew
already KOed and seven of eight where Buster did not KO. Only three recorded
actions used Buster, and all three were KOs.

v22 keeps the complete v17 policy and changes only this attack comparison.
Buster is approved when it is a visible Buster-only KO and the KO wins by
prizes or board clear, takes at least two prizes, or leaves an Energy-loaded
bench Garchomp/Gabite/Gible. Otherwise it is ranked one point below the
current Corkscrew base score. No opponent identity, matchup, turn, or target
card id is used.

The exact 41-state replay gate reconstructed every observation without error:
13 conversion states selected Buster 13/13; 28 rejected states selected Buster
0/28, with five Corkscrew and 23 unchanged development actions. Gold replay
agreement remains 141 mismatches over 324 decisions, equal to v17.

Paired full-distribution results versus v17:

- development 202643000: 416 -> 436/720, +20;
- blind 202683000: 282 -> 308/480, +26;
- unused holdout 202733000: 275 -> 283/480, +8;
- combined: 973 -> 1,027/1,680, +54, paired gains/losses 112/58.

Both seats improved in every panel. Every matchup was nonnegative in the
combined result; holdout Alakazam and Archaludon negatives did not repeat and
remain +9 and +4 overall. Duplicate controls were exact and there were zero
action errors or max-step games.

Packaged candidate:
`candidate_cynthia_garchomp_nasuo445_v22_buster_conversion_20260714.tar.gz`,
SHA256 `2644BD391D286A16414083244A4DE3E2F9B40A1D4D321B7C6009037F81C912C3`.
It has 13 main-first members, exact source/deck extraction, 60 cards, normal
import, no-`__file__` execution, and a 10-game Mega Lucario archive smoke at
8-2 with zero errors/max-step. v22 supersedes v17 as the next-reset probe;
v17 is the rollback.

#### v22 independent-seed and process confirmation

An additional unused seed, 202807131, was evaluated after the package was
frozen. Across the same 12-opponent population at 20 games per seat, v17
scored 279/480 and v22 scored 302/480, a +23 delta. Seat deltas were +11 and
+12. Eight matchups improved, Mega Lucario and Ogerpon were neutral, and the
only negatives were Starmie expanded -1 and Marnie Sota -2. Duplicate
controls were exact and all reports were valid. This fourth broad panel is
independent of the development, blind, and holdout seeds used for selection.

A separate 80-game, eight-opponent trace at seed 202813071 measured the
mechanism rather than only terminal wins. Relative to v17, v22 changed:

- wins: 35 -> 43;
- total attacks: 799 -> 836;
- missed attack turns after the first attack: 87 -> 67;
- Draconic Buster uses: 274 -> 138;
- Corkscrew Dive uses: 335 -> 504;
- mean first-attack turn: 6.55 -> 6.475;
- mean main-line bodies at first attack: 2.45 -> 2.475.

The unchanged first-attack timing and line width show that v22 is not merely
changing setup speed. It preserves the already selected board-formation
policy, reduces unnecessary all-Energy discards, and converts that saved
resource into more continuous attacks. The current live v9 reference reached
35 public games, 17-18, and 572.3024 after three consecutive wins. That is a
small recovery but remains a mature below-Bronze baseline; the quota is
exhausted, so no replacement is made before the expected next reset.

#### v22 live-state exposure and reproducible gate audit

The 35 public games contain 2,160 target decisions. The submitted v9
reconstructs exactly at 2,160/2,160. v17 changes 146 decisions in that fixed
observation corpus; v22 changes 173. Direct v17-v22 comparison isolates 27
differences over 19 episodes, and every difference replaces a v17 Buster:
five with Corkscrew, nine with a card play, eight with an attachment, and five
with an ability. There are no unrelated action changes between v17 and v22.

`tools/audit_cynthia_buster_replays.py` now makes this check reproducible. On
all 35 public replays it finds 41 states where both attacks are legal. v17
chooses Buster in 40 and no attack in one. v22 approves and chooses Buster in
exactly 13 states, chooses Corkscrew in five, and continues development in 23.
The state classes are 17 Corkscrew-also-KO, eight non-KO Buster, eight
Buster-only one-prize KO, seven Buster-only multi-prize KO, and one
game-winning KO. All seven multi-prize and the game-winning state are
approved; five of eight one-prize states are approved because a loaded backup
is visible. Unsafe candidate Buster count is zero.

The current live matchup record is Mega Lucario 5-3, Alakazam 3-2, Marnie
2-1, Dragapult 2-1, Starmie 1-3, Ogerpon 0-3, and smaller buckets. This is
used as a post-submit observation plan, not as a reason for a new exact-loss
patch. v22 already improves the broad Starmie populations and leaves Ogerpon
neutral locally; live results must determine whether either bucket needs a
future deck-level or general-policy change.

#### Exact live-deck safety and archetype correction

The apparent Ogerpon 0-3 bucket was a classifier artifact. The three decks
were unrelated shells containing only one generic Ogerpon marker: a
Crustle/Munkidori control deck, Cubchoo/Articuno control, and Teal Ogerpon/
Clefairy/Crustle. Reclassification of all 35 games shows only Starmie as a
repeated weak family at 1-3. The other control losses are one game each:
Crustle/Munkidori, Cubchoo/Articuno, Kangaskhan/Crustle, Teal Ogerpon/
Clefairy/Crustle, pure Crustle, Archaludon, and one unclassified deck.

`tools/extract_episode_decks.py` now uses required-card hierarchy for these
shells instead of partial marker ties. Kangaskhan and Great Tusk are checked
first, followed by the exact compound shells and then generic Crustle. Tests
cover the three new shells, generic Ogerpon, Kangaskhan, Great Tusk, pure
Crustle, and the single-marker false-positive case.

Nine exact 60-card live opponents were materialized with the nearest available
public rule policy. This measures deck-list safety under a fixed policy proxy;
it does not claim to clone each opponent's hidden policy. Across seeds
202817313 and 202827313, the first seven variants scored v17 283 -> v22
302/560, +19. Dapper Kangaskhan/Crustle was neutral over 80. Pure Crustle was
0, -3, then +3 over three seeds and finished 12-12/140. Final exact-list total:
305 -> 324/780, +19. Every individual deck style is nonnegative after its
confirmation seeds, duplicate controls are exact, and all reports are valid.
This strengthens the v22 submission case without adding a matchup exception.

#### Strong local-policy panel

The exact-list panel still used deliberately simple nearest-policy proxies, so
v22 was also tested against six of the strongest runnable local policies: the
historical Archaludon peak, the Shumpei Gold-copy Archaludon, MPGaming
Kangaskhan/Crustle v23, two independently developed Marnie styles, and a v22
Cynthia mirror. At seed 202857313, v17 scored 159 and v22 scored 163/360
(+4). The per-opponent deltas were +4, -3, +2, +2, -1, and 0 respectively;
duplicate controls were exact and all reports were valid.

The two negative buckets were repeated at unused seed 202867313. Shumpei
reversed from -3 to +6 (18 -> 24/60), while Marnie Kazuki was neutral
(38 -> 38/60). Across both seeds for those two styles, their combined result
is v17 130 -> v22 132/240 (+2). This removes the apparent repeated regression
and keeps v22 selected unchanged. These are materially stronger local
opponent policies than the earlier proxy panel, but they remain local
implementations and are not evidence that Kaggle opponents' hidden policies
have been cloned.

#### v23 all-Call-before-evolution sequencing

The remaining 141/324 exact-Gold mismatches in v22 were classified before
writing another rule. The largest reusable category was evolution and board
development order (54 states), followed by Energy/tool allocation (32),
search target choice (18), Roserade/support timing (12), trainer/stadium
sequencing (11), promotion/target conversion (6), attack timing (3), discard
(2), and other setup (3). Gold actions are treated as proposals rather than
labels: three of the four source replays are losses.

One repeated public-state pattern survived that caution. v22 protected a
Champion's Call only when it belonged to the same Gabite being evolved. The
Gold policy repeatedly used every currently legal free Call before evolving a
different Gabite. v23 therefore changes only the relative order between a
legal Champion's Call and a Garchomp-ex-on-Gabite evolution. Higher-scored KO,
attack, attachment, trainer, retreat, and other development actions remain
ahead; unrelated evolutions are unchanged. This is intentionally narrower
than the rejected global-Call-priority v2.

On the four exact Gold replays, mismatches fell 141 -> 133/324. There were ten
v22/v23 differences: eight changed an evolution to the recorded Call, while
the other two changed ordering inside states that were already mismatches. No
previously matching recorded action was lost. Across the 35 submitted-v9
public games, v23 differs from v22 in only 11/2,160 decisions over ten games,
and every difference is Garchomp evolution -> Champion's Call. This is an
exposure measurement, not an outcome label.

Paired safety results versus v22 are deliberately reported even though the
effect is small:

- historical Great Tusk regression gate: 37 -> 38/400;
- historical Mega Lucario regression gate: 62 -> 62/80;
- 12-opponent development seed 202643000: 436 -> 434/720;
- unused 12-opponent seed 202907313: 286 -> 287/480;
- six strong local policies: 163 -> 167/360;
- nine exact live 60-card decks with fixed policy proxies: 159 -> 160/360.

The two broad seeds total 722 -> 721/1,200 (-1), while all six gates total
1,143 -> 1,148/2,400 (+5). Duplicate controls are exact and there are zero
action errors or max-step games. The broad result is effectively neutral, so
v23 is not claimed as a large local win-rate improvement. It is promoted
because it fixes a repeated deck-theory sequencing defect, improves Gold
agreement without breaking an existing agreement, is positive against the
strong-policy and exact-live panels, and has no reproduced broad collapse.

Packaged candidate:
`candidate_cynthia_garchomp_nasuo445_v23_allcall_before_evolve_20260714.tar.gz`,
SHA256 `C8AD5F9BA979EA7A28732DB516C8B0681D310E3924319D08379C67E0C628CCD1`.
It contains the exact Gold 60 cards and 13 main-first members. Five focused
unit tests, `py_compile`, archive import/source equality, and a five-game
Mega Lucario smoke all pass with zero errors. v23 supersedes v22 as the next
reset live probe; v22 remains the rollback. Live success is not inferred from
these local results.

#### v24-v28 opening-width ablation and rejection

The remaining Energy/tool mismatch class suggested a general opening rule:
before the first Rock Fighting Energy or Power Weight, establish a second
main-line body or play an available width/search card. v24 limited this rule
to turns 1-2, fewer than two Gible/Gabite/Garchomp bodies, and no Energy on
the current main line. Basic Fighting Energy and all unrelated actions were
left unchanged.

v24 improved exact Gold mismatch 133 -> 130/324 without losing a previous
exact action. It scored +5/720 on the development panel, +1/360 against six
strong policies, and +7/480 on an unused broad seed. However, an exact-live
60-card panel was -2/360 and a two-bucket confirmation was -1/240. The
regression repeatedly appeared as player 1 against pure Crustle control.

The two observed flips were traced to turn-2 resource choices under visible
Dwebble/Crustle pressure. Three safety variants were tested rather than
accepting an exact-seed patch: energized evolved Active (v25), any energized
Active (v26), and visible Dwebble/Crustle plus opposing Energy (v27). They
either failed to cover both states or were too broad. v28 disabled the width
rule whenever visible card 344/345 identified the Crustle line. It restored
the two known seeds and preserved 130/324 Gold mismatch, but a fresh 1,080-
game gate scored 487 -> 486: broad 0/480, strong 0/360, and exact Crustle
-1/240. All reports had exact duplicate controls and zero action/max-step
errors.

Therefore v24-v28 are rejected. The useful finding is structural: early
width before special durability resources is promising mainly when playing
second, but current public state is insufficient to distinguish the states
where the delay is beneficial from Crustle-control states where it is not.
v23 remains the selected next-reset probe and v22 remains rollback.

#### v29-v31 damaged-Active rotation ablation

The local runner now records Active and Bench HP, Energy, and Tool state, and
`tools/audit_cynthia_local_rotation.py` identifies public-state rotation
windows. The initial hypothesis was that a damaged, loaded Garchomp should
rotate into an Energy-ready backup before being lost. v29 used a 200-damage
threshold and regressed by two games across broad and strong panels. v30 used
300 damage or four Active Energy and finished +1/1,080. v31 vetoed rotation
when Corkscrew immediately KOd the Active opponent, but this also removed the
only Archaludon gain. The effect was too small and unstable to justify another
hand rule, so v29-v31 are rejected. The telemetry is retained for later
rollout/value learning, where future attack continuity can be evaluated rather
than inferred from one threshold.

#### v35 reliable development before attack

The next experiment began from the deck's intended flow, not one replay loss.
In the submitted-v9 Starmie/Froslass games, all three losses reached attack
turns without a charged backup; the sole win established two Garchomp and two
Roserade. Exact Gold history was mixed (four supporting and three contradicting
windows), so a generic "always develop before attacking" rule was rejected.

v35 applies only when the Active is Garchomp ex with exactly one Energy, the
opponent has a Bench, no benched Garchomp is Energy-ready, and the current best
attack is not an immediate Active KO. It then ranks the following guaranteed
public-state actions ahead of that attack:

1. attach Energy to a benched Gible, Gabite, or Garchomp;
2. evolve a benched Gible or Gabite;
3. use Night Stretcher when Gible is in the discard and Bench space exists;
4. use Fighting Gong only when the Bench is empty and own prizes are four or
   five.

Direct Gible and Poffin are deliberately excluded from the forced overlay
because their broad flip attribution contained losses; the inherited v23
policy can still choose them normally. Immediate-KO attacks, Champion's Call
ordering, selective Buster conversion, role-aware Energy/Tool allocation,
matchup guards, and every unrelated score remain inherited from v23.

The final gate covers 3,000 paired games. Development gates improved 1,037 ->
1,046/1,920 (+9): exact-live +2/360, broad +2/720, strong +2/360, and unused
broad holdout +3/480. Blind gates improved 547 -> 549/1,080 (+2): broad
+1/480, strong +1/240, exact-live 0/360. There was no negative opponent bucket,
seat collapse, action error, or max-step game. Across all gates v23 scored
1,584 and v35 scored 1,595 (+11).

The pre-submit hypothesis is that a guaranteed one-action investment before a
non-winning attack increases next-turn attack continuity and prevents board
collapse across Starmie, Cynthia, Mega Lucario, and mixed Gold-list opponents.
The main risk is surrendering useful tempo against control or a hidden race;
live analysis must therefore compare first attack, missed post-first-attack
turns, backup readiness, and board-clear losses. Roll back to v23 if live
results show earlier development without increased subsequent attacks.

Packaged candidate:
`candidate_cynthia_garchomp_nasuo445_v35_reliable_development_before_attack_20260714.tar.gz`,
SHA256 `E691A08AC140EC7D91733BC7D70D381D3064742F0ED41F19CB524071B9ED2FA7`.
It contains the exact Gold 60 cards and 13 members. `main.py` and `deck.csv`
match the source hashes, compile/import/no-`__file__` checks pass, and the
archive matches source outcomes in a two-seat 10-game smoke with zero errors.
Fifteen focused v34/v35 tests pass. v23 remains the explicit rollback package.

The live replacement condition is satisfied independently of the local gain:
submission 54630859 is COMPLETE at 559.1698 after 40 public games (18-22) as
of 2026-07-13 20:30 JST. It is below Bronze and not recovering. The latest
loss is Hop/Trevenant episode 85732359, while the repeated severe family is
Starmie/Froslass at 1-4. Do not add a one-game Hop patch before the v35 probe;
the selected change targets general attack continuity and already passed the
broad, strong-policy, exact-list, and blind gates.

A public-snapshot replay attribution limits the claim further. In the five
Starmie/Froslass games, v35 changes exactly one of 250 reconstructable v23
decisions: episode 85682411 step 56, where it retrieves Gible with Night
Stretcher before a non-KO Corkscrew attack. That is the intended mechanism,
but it is not a counterfactual proof of a win. The other four games are
unchanged; two losses fail to establish an eligible Garchomp/backup state at
all. In latest Hop/Trevenant loss 85732359, v35 and v23 are identical at all
49 reconstructable decisions because Garchomp ex never becomes Active. This
supports submitting v35 as a narrow general sequencing probe while keeping
earlier main-line formation as a separate future hypothesis.

#### v36 Starmie direct-Gible order ablation

The two Starmie losses that never reached a v35 trigger were examined for the
earliest legal main-line action. Episode 85688147 contained no skipped direct
development. Episode 85679036 contained one turn-2 order difference: with an
Active Gible, empty Bench, Rock Energy, Poffin, and a second Gible available,
v35 selected Rock attachment before direct Gible. It nevertheless used Poffin
and benched that same Gible later in the main phase, so this was not yet a
turn-boundary development failure.

v36 ranked the direct Gible exactly one point above an otherwise selected
Energy attachment only on turns 1-2, against publicly visible Staryu or Mega
Starmie, with exactly one own main-line body. Seven focused tests cover the
positive state and Crustle, no-marker, late-turn, two-body, and non-attachment
negatives. The deck is byte-identical to v35.

The exposed sequential panel gave 36 -> 37/64 against four exact Starmie lists,
including one reproducible loss-to-win seed. Documented Crustle seeds and a
fresh Crustle panel were exact, and a 480-game broad panel was 326-326. This
was not enough to promote: an unused-seed blind Starmie panel scored 426 ->
425/600, with no game flip or measurable end-turn-2 readiness difference.
The single negative exact bucket was neutral 71-71 on a second 120-game seed.

Reject v36. The earlier +1 was an exposed trajectory effect, not a repeated
population gain. The actionable distinction is that same-turn Gible play order
does not solve missing Gabite/evolution timing or survival. Any future early
readiness candidate must improve the later evolution route in sequential blind
games, not merely move an already-selected Gible action earlier.

#### v37-v39 Poke Pad and Gible-target ablation

The 133/324 remaining Gold mismatches were revisited by semantic class rather
than copied as labels. Search/support actions account for 48 overlap-aware
mismatches; 44 occur in Gold losses and only four in the sole Gold win. The
repeated testable cluster was early Poke Pad into Gible in episodes 85023189
and 85023208. Actual replay observations carry the acting-player-public source
marker `select.effect.id == 1152`, so Poke Pad resolution can be identified
without module state, hidden order, or raw option indices. Episode 85023194
turn 3 is a useful full-board negative control.

v37 changed two parts together: play Poke Pad one point above an otherwise
selected Energy attachment on turns 1-2 with fewer than three main-line bodies,
then choose Gible one point above Gabite in the marked Poke Pad resolution.
The intended eight Gold decisions changed and the win control stayed exact.
Paired development gates were +11/720 broad, +4/360 strong, and +8/360
exact-live, for +23/1,440. The first negative cells did not generally repeat:
Cynthia-v23 was +9/120 and exact Starmie was +5/120 on unused seeds. The rule
was therefore decomposed rather than discarded from a single seed.

v38 retained only main-action priority and scored -3/1,440. v39 retained only
the marked Gible-over-Gabite target and scored +22/1,440: +3 broad, +12 strong,
and +7 exact-live. v39 did not change Poke Pad play frequency materially; it
changed 629 baseline Gabite targets toward 417 Gible and 288 Gabite targets in
the development corpus. This identifies target choice, not early trainer order,
as the source of the aggregate gain.

Safety confirmation prevents promotion. The initial Archaludon player-0 cell
was -3/30, then repeated at -3/180 over two unused seeds, for -6/210 combined.
Other negative cells reversed or became bounded: exact 85688147 +6/180,
Marnie TW +1/120, exact 85691988 +4/120, and a fresh broad player-0 population
+2/360. Overall v39 evidence is +32/2,400, but that does not justify accepting
a repeated adjacent Archaludon regression.

State attribution found six beneficial and nine harmful marked target shifts
against Archaludon. Public board shape, main-line width, hand/deck counts,
Energy, and turn measurements were nearly identical. No evidence-backed guard
can retain the gain while removing the loss; matchup identity is not a valid
policy feature by itself. Therefore v37-v39 are rejected and no blind promotion
panel is run. This is a useful negative result: a broad average can improve
substantially while a semantically coherent target rule remains unsafe in one
adjacent policy population.

The parallel Roserade audit found six states where Gold evolved Roserade before
Champion's Call, but five are from losing replays and no public discriminator
separates an immediate damage-breakpoint need from ordinary free-search order.
That rule is not implemented. v35 remains the selected next-reset candidate.

#### v40-v41 exposed-Gible Poke Pad ablation

The five live Starmie/Froslass games were re-audited before adding another
matchup patch. Episodes 85679036 and 85682411 exposed an older Gible with no
Gabite in hand while Poke Pad was legal before the opponent's next attack. The
bucket win 85680524 used Poke Pad into Gabite and Champion's Call. However,
85688147 and 85712701 already established Garchomp by turn 5 and still lost,
so early Gabite access cannot explain the whole 1-4 bucket.

v40 used only acting-player-public state: MAIN context, an in-play Gible with
`appearThisTurn == false`, no Gabite in hand, legal Poke Pad, no immediate KO,
and a low-value inherited action. It did not override the Poke Pad target.
Without a turn bound it also changed eight late decisions in Crustle episode
85678570, so it failed the stage-0 narrow-exposure gate.

v41 added `turn <= 3` and eliminated every Crustle difference while retaining
three semantic Starmie trigger windows. Paired results versus v35 were:

- Starmie/Froslass: 334 -> 339/600, +5;
- broad: 449 -> 454/720, +5;
- six strong policies: 161 -> 162/360, +1;
- exact-live: 179 -> 178/360, -1;
- exact 85682411 confirmation: 76 -> 77/120, +1;
- Archaludon safety: 162 -> 158/420, -4;
- independent Archaludon confirmation: 153 -> 151/420, -2.

The Archaludon regression pooled to 315 -> 309/840 (-6) and affected both
seats across the two schedules. Across all 3,000 executed games v41 was only
+5. Duplicate controls were exact, with zero action errors and max-step games.
Blind panels were skipped. This is the second independent demonstration that
a semantically plausible Gible-over-tempo rule can improve Starmie and broad
averages while damaging Archaludon. Reject v40-v41; keep v35 selected.

The semantically combined Crustle/control losses were also audited separately.
Three of four games formed meaningful Garchomp/Roserade or early prize lines,
but one-prize Crustle repeatedly traded into two-prize Garchomp. No repeated
Boss, Energy, Power Weight, Roserade, or Spiritomb error appeared in at least
two games. The narrow unbacked one-prize Buster leak in two v9 states is
already prevented by v35's selective-Buster gate, so no duplicate control
patch is added.

#### Root absolute-strength audit: v35 submission suspended

The planned automatic v35 submission is suspended after a root-level audit of
absolute performance and opponent-policy fidelity. On identical strong,
exact-live9, and broad schedules, total results were v9 584/1,440, v22
720/1,440, v23 728/1,440, and v35 734/1,440. v35's strong and exact-live9
absolute rates are only 44.17% and 41.39%. Its incremental result over v23 is
six games, or 0.42 percentage points, and every candidate retains a 0% exact
bucket floor.

The exact-live9 label was also too strong. The nine proxies copy the observed
60-card lists, but reproduce only 273/506 recorded source-replay decisions
(53.95%). The range is 32.43% for Kangaskhan/Crustle to 78.00% for one
Starmie policy. This panel therefore measures exact decks under approximate
local policies, not the live opponent-policy distribution.

Gold action agreement is v9 168/324, v22 183/324, v23 191/324, and v35
191/324. Across all 22 live losses, v35 differs incrementally from v23 at only
three of 1,212 reconstructable decisions: one Starmie, one Crustle-control,
and one Alakazam decision. No counterfactual replay proves a bucket repair.

The deterministic evaluator also copied v35 `candidate_win` totals into its
v23 summary. Root verification of the raw `baseline_win` column corrected v23
from 734 to 728 wins. Command execution and schedule keys were valid; the
failure was evidence synthesis. Root verification of both columns is now a
mandatory gate.

Do not submit v35 at the next quota reset. Keep Cynthia as the active track,
rebuild style-specific Starmie, Kangaskhan/Crustle, and control opponent
policies from source replays, then repeat the absolute audit before selecting
another candidate. Full evidence and corrected statistics are in
`docs/cynthia_absolute_strength_audit_2026-07-14.md`.

#### v63 Crustle immunity conversion

The active deterministic path supersedes the obsolete proxy-rebuild paragraph
above. Live v58 losses exposed a direct card-mechanics error: Garchomp ex
attacked Active Crustle for zero through Mysterious Rock Inn while the exact
deck's Spiritomb could convert the damaged Garchomp on the Bench into lethal
Raging Curse damage.

v63 is a fail-closed, public-state sequence rather than a generic matchup
patch. It requires Active Crustle, a damaged Active Garchomp ex, a legal ready
or immediately ready Spiritomb, free retreat, and guaranteed lethal damage.
It forces only Spiritomb play/attachment, retreat, promotion, and the lethal
attack, revalidating every phase. No search, hidden information, opponent
identity, learned policy, or generic damage scorer changes.

On fixed both-seat schedules, MPGaming Kangaskhan/Crustle improved
`40->114/200` and an independently implemented Dung Crustle policy improved
`152->168/200`, with `90/0` combined paired gains/losses. Full traces
confirmed the exact approved route in all 90 gains. Historical-Silver
Archaludon was exactly `61->61/200`; five non-Crustle safety buckets were
also outcome-equivalent. Package and evidence details are in
`analysis_outputs/cynthia_v63_crustle_spiritomb_counter_20260714/RESULT.md`.

Kaggle submission `54673338` completed validation at `600.0` in episode
`85870909` with no execution error. Public evidence is not yet available.

#### v64 Boss same-turn conversion guard: rejected safety correction

Live v63 episodes `85872552` and `85874127` exposed the same scoring error:
the theoretical `Boss for KO` branch could fire while the Active Pokemon had
no payable attack. v64 added a public-state same-turn conversion certificate
for that branch while preserving ordinary Boss pressure and the v63 Crustle
route. It correctly repaired both reconstructed states and passed 17 focused
tests.

The correction was strategically unsafe. On the frozen historical-Silver
Archaludon schedule, exact v63 scored `61/200` and v64 scored `49/200`, with
paired gains/losses `4/16`. Both seats regressed (`-7/-5`) and all four
50-game blocks were negative (`-3/-4/-2/-3`). The exact McNemar p-value was
`0.0118179321`; schedule, controls, exits, action errors, and max-step checks
were clean.

Reject v64 and retain v63. A future Boss correction must be derived from the
traced discordant states and expose a narrower public discriminator. Do not
infer that removing every non-convertible theoretical KO is beneficial:
Boss may still have disruption, stall, or future-prize value. Full evidence is
in `analysis_outputs/cynthia_v64_boss_same_turn_conversion_guard_20260714/RESULT.md`.

Full paired traces sharpen the rejection: all 20 outcome flips began at the
Boss decision itself. Root parsing of the switch logs found 11 regression
targets were Duraludon `169` and five were Cinderace `666`; Full Metal Lab was
active in 12 regressions. v64 did not reveal one bad alternative action; its
various readiness, evolution, setup, and attack fallbacks all lost games that
v63 won after the Boss line. Any narrower correction must preserve these
future-prize, development, and disruption routes and cannot be justified by
same-turn damage alone.

The live examples also require matchup-level reasoning rather than an exact
target-card exception: root reconstruction found Froslass `104` in episode
`85872552` and Staryu `1030` in `85874127`. A subagent initially conflated the
two targets; this was rejected by direct replay inspection before strategy or
submission use.

## Cynthia: Energy is valuable only with certified conversion

The Fighting Gong readiness experiment separated a resource proxy from actual
conversion. Choosing and attaching Energy succeeded in every targeted state,
but produced no new wins and destroyed two early board-width wins. Therefore:

- do not prefer Energy over Gible merely because the Active main line is empty;
- do not retain later-turn or Active-Garchomp subsets without positive outcome
  evidence;
- use an attachment-order rule only when it certifies the complete immediate
  prize sequence, including typed attack cost, Boss target, damage/protection,
  and same-turn attack legality;
- preserve exact v63 behavior on uncertainty.

This is a general distinction between readiness and conversion: a successful
resource action is not a successful game-plan rule unless it advances a
verified attack or prize transaction without damaging board formation.

### Attach-before-Boss is not a missing transaction

The next audit tested the strongest possible version of that distinction. On
600 historical-Silver anchor games, 64 public states had Active Garchomp ex,
no current attack option, a legal Fighting attachment, a v63 `Boss for KO`
choice, and a visible one-Energy Corkscrew KO target. The states covered both
seats, all six 50-game blocks, 25 baseline wins, and 39 baseline losses.

Exact v63 already executed `Boss -> attach -> Corkscrew Dive KO` in all 64
states. Therefore attach-before-Boss is not a missing game-plan sequence. A
large number of losses containing a rule trigger does not establish that
changing the trigger would convert those games. The branch is rejected without
implementation, and no target-, seat-, block-, or outcome-specific subset is
retained. Full evidence is in
`analysis_outputs/cynthia_v67_attach_before_boss_audit_20260714/RESULT.md`.

### Poffin role balance is usually completed naturally

The former v55 idea was re-audited only after a new 600-game exact-v63 Silver
schedule became available. Seventy states had one Gible, no support line, two
Bench slots, both Gible and Roselia legal, and baseline `Gible + Gible` Poffin
targets. This time the mechanical exposure gates passed.

The complete sequence did not. Exact v63 established Roselia or Roserade
before its next attack in 62 of 70 exposures. The eight remaining missing-route
states covered only four blocks and had one win control, far below the frozen
24-state, five-block, and six-win requirements. Do not force role diversity in
every qualifying Poffin resolution: later setup already supplies the support
role in nearly all exposed games, while replacing the third Gible risks main
attacker redundancy. Full evidence is in
`analysis_outputs/cynthia_v68_poffin_role_pair_expanded_audit_20260714/RESULT.md`.

### A loss-state marker is not yet a development rule

The one-shot Roselia bridge audit found 72 games where v63 was about to use a
non-KO Corkscrew Dive with no support line in play and could legally Bench a
Roselia first. The state was common across both seats and all six seed blocks,
but appeared in only five wins and 67 losses.

That imbalance diagnoses a weak board state; it does not establish that the
proposed Roselia action repairs it. A deterministic rule must also be observed
often enough in successful controls to show that it preserves a winning
sequence. The frozen 16-win minimum failed, so the branch was rejected before
implementation. Do not transform an outcome-correlated trigger into a rule by
post-hoc filtering. Full evidence is in
`analysis_outputs/cynthia_v69_one_shot_roselia_bridge_audit_20260714/RESULT.md`.

### A complete transaction still needs the intended matchup surface

The multi-prize Spiritomb audit was mechanically stronger than the rejected
readiness proxies. On 600 historical-Silver games, 116 states certified the
complete public route from damaged Garchomp through Spiritomb to a lethal
multi-prize Raging Curse. Both seats, every block, 30 wins, and 86 losses were
represented, and exact v63 never completed the route naturally.

The cross-matchup requirement nevertheless failed. Four live
Starmie/Froslass games contained 25 damaged-Garchomp versus multi-prize states
with legal retreat and no immediate game-winning Garchomp attack, but none had
Spiritomb plus a same-turn Energy route. A rule that is coherent and common
against the local anchor can still have zero action surface in the live bucket
it is expected to help.

Therefore require both a complete legal transaction and evidence that its
public trigger exists in the intended structural matchup. Do not delete a
precommitted cross-matchup gate after learning that a candidate is effectively
anchor-only. Full evidence is in
`analysis_outputs/cynthia_v70_multiprize_spiritomb_audit_20260714/RESULT.md`.

### Guaranteed disruption can still be only a loss-state marker

The post-KO Unfair Stamp audit tested a mechanically guaranteed transaction:
both public hands would improve by at least two cards in Cynthia's favor, an
attack remained legal, and no immediate winning attack was displaced. The
public card effect was not uncertain.

Only 15 of 600 historical-Silver games exposed the complete trigger. More
importantly, all 15 were baseline losses; there were no successful control
trajectories. The same trigger appeared zero times in four fixed
Starmie/Froslass live episodes. Thus certainty about an action's local effect
does not establish causal recovery from a collapsed game state.

Require a proposed disruption rule to have both successful controls and real
surface in the intended matchup before implementation. Do not confuse a
guaranteed hand swing with a guaranteed improvement in board formation,
attack continuity, or prize exchange. Full evidence is in
`analysis_outputs/cynthia_v71_postko_unfair_stamp_audit_20260714/RESULT.md`.

### One correct live sequence is not yet a generic continuity rule

Archaludon loss 85883400 exposed a concrete missed transaction: exact v63 took
a non-final Corkscrew KO while an unused attachment could have energized one
of two Benched Gabite. The attachment would have preserved the immediate KO
and improved the board after a revenge KO. This is a valid tactical diagnosis.

The frozen population audit showed why it was not promoted. Only nine of 600
historical-Silver games exposed the complete sequence, with seats `3/6`, four
of six blocks, and win/loss controls `3/6`. None of four fixed
Starmie/Froslass episodes exposed it. The other live Archaludon loss required
its only Energy on the Active and was not corroboration.

Therefore require a coherent sequence discovered in a live loss to recur
across independent seeds, both seats, successful controls, and at least one
relevant adjacent matchup before turning it into a generic deterministic
override. Mechanical correctness in one episode is necessary but not
sufficient. Full evidence is in
`analysis_outputs/cynthia_v72_preko_continuity_attach_audit_20260714/RESULT.md`.

### A real action-classification defect still needs timing evidence

Unfair Stamp exposed a different failure mode from the sparse v71 disruption
rule. Exact v63 can classify Stamp as ordinary pre-Corkscrew development and
force it above an attack that has a much higher raw score. On the 600-game
historical-Silver anchor, 52 games exposed a direct correction with both seats,
all blocks, and substantial win and loss controls. This is a broad, real
classification issue rather than a rare collapsed-state marker.

The frozen live requirement still failed. Six public episodes exposed the
same issue, but each belonged to a different archetype; there was no repeated
mixed bucket with qualifying wins and losses. Conserving a one-copy ACE SPEC
may improve late disruption or deck-out survival, but it may also forfeit a
useful immediate refill. Without repeated live timing evidence, those effects
cannot be separated.

Thus a mechanically obvious taxonomy correction is not automatically a safe
policy correction. Preserve the distinction between proving that an action
was boosted for the wrong abstract reason and proving that the replacement
timing improves the complete game. Full evidence is in
`analysis_outputs/cynthia_v73_unfair_stamp_not_generic_development_audit_20260714/RESULT.md`.

### Generic retreat scoring is a broad base-policy defect

The no-conversion retreat audit found a much wider surface than the recent
one-shot rules. In 250 of 600 historical-Silver games, exact v63 spent the
Active's only Energy on a generic retreat into an unenergized,
non-higher-stage Pokemon, gained no legal attack, and immediately ended. Both
seats, every seed block, and successful as well as losing trajectories were
well represented.

This is strong evidence that a flat positive retreat fallback is inconsistent
with Cynthia's Energy and evolution plan. It is not yet evidence for the exact
veto tested here. The fixed public corpus exposed eleven examples overall, but
only one Starmie/Froslass loss and one Archaludon loss; neither repeated weak
bucket supplied a qualifying win. The live timing gate therefore failed before
candidate implementation.

Treat generic retreat valuation as a base-policy design problem in the next
coherent rebuild. Do not turn this audit into a hidden matchup patch, and do
not infer from broad local frequency alone that always ending is safer. Full
evidence is in
`analysis_outputs/cynthia_v74_no_conversion_paid_retreat_audit_20260714/RESULT.md`.

### Repeated failure shape is not automatically a new rule surface

The post-v74 root recheck found the same damaged-Garchomp endgame in both live
Archaludon losses: 110 HP on the Active, a zero-Energy Benched Garchomp, and an
opposing return-KO threat. A checked 19-state rotation audit found zero
Energy-ready backups and zero retreats. The recurrence is strategically
meaningful, but the only complete repair begins with attachment and rotation,
which is the previously rejected v29-v31 surface. Repetition alone does not
make an old unsafe transaction newly admissible.

The checked Starmie/Froslass audit similarly found no unsafe Buster decision.
Both exact-v63 Buster choices passed the existing selective rule: one took a
nonterminal multi-prize KO in a loss, while one took a board-clear KO in a win.
Outcome contrast without a public-state discriminator is not evidence to
reverse the action.

When a repeated replay symptom maps to a frozen rejected surface, require a
genuinely different complete transaction with broad anchor support and mixed
live-bucket evidence. Do not recover it through narrower card, opponent, turn,
prize, outcome, seat, seed, or block filters. Full evidence is in
`analysis_outputs/cynthia_post_v74_replay_recheck_20260714/RESULT.md`.

### A replay repair must demonstrate outcome conversion

Two Alakazam losses exposed the same clear mechanics error: Rock Fighting
Energy was preloaded to the Bench while the Active Gible or Gabite remained
unprotected from a damage-counter attack. A fail-closed v77 guard changed
exactly those two decisions and left ten winning Rock-to-Bench controls
unchanged. This established correctness and replay specificity.

It did not establish policy value. On a frozen population of six distinct
complete Alakazam policies, v75 and v77 were identical at `477/600`, with zero
paired gains or losses in every seat-policy cell. The intended trigger did not
produce a measurable outcome conversion, so the broader safety panels were
correctly skipped and v77 was rejected.

Use replay evidence to identify a mechanism and construct a minimal public
transaction. Then require the transaction to occur and convert outcomes on an
independent complete-policy population. Exact repair of a losing replay alone
is not enough to add another deterministic rule surface. Full evidence is in
`analysis_outputs/cynthia_v77_alakazam_rock_active_guard_20260715/RESULT.md`.

### Proactive role completion can outperform replay-only patches

Cynthia v80 was designed while waiting for additional live games rather than
from one losing episode. Before an ordinary paid non-KO attack, it advances the
first incomplete public role in a fixed deck-theory order: one complete
Garchomp route, Roserade support, a second main line, then an energized backup.
It preserves visible KOs and falls through to the established policy when the
transaction is not legal.

This broader sequence improved the historical-Silver anchor from `148/600` to
`183/600` and the six-agent population from `271/480` to `293/480`, with both
seats positive and no opponent bucket below v75. The result is materially
larger and broader than the preceding replay-specific corrections. The useful
general rule is to use live losses as one evidence source, not as the only
hypothesis generator: coherent deck-role completion can be proposed directly
from the deck's game plan, then tested against complete strong agents.

Two implementation details were essential. Nested overrides must not assume an
attack is legal on turn 1, and a forced target in a multi-card search must still
complete the remaining selections using the baseline ordering. The initial v79
prototype violated both contracts; v80 fixed them before submission.

### Immediate deployment is not automatically continuity

v83 tested whether an already selected Pokemon search should retain and
immediately deploy a Basic when Cynthia had only one Pokemon in play. The
historical-Silver result fell from `183/600` to `179/600`. Trace inspection
also separated two different mechanisms: the clean target-preserving
deployment example did not convert its game, while apparent gains relied on
retargeting the search itself.

This distinction matters for deterministic rule design. "Search then bench"
sounds like one coherent transaction, but preserving a weak target and
changing to a role-critical target are different policies. Do not add a latch
that merely guarantees completion of an earlier search choice. Evaluate the
search target, deployment, and remaining turn as one complete transaction.

### Static board completeness is not dynamic readiness

v84 attempted a broad proactive handoff: once Garchomp, Roserade, and a backup
line were visible, it preferred Corkscrew pressure over further generic
development. It regressed from `183/600` to `149/600`, with paired
gains/losses `5/39`; every 100-game block and both seats were negative.

The failure shows that role counts alone do not describe a resilient engine.
A board can look complete while still lacking replacement evolutions, future
Energy routes, recovery after disruption, or a second attacker after a prize
exchange. A future handoff rule must model multi-turn reserve renewal and
resource state, not just the current number of completed roles.

### Use trace-preserved structural evidence to choose proactive hypotheses

A fresh 160-game v80 corpus against historical-Silver Archaludon scored
`45/160`. The strongest checked separator occurred before the first major
prize conversion: games with no Garchomp by Cynthia's own turn 3 were `1/57`,
while Garchomp plus Roserade by turn 3 were `39/82`. First Buster with an
Energy-bearing backup was `20/37`, compared with `18/71` without one.

These are correlations, not action labels. They justify inspecting legal
early-turn sequencing and reserve construction in full traces; they do not
justify forcing Garchomp, Roserade, or an attachment whenever a matching card
is visible. The rule candidate must identify a repeated public-state decision
where the baseline chooses a different complete transaction, and it must then
convert outcomes on an independent both-seat schedule.

### A future knockout cannot be part of a public-state guard

The v86 audit found 35 rows where v80 evolved an energized Active Gible to its
first Gabite, could instead evolve a Benched Gible, secured Garchomp, and then
lost the Active Gabite before the next own turn. All 35 trajectories were
losses, across both seats and multiple turns. The alternative of sheltering
Gabite and leaving Gible Active is strategically coherent in those observed
trajectories.

It still is not a legal deterministic rule as stated. Whether the opponent
will remove Active Gabite is future information, and the current public state
did not separate those games from cases where Gabite survives. Firing the rule
without that discriminator gives up Dragonslice damage and Gabite durability,
and deliberately offers a one-prize Gible. Therefore a recurrent failure
mechanism can be real while its only apparent guard remains unobservable.

Require the trigger itself, not just the retrospective certificate, to use
present public information. A post-trajectory event may validate a mechanism;
it cannot be copied into the submitted policy condition.

### A long development chain is not necessarily overdevelopment

In live loss 85981103, v80 used Night Stretcher to recover Gabite, chained
three Champion's Calls, attacked with Dragonslice, and converted the surviving
two Gabite into two Garchomp ex on the next turn. The sequence looked long but
completed the intended role transaction and maintained attacks. The loss came
after Cynthia had already conceded three prizes to Mega Lucario and then lost
the two-prize race.

Across all 40 public v80 games, Night Stretcher was a v80-specific choice only
three times, in two wins and one loss. More broadly, games with any v75-v80
difference were 9-6. These descriptive results do not prove causal benefit,
but they reject the idea that the role-cycle surface is merely a recurring
loss marker. Diagnose a sequence by the board and attack state it produces,
not by action count or visual complexity alone.

# Task 8: PUBLIC_LILLIE_PHYSICAL_MINIMUM_ROUTE_ARBITRATION_T8_V1

## Frozen parent

- Parent: `archaludon_public_complete_supporter_purpose_arbitration_t7_v1`
- Parent `main.py` SHA-256:
  `8364A91B1DAF48968D9D5C3BBA257D43546E27AB7076841A5400124048602E28`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Hypothesis

Lillie's Determinationを固定スコアのドロー札ではなく、公開情報だけで計算した
手札・山札変換と、実行可能な物理ルートの非破壊比較として扱う。保護対象は
カード名ではなく、完全ルートに必要な最小枚数・serialだけとする。Direct Lillie
とGear→Lillieを同じSupporter transaction ownerで扱う。

## Exact transformation

```text
draw_n = 8 if own_prizes == 6 else 6
shuffle_count = pre_hand_count - 1
post_hand_count = draw_n
post_deck_count = pre_deck_count + shuffle_count - draw_n
```

played Lillieはdiscardへ移り、他の手札serialは`DECK_UNKNOWN`になる。再ドロー
identityは一切仮定しない。

## Hard priority

1. deck/setup/result/mandatory callback、legality、exact metadata;
2. Task 4–7、CUM/PFC/PCRD/DPER/PF/Turbo等の既存owner;
3. current Activeへのexact terminal attack;
4. Task 7 `FINISH_NOW_EXACT_BOSS`;
5. 既存の完全Prize/attack/board/search/recovery/Tool/Stadium/Supporter route;
6. Lillie前に今すぐmaterializeできる保護ルート最小部分;
7. materialize不能な必要最小物理カードの`HOLD_LILLIE`;
8. 公開利益を持つLillie;
9. exact cumulative parent.

低い層のcount利益で高い層の悪化を補償しない。Task 9のharmful-KO、一般Boss、
comeback価値は作らない。

## Protected routes

すべて、合法な先頭semantic role、完全queue、purpose、target serial、必要最小枚数、
遷移証明を持つ場合だけ認める。

- `ZERO_BENCH_BASIC`;
- `EXACT_NEXT_ATTACKER_BASIC`;
- `CURRENT_OR_NEXT_ATTACKER_EVOLUTION`;
- `ONE_METAL_ATTACK_COMPLETION`;
- Task 5/6または既存planner認証済みPad、Ultra Ball、Night Stretcher、Hero Cape、
  Jumbo Ice Cream、Full Metal Lab route;
- 既存certificateで宣言済みBoss/Explorer route;
- exact ready-backup、recovery、次ターン進化/attack route.

同名複数は必要最小枚数だけを`required_refs`へ束縛し、同値なら最小serial。余剰は
保護しない。カード名だけを理由にMetal、Pokémon、Boss、回収札を一律保護しない。

## Four directions

### PLAY_LILLIE

上位層が不変かつ、少なくとも一つを満たす。

- `HAND_RENEWAL_EXACT_COUNT`: `post_hand_count > pre_hand_count`;
- `DECKOUT_MARGIN_EXACT_COUNT`: `post_deck_count > pre_deck_count`;
- `RETURN_SURVIVAL_EXACT_HAND_COUNT`: 既存exact registry上、相手の現在支払い可能な
  公開手札枚数依存attackによるcertain KO/terminal reply/return Prizeが改善する。

`post_deck_count >= 1`を要求する。関連効果UNKNOWN、またはLillie後に新しいcertain
KO/terminal replyを作る場合はPLAY不可。Direct複数は最小serial。DirectとGearが
同時ならDirectを優先する。

### MATERIALIZE_THEN_REEVALUATE

PLAY利益があるが、Supporter権を使わず保護最小部分を今ターン完遂できる場合、
先にBasic配置、exact evolution/Assemble Alloy、bound targetへの一枚manual Metal、
または既存認証済みsearch/recovery/Tool/Stadium routeを実行する。実行後の実state
から再計算し、事前PLAYを持ち越さない。複雑なPFC/PCRD routeはTask8 ownerを立てず
原子的にhandoffし、owner-free MAINで再評価する。

### HOLD_LILLIE

必要最小物理カードを今ターンmaterializeできず、Lillieで`DECK_UNKNOWN`へ移すと
完全な次ターンattack/evolution/recovery/declared Boss/backup routeが消える場合。
materializer、exact attack、または安全なENDまでの一意で合法な代替queueが必要。
代替を束縛できなければparentへfail-close。単なるcard identityはHOLD理由にしない。

### GEAR_TO_LILLIE

Direct Lillieなし、上位PF/Task7目的なし、Lillieが公開領域で全枯れでなく、安全な
Gear whiff後継続がexactな場合だけ`contingent_on_reveal=True`で宣言する。

Gear hit時の変換:

```text
pre_lillie_hand = H
pre_lillie_deck = D - 1
shuffle_count = H - 1
post_hand_count = draw_n
post_deck_count = D + H - draw_n - 2
```

公開後に最小Lillie serialを初めて束縛し、利益を再検証する。Task7 terminal
`{Boss,Lillie}`はTask7がBoss。Task8状態はLillieがあれば最小serial、なければ`[]`。
undeclared Boss/Explorerへ代替しない。

## Ownership and lifecycle

並行ownerを作らず、既存`_pfgear_transaction`をrule-id dispatch付き単一Supporter
ownerとして再利用する。Task7/PF目的を先に評価する。

Direct/materialization:

```text
DECLARED
-> MATERIALIZER_EMITTED / MATERIALIZER_CONTINUATION
-> MATERIALIZER_CONFIRMED
-> LILLIE_PLAY_EMITTED
-> LILLIE_RESOLVED
-> COMPLETE
```

Gear:

```text
GEAR_PLAY_EMITTED
-> GEAR_LILLIE_SELECT_EMITTED | GEAR_WHIFF_EMPTY_EMITTED
-> LILLIE_IN_HAND_CONFIRMED
-> LILLIE_PLAY_EMITTED
-> LILLIE_RESOLVED
-> COMPLETE
```

解決はbound Lillieがdiscard、`supporterPlayed=True`、exact hand/deck countだけで確認。
retryはsemantic roleを再bindしstage不変、`duplicate_count`のみ増やす。
option/lookingは`(card_id,serial,status,semantic_role)`でsort/hashする。

可逆境界前はclearしてparentへ戻す。不可逆発行後はundoを捏造せず
`IRREVERSIBLE_ABORT`を記録して現在stateのparentへhandoffする。seat/turn/result/
action-count/metadata/zone/flag/owner不一致でturnをまたがない。

## Required focused and safety gates

- 両seatでsix-Prize draw8、他Prize draw6とcount式;
- HAND_RENEWAL、DECKOUT_MARGIN、exact hand-size survival;
- neutral count、post-deck0、hand-size attack悪化の負例;
- zero-Bench Basic、exact evolution、one-Metal current/backup materialize;
- Pad/Ultra/Stretcher/Tool/Stadium owner handoff;
- future evolution/recovery/declared Boss/ready backup各HOLD;
- duplicatesで必要最小serialのみ保護;
- Task7 terminal Boss/current terminal attack/全既存owner controls;
- Gear全8 subset、multiple Lillie、固定looking+option反転、retry、whiff clear;
- Direct優先、Lillie全枯れ、hidden redraw identity不変;
- stale/malformed/owner collision/conservation.

Parent/deck hash固定、candidateは`main.py`のみ変更。compile/import/final callable、
legal60/ACE1/cache-free。current+207 historical shadowの全first differenceを
`PLAY/MATERIALIZE/HOLD/GEAR_LILLIE`へ分類しTask7 terminal変化0。extracted both-seat
smokeはaction error0/maxstep0。source別に
`starts = completes + whiffs + aborts + live`を成立させる。

これは実装安全性の契約であり、広い勝率評価を要求しない。

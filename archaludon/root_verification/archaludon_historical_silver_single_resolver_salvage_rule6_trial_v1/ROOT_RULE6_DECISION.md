# Rule 6 root採否

`PARENT_POKE_PAD_EMPTY_BENCH_DURALUDON_ONE_METAL_READY_SUCCESSOR_TRANSACTION_V1`を**REJECT**する。

- 数値・実行安全性: fixed160 `100=100`、G/R/T `0/0/160`、fault 0。
- 自然coverage: start 1、ready完結 0、whiff完結 0。
- 凍結条件: 自然start後に完結0なら`REJECT`。

条件拡張や補修stackは行わない。受理親はRule 5 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`のままとし、次はそこからRule 7だけを実装する。

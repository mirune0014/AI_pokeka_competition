# Round 0 source-episode oracle upper bound

- Read-only aggregation from frozen source traces and merged OK branch results.
- One override maximum per source episode: `oracle_reward = max(baseline terminal_reward, all candidate rewards)`.
- Transition notation in the tables: `WIN/DRAW/LOSS` counts.

## Overall

| scope | episodes | baseline W/D/L | oracle W/D/L | loss?win | loss?draw | draw?win | improved episodes | reward delta total | beneficial groups per improved episode | beneficial-but-not-improved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 2000 | 1621/0/379 | 1937/0/63 | 316 | 0 | 0 | 316 | 632.000000 | 3.762658 | 0 |

## By opponent

| opponent | episodes | baseline W/D/L | oracle W/D/L | loss?win | loss?draw | draw?win | improved episodes | reward delta total | beneficial groups per improved episode | beneficial-but-not-improved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| alakazam_public | 250 | 212/0/38 | 246/0/4 | 34 | 0 | 0 | 34 | 68.000000 | 4.147059 | 0 |
| alakazam_rmy_live | 250 | 190/0/60 | 241/0/9 | 51 | 0 | 0 | 51 | 102.000000 | 3.823529 | 0 |
| dragapult_live | 250 | 239/0/11 | 249/0/1 | 10 | 0 | 0 | 10 | 20.000000 | 5.400000 | 0 |
| historical_silver | 250 | 113/0/137 | 225/0/25 | 112 | 0 | 0 | 112 | 224.000000 | 3.276786 | 0 |
| marnie_kazuki_live | 250 | 212/0/38 | 244/0/6 | 32 | 0 | 0 | 32 | 64.000000 | 3.968750 | 0 |
| mega_lucario_public | 250 | 233/0/17 | 249/0/1 | 16 | 0 | 0 | 16 | 32.000000 | 3.500000 | 0 |
| ogerpon_cornerstone_public | 250 | 197/0/53 | 235/0/15 | 38 | 0 | 0 | 38 | 76.000000 | 3.789474 | 0 |
| starmie_public | 250 | 225/0/25 | 248/0/2 | 23 | 0 | 0 | 23 | 46.000000 | 4.565217 | 0 |

## By seat

| seat | episodes | baseline W/D/L | oracle W/D/L | loss?win | loss?draw | draw?win | improved episodes | reward delta total | beneficial groups per improved episode | beneficial-but-not-improved |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1000 | 818/0/182 | 967/0/33 | 149 | 0 | 0 | 149 | 298.000000 | 3.711409 | 0 |
| 1 | 1000 | 803/0/197 | 970/0/30 | 167 | 0 | 0 | 167 | 334.000000 | 3.808383 | 0 |

## Input controls

- source traces: `2000`
- branch groups: `15725`
- branch result rows: `98323`; OK: `98323`; non-OK: `0`

No individual game or position analysis, model proposal, threshold change, code change, commit, or push was performed.

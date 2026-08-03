# Rule 7 frozen-shadow first-difference review

The frozen Rule 5 versus Rule 7 shadow produced 23 first differences. Every row below is recorded in full, with proposal telemetry, in `shadow_differences.json`. `P` and `C` are parent and candidate option positions. No serial-only/order-only difference remains.

| Replay | Seat | Step/turn | Class | P -> C | Energy -> target | Role/start/deficit/allocation |
|---|---:|---:|---|---|---|---|
| 89273754 | 1 | 22/2 | primary exact fill | 0 -> 1 | 114 -> 64 | 224/0/3/3 |
| 89274268 | 0 | 20/2 | primary exact fill | 0 -> 2 | 57 -> 3 | 224/0/3/3 |
| 89277462 | 0 | 46/6 | zero recipient | 0,1,2 -> [] | - | empty Bench |
| 89280661 | 1 | 49/5 | primary exact fill | 0 -> 1 | 117 -> 63 | 224/0/3/3 |
| 89283885 | 1 | 29/3 | backup remainder | 0 -> 2 | 122 -> 63 | 224/0/3/1 |
| 89284426 | 1 | 16/2 | primary exact fill | 0 -> 1 | 114 -> 63 | 224/0/3/3 |
| 89284426 | 1 | 60/6 | backup remainder | 0 -> 2 | 118 -> 64 | 224/0/3/2 |
| 89284651 | 1 | 31/2 | primary exact fill | 0 -> 1 | 117 -> 63 | 224/0/3/3 |
| 89285518 | 1 | 32/3 | backup remainder | 0 -> 1 | 121 -> 64 | 224/0/3/1 |
| 89286075 | 0 | 53/4 | useful count reduced | 0,1,2 -> 1,2 | selected 33,55 -> 4 | 224/1/2/2 |
| 89289354 | 0 | 17/2 | zero recipient | 0,1,2 -> [] | - | empty Bench |
| 89289354 | 0 | 35/4 | zero recipient | 0,1,2 -> [] | - | empty Bench |
| 89292065 | 0 | 15/2 | zero recipient | 0,1,2 -> [] | - | empty Bench |
| 89292065 | 0 | 32/4 | useful count reduced | 0,1,2 -> 0,1 | selected 54,55 -> 6 | 224/1/2/2 |
| 89298963 | 0 | 26/2 | primary exact fill | 0 -> 1 | 57 -> 3 | 224/0/3/3 |
| 89305863 | 0 | 115/8 | useful count reduced | 0,1,2 -> 1,2 | selected 33,55 -> 6 | 224/1/2/2 |
| 87792210 | 1 | 70/6 | backup remainder | 0 -> 1 | 122 -> 64 | 224/0/3/1 |
| 87878368 | 1 | 29/2 | primary exact fill | 0 -> 1 | 120 -> 65 | 224/0/3/3 |
| 87980916 | 0 | 34/2 | primary exact fill | 0 -> 1 | 58 -> 4 | 224/0/3/3 |
| 88096405 | 0 | 18/2 | primary exact fill | 0 -> 1 | 57 -> 4 | 224/0/3/3 |
| 88252126 | 0 | 55/10 | primary exact fill | 0 -> 1 | 54 -> 4 | 224/0/3/3 |
| 88397067 | 1 | 21/2 | primary exact fill | 0 -> 3 | 117 -> 63 | 224/0/3/3 |
| 88579549 | 1 | 23/2 | primary exact fill | 0 -> 1 | 121 -> 64 | 224/0/3/3 |

Inspection result: all 23 first differences are within the frozen allowed classes. The 12 primary-target changes complete a zero-Energy Duraludon to exact Raging Hammer cost; the four backup changes use only the post-primary remainder; the three count reductions stop at exact readiness; and all four zero selections have an empty Bench. No first difference allocates to a third target, exceeds three Basic Metal, uses an evolution projection, or occurs outside exact Turbo Flare.

The runner rolls candidate ownership back immediately after each first action difference because the stored suffix reflects the historical parent action, not the counterfactual candidate action. On the 23 same-action paths, the candidate emits the exact final target with `UNCONFIRMED_ENGINE_TERMINAL_BOUNDARY`, immediately leaves `owner_after=null`, and retains only the passive retry token. All 23 next nonmatching callbacks clear that token and continue through the normal resolver; there are zero owner-release, prohibited-status, or passive-suppression violations. Final target emissions are not reported as completed or confirmed transactions.

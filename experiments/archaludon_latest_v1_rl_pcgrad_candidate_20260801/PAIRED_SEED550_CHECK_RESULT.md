# Paired seed-550 checkpoint check

## Scope

This is a small regression check, not a promotion panel. Each checkpoint used
the same eight opponents, both seats, and seed `731200550` for 16 matched cells.
The collector's policy RNG is also derived from the common game seed.

## Bound inputs

| Arm | Checkpoint SHA-256 | Manifest SHA-256 | Dataset SHA-256 |
|---|---|---|---|
| Zero-residual latest-v1 start | `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04` | `90E19DD7B1CF976C3AA484ABA480684FEB6BABE565326275F3ECA3E98C0F4AF9` | `0324C6DEDB3CB6494B25D08852C4F2AC78AEFB15E38F20716F6395CE8C0B543C` |
| Immediate predecessor | `CE617018EAE2A8F18E966BBEA8269259D2F7C70FABD53A61A73C7CA2DB107F06` | `330ED2342AB93ABBBA80A1ED48C12F00D9DBA4D7667EBBEEBFD6263390336774` | `F9238F88BE6687522751B82C911CBCEE98D1F73499E02E1C0B4F88187484677C` |
| Current fresh-PPO checkpoint | `F87587785CF1C47E1399C9FEC761346341C7D9BDB47F1EBA778AD9FA5970912E` | `EB8E7452A7616E8E699404FBE93709FD5B3BC47CFD41C61B3A93241EA699FEDF` | `46E4217006BA036D3E970D3673D73FF6AF69352D1C474B9B22E3932832FFD8DE` |

Every arm completed 16 clean games with zero action errors and zero max-step
hits.

## Results

| Arm | Wins | Losses | PPO rows |
|---|---:|---:|---:|
| Zero-residual latest-v1 start | 11 | 5 | 437 |
| Immediate predecessor | 10 | 6 | 432 |
| Current fresh-PPO checkpoint | 10 | 6 | 432 |

Current versus immediate predecessor:

- all 16 action traces and outcomes were identical;
- all 432 eligible rows had non-identical probability vectors;
- mean total variation was `0.000407961`, maximum was `0.002040277`;
- no argmax changed.

Current versus zero-residual start:

- 13 of 16 action traces were identical;
- three traces diverged late in the game;
- one outcome changed: Starmie seat 1 changed from win to loss;
- no cell changed from loss to win;
- Historical Silver remained 0/2 for both checkpoints on this seed.

## Decision

Do not promote the current checkpoint as stronger. This one-seed check is too
small to reject PPO or the fresh-rollout path, but it supplies no strength gain
and contains one adverse outcome. Keep the current checkpoint only as the next
training state, while retaining the zero-residual start and both intermediate
checkpoints for immediate rollback.

The next useful evidence is more matched seeds, especially against Historical
Silver and Starmie, rather than more epochs over an already consumed batch.

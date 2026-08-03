"""Corrections that require exact evolution-line transaction metadata."""

import planner_final_policy as final_policy


_ORIGINAL_CERTIFY_CANDIDATE = final_policy._certify_candidate


def certify_candidate(parent, obs, candidate):
    result = _ORIGINAL_CERTIFY_CANDIDATE(parent, obs, candidate)
    if result is None:
        return None
    plan, action, commit = result
    if dict(plan.metadata).get("kind") == "RUN_AWAY_SETUP_CLOCK" and commit:
        transaction = commit.get("transaction")
        if transaction is not None:
            source_serial = transaction["data"].get("source_serial")
            owner = transaction["data"].get("owner")
            player = obs.current.players[owner] if owner in (0, 1) else None
            source = next(
                (
                    pokemon
                    for pokemon in (list(player.active) + list(player.bench) if player is not None else [])
                    if pokemon.serial == source_serial
                ),
                None,
            )
            if source is None:
                return None
            # Run Away Draw shuffles the full evolution stack in addition to
            # the top Dudunsparce and any attached cards.
            transaction["data"]["attached_count"] += len(source.preEvolution or [])
    return plan, action, commit


final_policy._certify_candidate = certify_candidate


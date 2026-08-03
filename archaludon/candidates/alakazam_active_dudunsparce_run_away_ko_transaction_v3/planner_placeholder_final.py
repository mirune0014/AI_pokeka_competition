"""Canonicalize engine `[None]` empty board placeholders as absence."""

import copy

import planner_model as model
import planner_policy as core
import planner_raw_parity_v3 as raw_v3
import planner_runtime_model as runtime_model
import planner_snapshot_serial_final as snapshot_final


_ORIGINAL_RAW_PARITY = raw_v3.raw_parsed_agree
_ORIGINAL_SNAPSHOT = snapshot_final.public_snapshot


def _clean_raw(raw):
    cleaned = copy.deepcopy(raw)
    for player in cleaned["current"]["players"]:
        for zone in ("active", "bench"):
            player[zone] = [pokemon for pokemon in player[zone] if pokemon is not None]
    return cleaned


def _clean_obs(obs):
    cleaned = copy.deepcopy(obs)
    for player in cleaned.current.players:
        player.active = [pokemon for pokemon in player.active if pokemon is not None]
        player.bench = [pokemon for pokemon in player.bench if pokemon is not None]
    return cleaned


def raw_parsed_agree(raw, obs):
    try:
        # Absence is normalized only when both representations contain the
        # same number and positions of empty sentinels.
        for raw_player, parsed_player in zip(raw["current"]["players"], obs.current.players):
            for zone in ("active", "bench"):
                raw_zone = raw_player[zone]
                parsed_zone = getattr(parsed_player, zone)
                if len(raw_zone) != len(parsed_zone):
                    return False
                if tuple(value is None for value in raw_zone) != tuple(value is None for value in parsed_zone):
                    return False
        return _ORIGINAL_RAW_PARITY(_clean_raw(raw), _clean_obs(obs))
    except (KeyError, TypeError, AttributeError):
        return False


def public_snapshot(parent, obs):
    return _ORIGINAL_SNAPSHOT(parent, _clean_obs(obs))


runtime_model.raw_parsed_agree = raw_parsed_agree
runtime_model.public_snapshot = public_snapshot
model.public_snapshot = public_snapshot
core.public_snapshot = public_snapshot


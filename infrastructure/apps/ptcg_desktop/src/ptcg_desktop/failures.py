from __future__ import annotations

from .models import MatchPhase, MatchResult


AGENT_FAILURE_CODES = {
    "agent_exception",
    "agent_timeout",
    "agent_invalid_type",
    "agent_invalid_action",
    "agent_selection_rejected",
}


def normal_result(engine_result: int) -> MatchResult:
    if engine_result not in (0, 1, 2):
        raise ValueError(f"invalid engine result: {engine_result}")
    if engine_result == 2:
        return MatchResult("normal", None, 2, "draw", "引き分けです。")
    return MatchResult("normal", engine_result, engine_result, "engine_result", f"Player {engine_result} の勝利です。")


def human_forfeit(human_seat: int) -> MatchResult:
    if human_seat not in (0, 1):
        raise ValueError("human seat must be 0 or 1")
    winner = 1 - human_seat
    return MatchResult("human_forfeit", winner, None, "human_forfeit", "放棄により対戦相手の勝利です。", human_seat)


def classify_failure(code: str, human_seat: int, *, phase: MatchPhase | str | None = None) -> MatchResult:
    if human_seat not in (0, 1):
        raise ValueError("human seat must be 0 or 1")
    phase_value = MatchPhase(phase) if isinstance(phase, str) else phase
    if code in AGENT_FAILURE_CODES or (code in {"worker_exit", "timeout"} and phase_value == MatchPhase.AGENT_THINKING):
        return MatchResult(
            "technical_forfeit",
            human_seat,
            None,
            code,
            "AI 側の技術的敗北により、人間側の勝利です。",
            1 - human_seat,
        )
    return MatchResult(
        "system_error",
        None,
        None,
        code,
        "対戦を継続できないシステム障害が発生しました。",
        None,
    )

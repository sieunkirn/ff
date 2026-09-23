"""
음식 판정: 올바른 표정 / 오답 / 놓침 / 특수 아이템
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import config
from food import FoodItem


@dataclass
class JudgeResult:
    kind: str  # perfect, wrong, missed, coffee_curse, bomb_hit, pass
    score_delta: int
    message: str


def judge_food_in_zone(food: FoodItem, player_action: str) -> Optional[JudgeResult]:
    """
    판정 구역 안에서 플레이어 동작이 감지됐을 때 호출.
    player_action이 NONE이면 None 반환.
    """
    if player_action == config.FaceAction.NONE:
        return None

    required = food.required_action

    if food.special_key == "coffee":
        return JudgeResult("coffee_curse", config.SCORE_COFFEE_WRONG, "☕ 커피의 저주!")

    if food.special_key == "bomb":
        return JudgeResult("bomb_hit", config.SCORE_BOMB_WRONG, "💣 BOOM!")

    if player_action == required:
        return JudgeResult("perfect", config.SCORE_PERFECT, "PERFECT!")

    return JudgeResult("wrong", config.SCORE_WRONG, "WRONG!")


def judge_food_missed(food: FoodItem) -> JudgeResult:
    """판정 구역을 지나쳤는데 잡지 못한 경우"""
    if food.special_key in ("coffee", "bomb"):
        return JudgeResult("pass", 0, "")
    return JudgeResult("missed", config.SCORE_MISSED, "MISSED!")


def apply_score(current: int, delta: int) -> int:
    return max(0, current + delta)

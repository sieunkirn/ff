"""
음식 엔티티 생성·낙하·리소스 로딩
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

import pygame

import config


@dataclass
class FoodItem:
    """화면에 떨어지는 음식 하나"""

    x: float
    y: float
    speed: float
    emoji: str
    food_id: str
    category_key: Optional[str]  # fast_food / fruit / vegetable / None(특수)
    special_key: Optional[str]  # coffee / bomb
    required_action: str
    hint_text: str
    size: int = 48
    in_judge_zone: bool = False
    was_in_judge_zone: bool = False
    judged: bool = False
    surface: Optional[pygame.Surface] = field(default=None, repr=False)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.size, self.size)

    def update(self, dt: float) -> None:
        """아래로 이동"""
        self.y += self.speed * dt

    def is_off_screen(self) -> bool:
        return self.y > config.SCREEN_HEIGHT + self.size


class FoodAssetCache:
    """PNG가 있으면 사용, 없으면 이모지 텍스트로 그림"""

    def __init__(self) -> None:
        self._emoji_font: Optional[pygame.font.Font] = None
        self._image_cache: dict[str, pygame.Surface] = {}

    def _emoji_font_for(self, size: int) -> pygame.font.Font:
        if self._emoji_font is None or self._emoji_font.get_height() != size:
            self._emoji_font = pygame.font.SysFont("Segoe UI Emoji", size)
        return self._emoji_font

    def get_surface(self, emoji: str, image_name: Optional[str], size: int) -> pygame.Surface:
        key = f"{image_name or emoji}:{size}"
        if key in self._image_cache:
            return self._image_cache[key]

        surface: pygame.Surface
        if image_name:
            path = config.FOODS_IMAGE_DIR / image_name
            if path.is_file():
                try:
                    img = pygame.image.load(str(path)).convert_alpha()
                    surface = pygame.transform.smoothscale(img, (size, size))
                    self._image_cache[key] = surface
                    return surface
                except pygame.error:
                    pass

        font = self._emoji_font_for(size)
        rendered = font.render(emoji, True, (255, 255, 255))
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        rect = rendered.get_rect(center=(size // 2, size // 2))
        surface.blit(rendered, rect)
        self._image_cache[key] = surface
        return surface


class FoodSpawner:
    """난이도에 맞춰 음식 생성"""

    def __init__(self, assets: FoodAssetCache) -> None:
        self.assets = assets
        self._spawn_timer = 0.0
        self._category_keys = list(config.FOOD_CATEGORIES.keys())

    def reset(self) -> None:
        self._spawn_timer = 0.0

    def _pick_normal_food(self) -> tuple[str, dict, dict]:
        cat_key = random.choice(self._category_keys)
        cat = config.FOOD_CATEGORIES[cat_key]
        item = random.choice(cat["items"])
        return cat_key, cat, item

    def _pick_special(self) -> Optional[tuple[str, dict]]:
        if random.random() > config.SPECIAL_SPAWN_CHANCE:
            return None
        special_key = random.choices(
            list(config.SPECIAL_FOODS.keys()),
            weights=[config.SPECIAL_FOODS[k]["spawn_weight"] for k in config.SPECIAL_FOODS],
            k=1,
        )[0]
        return special_key, config.SPECIAL_FOODS[special_key]

    def try_spawn(
        self, dt: float, tier: dict, current_count: int, fall_speed: float
    ) -> Optional[FoodItem]:
        """간격이 되면 새 음식 반환"""
        if current_count >= tier["max_on_screen"]:
            return None

        self._spawn_timer += dt
        if self._spawn_timer < tier["spawn_interval"]:
            return None
        self._spawn_timer = 0.0

        size = 52
        margin = 80
        x = random.randint(margin, config.SCREEN_WIDTH - margin - size)

        special = self._pick_special()
        if special:
            special_key, data = special
            surf = self.assets.get_surface(data["emoji"], data.get("image"), size)
            return FoodItem(
                x=float(x),
                y=-size,
                speed=fall_speed,
                emoji=data["emoji"],
                food_id=data["id"],
                category_key=None,
                special_key=special_key,
                required_action=data["required_action"],
                hint_text=data["hint_text"],
                size=size,
                surface=surf,
            )

        cat_key, cat, item = self._pick_normal_food()
        surf = self.assets.get_surface(item["emoji"], item.get("image"), size)
        return FoodItem(
            x=float(x),
            y=-size,
            speed=fall_speed,
            emoji=item["emoji"],
            food_id=item["id"],
            category_key=cat_key,
            special_key=None,
            required_action=cat["required_action"],
            hint_text=cat["hint_text"],
            size=size,
            surface=surf,
        )


def get_difficulty_tier(elapsed_sec: float) -> dict:
    """경과 시간에 맞는 난이도 구간 반환"""
    tier = config.DIFFICULTY_TIERS[0]
    for t in config.DIFFICULTY_TIERS:
        if elapsed_sec >= t["from_sec"]:
            tier = t
    return tier


def fall_speed_for_tier(tier: dict) -> float:
    return config.BASE_FALL_SPEED * tier["fall_mult"]

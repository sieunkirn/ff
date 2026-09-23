"""
FACE FOOD FIGHT — Pygame 게임 루프 및 화면
1단계: 시작 화면, 카운트다운, 음식 낙하, 기본 UI
"""

from __future__ import annotations

import enum
import sys
from typing import List, Optional

import pygame

import config
from face_detector import FaceDetector, FaceStatus
from food import FoodAssetCache, FoodItem, FoodSpawner, fall_speed_for_tier, get_difficulty_tier
from judging import JudgeResult, apply_score, judge_food_in_zone, judge_food_missed


class GamePhase(enum.Enum):
    TITLE = "title"
    COUNTDOWN = "countdown"
    PLAYING = "playing"
    GAME_OVER = "game_over"


class FaceFoodFightGame:
    """게임 전체 상태와 렌더·업데이트"""

    def __init__(self, debug_mode: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption("FACE FOOD FIGHT")
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.debug_mode = debug_mode

        self.title_font = pygame.font.SysFont("malgungothic", 72, bold=True)
        self.ui_font = pygame.font.SysFont("malgungothic", 28)
        self.small_font = pygame.font.SysFont("malgungothic", 22)
        self.big_font = pygame.font.SysFont("malgungothic", 96, bold=True)

        self.assets = FoodAssetCache()
        self.spawner = FoodSpawner(self.assets)
        self.face = FaceDetector(debug_mode=debug_mode)

        self.phase = GamePhase.TITLE
        self.foods: List[FoodItem] = []
        self.score = 0
        self.elapsed = 0.0
        self.countdown_left = float(config.COUNTDOWN_BEFORE_START_SEC)
        self.start_button_rect = pygame.Rect(0, 0, 320, 64)
        self._layout_start_button()

        self._face_accum = 0.0
        self._face_interval = 1.0 / config.FACE_DETECT_FPS

        self.focus_food: Optional[FoodItem] = None
        self.feedback_text = ""
        self.feedback_timer = 0.0
        self.feedback_color = (255, 255, 255)
        self.particles: list[dict] = []
        self.collected: dict[str, int] = {}
        self.missed_count = 0
        self.perfect_count = 0
        self._try_init_sounds()

    def _try_init_sounds(self) -> None:
        """사운드 파일 없어도 게임은 계속"""
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                return
        for name, file in (("perfect", "perfect.wav"), ("wrong", "wrong.wav")):
            path = config.SOUNDS_DIR / file
            if path.is_file():
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    pass

    def _layout_start_button(self) -> None:
        self.start_button_rect.center = (
            config.SCREEN_WIDTH // 2,
            config.SCREEN_HEIGHT // 2 + 80,
        )

    def run(self) -> None:
        """메인 루프"""
        self.face.start()
        running = True
        try:
            while running:
                dt = self.clock.tick(config.GAME_FPS) / 1000.0
                dt = min(dt, 0.05)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        self._on_key_down(event.key)
                    elif event.type == pygame.KEYUP:
                        self.face.release_action_on_key_up(event.key)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self._on_mouse_click(event.pos)

                self._update_face(dt)
                self._update_phase(dt)

                self._draw()
                pygame.display.flip()
        finally:
            self.face.stop()
            pygame.quit()

    def _on_key_down(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return
        self.face.handle_debug_key(key)
        if self.phase == GamePhase.GAME_OVER and key == pygame.K_RETURN:
            self._reset_to_title()

    def _on_mouse_click(self, pos: tuple[int, int]) -> None:
        if self.phase == GamePhase.TITLE and self.start_button_rect.collidepoint(pos):
            self._begin_countdown()
        elif self.phase == GamePhase.GAME_OVER and self._retry_button_rect().collidepoint(pos):
            self._reset_to_title()

    def _begin_countdown(self) -> None:
        self.phase = GamePhase.COUNTDOWN
        self.countdown_left = float(config.COUNTDOWN_BEFORE_START_SEC)

    def _start_playing(self) -> None:
        self.phase = GamePhase.PLAYING
        self.foods.clear()
        self.spawner.reset()
        self.score = 0
        self.elapsed = 0.0
        self.focus_food = None
        self.feedback_text = ""
        self.feedback_timer = 0.0
        self.particles.clear()
        self.collected.clear()
        self.missed_count = 0
        self.perfect_count = 0

    def _reset_to_title(self) -> None:
        self.phase = GamePhase.TITLE
        self.foods.clear()

    def _update_face(self, dt: float) -> None:
        self._face_accum += dt
        while self._face_accum >= self._face_interval:
            self._face_accum -= self._face_interval
            self.face.process_frame_if_due(self._face_interval)

    def _update_phase(self, dt: float) -> None:
        if self.phase == GamePhase.COUNTDOWN:
            self.countdown_left -= dt
            if self.countdown_left <= 0:
                self._start_playing()
            return

        if self.phase != GamePhase.PLAYING:
            return

        self.elapsed += dt
        if self.elapsed >= config.GAME_DURATION_SEC:
            self.phase = GamePhase.GAME_OVER
            return

        tier = get_difficulty_tier(self.elapsed)
        speed = fall_speed_for_tier(tier)

        new_food = self.spawner.try_spawn(dt, tier, len(self.foods), speed)
        if new_food:
            self.foods.append(new_food)

        judge_top = config.JUDGE_ZONE_Y
        judge_bottom = config.JUDGE_ZONE_Y + config.JUDGE_ZONE_HEIGHT

        for food in self.foods:
            food.update(dt)
            rect = food.rect
            food.in_judge_zone = judge_top <= rect.centery <= judge_bottom

        self._update_focus_food()
        self._process_judgments()

        if self.feedback_timer > 0:
            self.feedback_timer -= dt
        self._update_particles(dt)

        remaining: List[FoodItem] = []
        for food in self.foods:
            if food.judged:
                continue
            if food.is_off_screen():
                if food.was_in_judge_zone:
                    self._resolve_missed(food)
                continue
            remaining.append(food)
        self.foods = remaining

    def _update_focus_food(self) -> None:
        """판정 구역에 있는 음식 중 가장 아래쪽을 '현재 타겟'으로 표시"""
        in_zone = [f for f in self.foods if f.in_judge_zone]
        if not in_zone:
            self.focus_food = None
            return
        self.focus_food = max(in_zone, key=lambda f: f.y)

    def _process_judgments(self) -> None:
        """판정 구역에서 표정과 음식 매칭"""
        action = self.face.latest_action
        judge_bottom = config.JUDGE_ZONE_Y + config.JUDGE_ZONE_HEIGHT

        for food in self.foods:
            if food.judged:
                continue

            if food.in_judge_zone:
                food.was_in_judge_zone = True
                if action != config.FaceAction.NONE:
                    result = judge_food_in_zone(food, action)
                    if result:
                        self._apply_judge_result(food, result)
            elif food.was_in_judge_zone and food.rect.centery > judge_bottom:
                self._resolve_missed(food)

    def _resolve_missed(self, food: FoodItem) -> None:
        if food.judged:
            return
        result = judge_food_missed(food)
        if result.kind == "pass":
            food.judged = True
            return
        self._apply_judge_result(food, result)

    def _apply_judge_result(self, food: FoodItem, result: JudgeResult) -> None:
        food.judged = True
        if result.score_delta:
            self.score = apply_score(self.score, result.score_delta)
        if result.message:
            self._show_feedback(result.message, result.kind)
        if result.kind == "perfect":
            self.perfect_count += 1
            self.collected[food.emoji] = self.collected.get(food.emoji, 0) + 1
            self._spawn_particles(food.rect.centerx, food.rect.centery)
            if "perfect" in self.sounds:
                self.sounds["perfect"].play()
        elif result.kind == "missed":
            self.missed_count += 1
        elif result.kind in ("wrong", "coffee_curse", "bomb_hit") and "wrong" in self.sounds:
            self.sounds["wrong"].play()

    def _show_feedback(self, text: str, kind: str) -> None:
        colors = {
            "perfect": (100, 255, 120),
            "wrong": (255, 100, 100),
            "missed": (255, 180, 80),
            "coffee_curse": (180, 120, 60),
            "bomb_hit": (255, 60, 60),
        }
        self.feedback_text = text
        self.feedback_timer = 1.2
        self.feedback_color = colors.get(kind, (255, 255, 255))

    def _spawn_particles(self, x: int, y: int) -> None:
        import random

        for _ in range(12):
            self.particles.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "vx": random.uniform(-120, 120),
                    "vy": random.uniform(-180, -40),
                    "life": random.uniform(0.4, 0.8),
                }
            )

    def _update_particles(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 300 * dt
            alive.append(p)
        self.particles = alive

    def _draw(self) -> None:
        self.screen.fill((30, 40, 70))

        if self.phase == GamePhase.TITLE:
            self._draw_title()
        elif self.phase == GamePhase.COUNTDOWN:
            self._draw_countdown()
        elif self.phase == GamePhase.PLAYING:
            self._draw_playing()
        elif self.phase == GamePhase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = self.title_font.render("FACE FOOD FIGHT", True, (255, 220, 100))
        sub = self.ui_font.render("먹지 말고 표정으로 잡아라!", True, (220, 230, 255))
        self.screen.blit(title, title.get_rect(center=(config.SCREEN_WIDTH // 2, 220)))
        self.screen.blit(sub, sub.get_rect(center=(config.SCREEN_WIDTH // 2, 300)))

        pygame.draw.rect(self.screen, (80, 160, 255), self.start_button_rect, border_radius=12)
        pygame.draw.rect(self.screen, (255, 255, 255), self.start_button_rect, 2, border_radius=12)
        btn = self.ui_font.render("게임 시작", True, (255, 255, 255))
        self.screen.blit(btn, btn.get_rect(center=self.start_button_rect.center))

        if self.debug_mode:
            hint = self.small_font.render(
                "DEBUG: W=윙크 M=입 벌리기 E=눈 크게", True, (180, 180, 180)
            )
            self.screen.blit(hint, (40, config.SCREEN_HEIGHT - 40))
        else:
            self._draw_camera_panel()

    def _draw_countdown(self) -> None:
        num = max(1, int(self.countdown_left) + 1)
        if self.countdown_left <= 0:
            num = 0
        text = self.big_font.render(str(num if num > 0 else "GO!"), True, (255, 100, 100))
        self.screen.blit(text, text.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)))
        label = self.ui_font.render("준비...", True, (255, 255, 255))
        self.screen.blit(label, label.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 80)))
        if not self.debug_mode:
            self._draw_camera_panel()

    def _draw_playing(self) -> None:
        self._draw_playfield()
        self._draw_hud()
        self._draw_camera_panel()
        self._draw_action_hint()

        for food in self.foods:
            if food.surface:
                self.screen.blit(food.surface, (int(food.x), int(food.y)))
            if food is self.focus_food:
                pygame.draw.rect(self.screen, (255, 255, 0), food.rect.inflate(8, 8), 2)

        if self.face.status == FaceStatus.NO_FACE and not self.debug_mode:
            warn = self.ui_font.render("얼굴을 카메라에 보여주세요.", True, (255, 120, 120))
            self.screen.blit(warn, warn.get_rect(center=(config.SCREEN_WIDTH // 2, 50)))

        for p in self.particles:
            alpha = int(255 * min(1.0, p["life"] / 0.4))
            s = pygame.Surface((8, 8), pygame.SRCALPHA)
            s.fill((255, 220, 80, alpha))
            self.screen.blit(s, (int(p["x"]), int(p["y"])))

        if self.feedback_timer > 0 and self.feedback_text:
            fb = self.big_font.render(self.feedback_text, True, self.feedback_color)
            self.screen.blit(fb, fb.get_rect(center=(config.SCREEN_WIDTH // 2, 140)))

    def _draw_playfield(self) -> None:
        ground_y = config.SCREEN_HEIGHT - 100
        pygame.draw.rect(
            self.screen,
            (50, 90, 50),
            pygame.Rect(0, ground_y, config.SCREEN_WIDTH, config.SCREEN_HEIGHT - ground_y),
        )
        pygame.draw.line(self.screen, (100, 180, 100), (0, ground_y), (config.SCREEN_WIDTH, ground_y), 3)

        zone = pygame.Rect(0, config.JUDGE_ZONE_Y, config.SCREEN_WIDTH, config.JUDGE_ZONE_HEIGHT)
        s = pygame.Surface((zone.width, zone.height), pygame.SRCALPHA)
        s.fill((255, 255, 0, 40))
        self.screen.blit(s, zone.topleft)
        pygame.draw.rect(self.screen, (255, 220, 80), zone, 2)

        player = self.ui_font.render("🧑 플레이어", True, (255, 255, 255))
        self.screen.blit(
            player,
            player.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 50)),
        )

    def _draw_hud(self) -> None:
        score_t = self.ui_font.render(f"점수: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_t, (24, 16))

        remaining = max(0, config.GAME_DURATION_SEC - self.elapsed)
        time_t = self.ui_font.render(f"남은 시간: {remaining:04.1f}s", True, (255, 255, 255))
        self.screen.blit(time_t, time_t.get_rect(topright=(config.SCREEN_WIDTH - 24, 16)))

        tier = get_difficulty_tier(self.elapsed)
        diff_t = self.small_font.render(f"난이도: {tier['name']}", True, (200, 220, 255))
        self.screen.blit(diff_t, (24, 52))

    def _draw_camera_panel(self) -> None:
        pad = 16
        w, h = config.CAMERA_PREVIEW_WIDTH, config.CAMERA_PREVIEW_HEIGHT
        x = config.SCREEN_WIDTH - w - pad
        y = config.SCREEN_HEIGHT - h - pad - 120

        pygame.draw.rect(self.screen, (20, 20, 30), (x - 4, y - 36, w + 8, h + 40), border_radius=8)
        cam_label = self.small_font.render("CAMERA", True, (180, 180, 200))
        self.screen.blit(cam_label, (x, y - 32))

        preview_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, (40, 40, 55), preview_rect)
        if self.face.preview_surface:
            scaled = pygame.transform.smoothscale(self.face.preview_surface, (w, h))
            self.screen.blit(scaled, preview_rect)
        else:
            msg = "(내장 카메라 없음)" if self.face.status == FaceStatus.NO_CAMERA else "(연결 중...)"
            placeholder = self.small_font.render(msg, True, (120, 120, 140))
            self.screen.blit(placeholder, placeholder.get_rect(center=preview_rect.center))

        status = self.small_font.render(self.face.status_label(), True, (150, 255, 150))
        self.screen.blit(status, (x, y + h + 6))

        act = self.small_font.render(
            f"Detected: {self.face.action_display_label()}", True, (255, 255, 200)
        )
        self.screen.blit(act, (x, y + h + 28))

    def _draw_action_hint(self) -> None:
        box = pygame.Rect(24, config.SCREEN_HEIGHT - 220, 360, 120)
        pygame.draw.rect(self.screen, (25, 35, 55), box, border_radius=10)
        pygame.draw.rect(self.screen, (100, 140, 200), box, 2, border_radius=10)

        if self.focus_food:
            emoji = self.focus_food.emoji
            cat = config.FOOD_CATEGORIES.get(self.focus_food.category_key or "", {})
            hint_emoji = cat.get("hint_emoji", "")
            hint = f"{hint_emoji} {self.focus_food.hint_text}".strip()
        else:
            emoji = "🍽"
            hint = "음식이 노란 판정 구역에 올 때 표정을 지으세요!"

        e_surf = self.title_font.render(emoji, True, (255, 255, 255))
        self.screen.blit(e_surf, (box.x + 16, box.y + 10))
        lines = self._wrap_text(hint, self.ui_font, box.width - 100)
        ty = box.y + 20
        for line in lines:
            t = self.ui_font.render(line, True, (230, 240, 255))
            self.screen.blit(t, (box.x + 90, ty))
            ty += t.get_height() + 4

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return [text]
        lines: list[str] = []
        cur = words[0]
        for w in words[1:]:
            test = f"{cur} {w}"
            if font.size(test)[0] <= max_width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def _retry_button_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, 280, 56).move(
            config.SCREEN_WIDTH // 2 - 140, config.SCREEN_HEIGHT // 2 + 120
        )

    def _draw_game_over(self) -> None:
        over = self.title_font.render("GAME OVER", True, (255, 120, 120))
        self.screen.blit(over, over.get_rect(center=(config.SCREEN_WIDTH // 2, 200)))
        score = self.ui_font.render(f"최종 점수: {self.score:,}", True, (255, 255, 255))
        self.screen.blit(score, score.get_rect(center=(config.SCREEN_WIDTH // 2, 270)))

        total = self.perfect_count + self.missed_count
        acc = int(self.perfect_count / total * 100) if total else 0
        stats = self.small_font.render(
            f"획득 {self.perfect_count} · 놓침 {self.missed_count} · 정확도 {acc}%",
            True,
            (200, 210, 230),
        )
        self.screen.blit(stats, stats.get_rect(center=(config.SCREEN_WIDTH // 2, 320)))

        rect = self._retry_button_rect()
        pygame.draw.rect(self.screen, (80, 160, 255), rect, border_radius=10)
        btn = self.ui_font.render("다시 하기", True, (255, 255, 255))
        self.screen.blit(btn, btn.get_rect(center=rect.center))


def main(debug: bool = False) -> None:
    game = FaceFoodFightGame(debug_mode=debug)
    game.run()


if __name__ == "__main__":
    debug_flag = "--debug" in sys.argv or "-d" in sys.argv
    main(debug=debug_flag)

"""
FACE FOOD FIGHT — 전역 설정
Raspberry Pi / PC 공통으로 사용하는 상수와 음식·동작 데이터
"""

from pathlib import Path

# ── 경로 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FOODS_IMAGE_DIR = ASSETS_DIR / "foods"
SOUNDS_DIR = ASSETS_DIR / "sounds"
IMAGES_DIR = ASSETS_DIR / "images"

# ── 화면 / FPS ────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
GAME_FPS = 60
FACE_DETECT_FPS = 20  # 2단계 이후 MediaPipe용 (게임 루프와 분리 예정)

# ── 게임 규칙 ─────────────────────────────────────────
GAME_DURATION_SEC = 60
COUNTDOWN_BEFORE_START_SEC = 3
DEFAULT_PLAYER_NAMES = ["플레이어1", "플레이어2", "플레이어3", "플레이어4"]

SCORE_PERFECT = 100
SCORE_WRONG = -50
SCORE_MISSED = -20
SCORE_COFFEE_WRONG = -100
SCORE_BOMB_WRONG = -200

# ── 난이도 (경과 시간 기준, 초) ───────────────────────
DIFFICULTY_TIERS = [
    {"name": "EASY", "from_sec": 0, "fall_mult": 1.0, "spawn_interval": 1.8, "max_on_screen": 2},
    {"name": "NORMAL", "from_sec": 15, "fall_mult": 1.3, "spawn_interval": 1.4, "max_on_screen": 3},
    {"name": "HARD", "from_sec": 30, "fall_mult": 1.6, "spawn_interval": 1.0, "max_on_screen": 4},
    {"name": "INSANE", "from_sec": 45, "fall_mult": 2.0, "spawn_interval": 0.7, "max_on_screen": 5},
]

BASE_FALL_SPEED = 180  # 픽셀/초

# ── 판정 영역 (화면 하단 쪽) ───────────────────────────
JUDGE_ZONE_HEIGHT = 120
JUDGE_ZONE_Y = SCREEN_HEIGHT - 180 - JUDGE_ZONE_HEIGHT

# ── 카메라 미리보기 ───────────────────────────────────
# 노트북 내장 카메라는 보통 0, USB 웹캠을 쓰면 1 등으로 변경
CAMERA_INDEX = 0
CAMERA_PREVIEW_WIDTH = 240
CAMERA_PREVIEW_HEIGHT = 180
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_MIRROR = True  # 셀카처럼 좌우 반전

# ── 얼굴 동작 (2단계 이후 사용) ───────────────────────
class FaceAction:
    NONE = "none"
    WINK_LEFT = "wink_left"
    MOUTH_OPEN = "mouth_open"
    EYES_WIDE = "eyes_wide"


# MediaPipe 판정 임계값 (face_detector.py에서 사용)
BLINK_THRESHOLD = 0.15
EYE_OPEN_MIN = 0.18          # 윙크 시 반대쪽 눈이 열려 있어야 하는 최소 EAR
MOUTH_OPEN_THRESHOLD = 0.06
EYE_OPEN_THRESHOLD = 1.35
ACTION_CONFIRM_FRAMES = 3

# ── 음식 카테고리 (동작·아이템은 데이터로 분리) ───────
FOOD_CATEGORIES = {
    "fast_food": {
        "label": "패스트푸드",
        "required_action": FaceAction.WINK_LEFT,
        "hint_emoji": "😉",
        "hint_text": "왼쪽 눈을 윙크하세요!",
        "items": [
            {"id": "burger", "emoji": "🍔", "image": "burger.png"},
            {"id": "chicken", "emoji": "🍗", "image": "chicken.png"},
            {"id": "pizza", "emoji": "🍕", "image": "pizza.png"},
        ],
    },
    "fruit": {
        "label": "과일",
        "required_action": FaceAction.MOUTH_OPEN,
        "hint_emoji": "👄",
        "hint_text": "입을 크게 벌리세요!",
        "items": [
            {"id": "apple", "emoji": "🍎", "image": "apple.png"},
            {"id": "banana", "emoji": "🍌", "image": "banana.png"},
            {"id": "strawberry", "emoji": "🍓", "image": "strawberry.png"},
        ],
    },
    "vegetable": {
        "label": "채소",
        "required_action": FaceAction.EYES_WIDE,
        "hint_emoji": "👀",
        "hint_text": "양쪽 눈을 크게 뜨세요!",
        "items": [
            {"id": "broccoli", "emoji": "🥦", "image": "broccoli.png"},
            {"id": "carrot", "emoji": "🥕", "image": "carrot.png"},
            {"id": "cucumber", "emoji": "🥒", "image": "cucumber.png"},
        ],
    },
}

SPECIAL_FOODS = {
    "coffee": {
        "id": "coffee",
        "emoji": "☕",
        "image": "coffee.png",
        "required_action": FaceAction.NONE,
        "hint_text": "아무 표정도 하지 마세요!",
        "spawn_weight": 0.08,
    },
    "bomb": {
        "id": "bomb",
        "emoji": "💣",
        "image": "bomb.png",
        "required_action": FaceAction.NONE,
        "hint_text": "표정 없이 피하세요!",
        "spawn_weight": 0.06,
    },
}

SPECIAL_SPAWN_CHANCE = 0.12  # 일반 스폰 시 특수 아이템 시도 확률

# ── 디버그 ────────────────────────────────────────────
DEBUG_MODE_DEFAULT = False

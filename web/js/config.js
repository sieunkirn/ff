/** FACE FOOD FIGHT — 웹版 설정 (Python config.py와 동일 규칙) */

export const CONFIG = {
  WIDTH: 1280,
  HEIGHT: 720,
  GAME_DURATION_SEC: 60,
  COUNTDOWN_SEC: 3,
  BASE_FALL_SPEED: 180,
  JUDGE_ZONE_HEIGHT: 120,
  get JUDGE_ZONE_Y() {
    return this.HEIGHT - 180 - this.JUDGE_ZONE_HEIGHT;
  },
  SCORE: {
    PERFECT: 100,
    WRONG: -50,
    MISSED: -20,
    COFFEE: -100,
    BOMB: -200,
  },
  DIFFICULTY_TIERS: [
    { name: "EASY", fromSec: 0, fallMult: 1.0, spawnInterval: 1.8, maxOnScreen: 2 },
    { name: "NORMAL", fromSec: 15, fallMult: 1.3, spawnInterval: 1.4, maxOnScreen: 3 },
    { name: "HARD", fromSec: 30, fallMult: 1.6, spawnInterval: 1.0, maxOnScreen: 4 },
    { name: "INSANE", fromSec: 45, fallMult: 2.0, spawnInterval: 0.7, maxOnScreen: 5 },
  ],
  FACE: {
    BLINK_THRESHOLD: 0.15,
    EYE_OPEN_MIN: 0.18,
    MOUTH_OPEN_THRESHOLD: 0.06,
    EYE_OPEN_THRESHOLD: 1.35,
    CONFIRM_FRAMES: 3,
    DETECT_INTERVAL_MS: 50,
  },
  SPECIAL_SPAWN_CHANCE: 0.12,
};

export const FaceAction = {
  NONE: "none",
  WINK_LEFT: "wink_left",
  MOUTH_OPEN: "mouth_open",
  EYES_WIDE: "eyes_wide",
};

export const FOOD_CATEGORIES = {
  fast_food: {
    requiredAction: FaceAction.WINK_LEFT,
    hintEmoji: "😉",
    hintText: "왼쪽 눈을 윙크하세요!",
    items: ["🍔", "🍗", "🍕"],
  },
  fruit: {
    requiredAction: FaceAction.MOUTH_OPEN,
    hintEmoji: "👄",
    hintText: "입을 크게 벌리세요!",
    items: ["🍎", "🍌", "🍓"],
  },
  vegetable: {
    requiredAction: FaceAction.EYES_WIDE,
    hintEmoji: "👀",
    hintText: "양쪽 눈을 크게 뜨세요!",
    items: ["🥦", "🥕", "🥒"],
  },
};

export const SPECIAL_FOODS = {
  coffee: {
    emoji: "☕",
    requiredAction: FaceAction.NONE,
    hintText: "아무 표정도 하지 마세요!",
    weight: 0.08,
  },
  bomb: {
    emoji: "💣",
    requiredAction: FaceAction.NONE,
    hintText: "표정 없이 피하세요!",
    weight: 0.06,
  },
};

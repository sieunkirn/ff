import { CONFIG, FaceAction } from "./config.js";

export function judgeInZone(food, action) {
  if (action === FaceAction.NONE) return null;

  if (food.specialKey === "coffee") {
    return { kind: "coffee_curse", delta: CONFIG.SCORE.COFFEE, message: "☕ 커피의 저주!" };
  }
  if (food.specialKey === "bomb") {
    return { kind: "bomb_hit", delta: CONFIG.SCORE.BOMB, message: "💣 BOOM!" };
  }
  if (action === food.requiredAction) {
    return { kind: "perfect", delta: CONFIG.SCORE.PERFECT, message: "PERFECT!" };
  }
  return { kind: "wrong", delta: CONFIG.SCORE.WRONG, message: "WRONG!" };
}

export function judgeMissed(food) {
  if (food.specialKey === "coffee" || food.specialKey === "bomb") {
    return { kind: "pass", delta: 0, message: "" };
  }
  return { kind: "missed", delta: CONFIG.SCORE.MISSED, message: "MISSED!" };
}

export function applyScore(score, delta) {
  return Math.max(0, score + delta);
}

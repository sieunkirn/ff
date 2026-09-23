import {
  CONFIG,
  FaceAction,
  FOOD_CATEGORIES,
  SPECIAL_FOODS,
} from "./config.js";
import { judgeInZone, judgeMissed, applyScore } from "./judging.js";

function pickTier(elapsed) {
  let tier = CONFIG.DIFFICULTY_TIERS[0];
  for (const t of CONFIG.DIFFICULTY_TIERS) {
    if (elapsed >= t.fromSec) tier = t;
  }
  return tier;
}

function randomFood() {
  if (Math.random() < CONFIG.SPECIAL_SPAWN_CHANCE) {
    const keys = Object.keys(SPECIAL_FOODS);
    const weights = keys.map((k) => SPECIAL_FOODS[k].weight);
    const sum = weights.reduce((a, b) => a + b, 0);
    let r = Math.random() * sum;
    for (let i = 0; i < keys.length; i++) {
      r -= weights[i];
      if (r <= 0) {
        const s = SPECIAL_FOODS[keys[i]];
        return {
          emoji: s.emoji,
          categoryKey: null,
          specialKey: keys[i],
          requiredAction: s.requiredAction,
          hintText: s.hintText,
        };
      }
    }
  }
  const catKeys = Object.keys(FOOD_CATEGORIES);
  const catKey = catKeys[Math.floor(Math.random() * catKeys.length)];
  const cat = FOOD_CATEGORIES[catKey];
  const emoji = cat.items[Math.floor(Math.random() * cat.items.length)];
  return {
    emoji,
    categoryKey: catKey,
    specialKey: null,
    requiredAction: cat.requiredAction,
    hintText: cat.hintText,
    hintEmoji: cat.hintEmoji,
  };
}

export class Game {
  constructor(canvas, face) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.face = face;
    this.phase = "title";
    this.score = 0;
    this.elapsed = 0;
    this.countdown = CONFIG.COUNTDOWN_SEC;
    this.foods = [];
    this.spawnTimer = 0;
    this.feedback = { text: "", timer: 0, color: "#fff" };
    this.particles = [];
    this.perfectCount = 0;
    this.missedCount = 0;
    this.focusFood = null;
    this._lastTs = 0;
  }

  startCountdown() {
    this.phase = "countdown";
    this.countdown = CONFIG.COUNTDOWN_SEC;
  }

  resetPlaying() {
    this.phase = "playing";
    this.score = 0;
    this.elapsed = 0;
    this.foods = [];
    this.spawnTimer = 0;
    this.perfectCount = 0;
    this.missedCount = 0;
    this.feedback.timer = 0;
    this.particles = [];
    if (this.face.smoother) this.face.smoother.reset();
  }

  update(dt, now) {
    this.face.tick(now);

    if (this.phase === "countdown") {
      this.countdown -= dt;
      if (this.countdown <= 0) this.resetPlaying();
      return;
    }
    if (this.phase !== "playing") return;

    this.elapsed += dt;
    if (this.elapsed >= CONFIG.GAME_DURATION_SEC) {
      this.phase = "gameover";
      return;
    }

    const tier = pickTier(this.elapsed);
    const speed = CONFIG.BASE_FALL_SPEED * tier.fallMult;

    this.spawnTimer += dt;
    if (this.spawnTimer >= tier.spawnInterval && this.foods.length < tier.maxOnScreen) {
      this.spawnTimer = 0;
      const data = randomFood();
      const size = 52;
      this.foods.push({
        x: 80 + Math.random() * (CONFIG.WIDTH - 160 - size),
        y: -size,
        size,
        speed,
        judged: false,
        wasInZone: false,
        inZone: false,
        ...data,
      });
    }

    const jy = CONFIG.JUDGE_ZONE_Y;
    const jb = jy + CONFIG.JUDGE_ZONE_HEIGHT;
    const action = this.face.action;

    for (const food of this.foods) {
      if (food.judged) continue;
      food.y += food.speed * dt;
      const cy = food.y + food.size / 2;
      food.inZone = cy >= jy && cy <= jb;

      if (food.inZone) {
        food.wasInZone = true;
        const result = judgeInZone(food, action);
        if (result) this.applyResult(food, result);
      } else if (food.wasInZone && cy > jb) {
        this.applyResult(food, judgeMissed(food));
      }
    }

    this.foods = this.foods.filter((f) => {
      if (f.judged) return false;
      if (f.y > CONFIG.HEIGHT + f.size) {
        if (f.wasInZone) this.applyResult(f, judgeMissed(f));
        return false;
      }
      return true;
    });

    const inZone = this.foods.filter((f) => f.inZone && !f.judged);
    this.focusFood = inZone.length ? inZone.reduce((a, b) => (a.y > b.y ? a : b)) : null;

    if (this.feedback.timer > 0) this.feedback.timer -= dt;
    this.particles.forEach((p) => {
      p.life -= dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 300 * dt;
    });
    this.particles = this.particles.filter((p) => p.life > 0);
  }

  applyResult(food, result) {
    if (food.judged) return;
    food.judged = true;
    if (result.delta) this.score = applyScore(this.score, result.delta);
    if (result.message) {
      const colors = {
        perfect: "#64ff78",
        wrong: "#ff6464",
        missed: "#ffb450",
        coffee_curse: "#b4783c",
        bomb_hit: "#ff3c3c",
      };
      this.feedback = { text: result.message, timer: 1.2, color: colors[result.kind] || "#fff" };
    }
    if (result.kind === "perfect") {
      this.perfectCount++;
      const cx = food.x + food.size / 2;
      const cy = food.y + food.size / 2;
      for (let i = 0; i < 12; i++) {
        this.particles.push({
          x: cx,
          y: cy,
          vx: (Math.random() - 0.5) * 240,
          vy: -80 - Math.random() * 120,
          life: 0.4 + Math.random() * 0.4,
        });
      }
    } else if (result.kind === "missed") this.missedCount++;
  }

  draw() {
    const ctx = this.ctx;
    const W = CONFIG.WIDTH;
    const H = CONFIG.HEIGHT;

    ctx.fillStyle = "#1e2846";
    ctx.fillRect(0, 0, W, H);

    if (this.phase === "title") {
      this.drawTitle(ctx, W, H);
      this.drawCameraPanel(ctx, W, H);
      return;
    }
    if (this.phase === "countdown") {
      this.drawCountdown(ctx, W, H);
      this.drawCameraPanel(ctx, W, H);
      return;
    }
    if (this.phase === "gameover") {
      this.drawGameOver(ctx, W, H);
      return;
    }

    this.drawPlayfield(ctx, W, H);
    this.drawHud(ctx, W, H);

    for (const food of this.foods) {
      ctx.font = `${food.size}px serif`;
      ctx.textAlign = "left";
      ctx.fillText(food.emoji, food.x, food.y + food.size * 0.85);
      if (food === this.focusFood) {
        ctx.strokeStyle = "#ffff00";
        ctx.lineWidth = 2;
        ctx.strokeRect(food.x - 4, food.y - 4, food.size + 8, food.size + 8);
      }
    }

    this.drawHint(ctx);
    this.drawCameraPanel(ctx, W, H);

    if (this.face.status === "no_face" && !this.face.debugMode) {
      ctx.fillStyle = "#ff7878";
      ctx.font = "28px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("얼굴을 카메라에 보여주세요.", W / 2, 50);
    }

    if (this.feedback.timer > 0) {
      ctx.fillStyle = this.feedback.color;
      ctx.font = "bold 72px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(this.feedback.text, W / 2, 140);
    }

    ctx.fillStyle = "rgba(255,220,80,0.9)";
    for (const p of this.particles) {
      ctx.fillRect(p.x, p.y, 8, 8);
    }
  }

  drawTitle(ctx, W, H) {
    ctx.fillStyle = "#ffdc64";
    ctx.font = "bold 64px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("FACE FOOD FIGHT", W / 2, 200);
    ctx.fillStyle = "#dce6ff";
    ctx.font = "28px system-ui, sans-serif";
    ctx.fillText("먹지 말고 표정으로 잡아라!", W / 2, 260);
    ctx.fillStyle = "#888";
    ctx.font = "18px system-ui, sans-serif";
    ctx.fillText("웹캠 허용 후 [게임 시작]을 누르세요 (HTTPS 필요)", W / 2, 310);
  }

  drawCountdown(ctx, W, H) {
    const n = Math.max(0, Math.ceil(this.countdown));
    ctx.fillStyle = "#ff6464";
    ctx.font = "bold 96px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(n > 0 ? String(n) : "GO!", W / 2, H / 2);
  }

  drawGameOver(ctx, W, H) {
    ctx.fillStyle = "#ff7878";
    ctx.font = "bold 64px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("GAME OVER", W / 2, 180);
    ctx.fillStyle = "#fff";
    ctx.font = "32px system-ui, sans-serif";
    ctx.fillText(`최종 점수: ${this.score.toLocaleString()}`, W / 2, 260);
    const total = this.perfectCount + this.missedCount;
    const acc = total ? Math.round((this.perfectCount / total) * 100) : 0;
    ctx.font = "22px system-ui, sans-serif";
    ctx.fillStyle = "#c8d2e6";
    ctx.fillText(`획득 ${this.perfectCount} · 놓침 ${this.missedCount} · 정확도 ${acc}%`, W / 2, 310);
    ctx.fillText("[다시 하기] 버튼을 누르세요", W / 2, 360);
  }

  drawPlayfield(ctx, W, H) {
    const ground = H - 100;
    ctx.fillStyle = "#325a32";
    ctx.fillRect(0, ground, W, H - ground);
    ctx.fillStyle = "rgba(255,255,0,0.15)";
    ctx.fillRect(0, CONFIG.JUDGE_ZONE_Y, W, CONFIG.JUDGE_ZONE_HEIGHT);
    ctx.strokeStyle = "#ffdc50";
    ctx.strokeRect(0, CONFIG.JUDGE_ZONE_Y, W, CONFIG.JUDGE_ZONE_HEIGHT);
    ctx.font = "28px serif";
    ctx.textAlign = "center";
    ctx.fillText("🧑 플레이어", W / 2, H - 40);
  }

  drawHud(ctx, W) {
    const tier = pickTier(this.elapsed);
    ctx.fillStyle = "#fff";
    ctx.font = "24px system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(`점수: ${this.score}`, 24, 36);
    ctx.textAlign = "right";
    const rem = Math.max(0, CONFIG.GAME_DURATION_SEC - this.elapsed);
    ctx.fillText(`남은 시간: ${rem.toFixed(1)}s`, W - 24, 36);
    ctx.textAlign = "left";
    ctx.font = "18px system-ui, sans-serif";
    ctx.fillStyle = "#c8dcff";
    ctx.fillText(`난이도: ${tier.name}`, 24, 62);
  }

  drawHint(ctx) {
    const box = { x: 24, y: CONFIG.HEIGHT - 200, w: 380, h: 110 };
    ctx.fillStyle = "#192337";
    ctx.strokeStyle = "#648cc8";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(box.x, box.y, box.w, box.h, 10);
    ctx.fill();
    ctx.stroke();

    let emoji = "🍽";
    let hint = "음식이 노란 판정 구역에 올 때 표정을 지으세요!";
    if (this.focusFood) {
      emoji = this.focusFood.emoji;
      const cat = FOOD_CATEGORIES[this.focusFood.categoryKey];
      const he = cat?.hintEmoji || "";
      hint = `${he} ${this.focusFood.hintText}`.trim();
    }
    ctx.font = "48px serif";
    ctx.textAlign = "left";
    ctx.fillText(emoji, box.x + 16, box.y + 58);
    ctx.fillStyle = "#e6f0ff";
    ctx.font = "22px system-ui, sans-serif";
    ctx.fillText(hint, box.x + 90, box.y + 48, box.w - 100);
  }

  drawCameraPanel(ctx, W, H) {
    const pw = 240;
    const ph = 180;
    const x = W - pw - 16;
    const y = H - ph - 130;
    const v = this.face.video;

    ctx.fillStyle = "#14141e";
    ctx.fillRect(x - 4, y - 28, pw + 8, ph + 52);
    ctx.fillStyle = "#b4b4c8";
    ctx.font = "16px system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("CAMERA", x, y - 8);

    ctx.fillStyle = "#282837";
    ctx.fillRect(x, y, pw, ph);

    if (v.readyState >= 2 && v.videoWidth) {
      ctx.save();
      ctx.translate(x + pw, y);
      ctx.scale(-1, 1);
      ctx.drawImage(v, 0, 0, pw, ph);
      ctx.restore();
    } else {
      ctx.fillStyle = "#787890";
      ctx.font = "14px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        this.face.status === "no_camera" ? "(카메라 없음)" : "(연결 중…)",
        x + pw / 2,
        y + ph / 2
      );
    }

    ctx.textAlign = "left";
    ctx.fillStyle = "#96ff96";
    ctx.font = "14px system-ui, sans-serif";
    ctx.fillText(this.face.getStatusLabel(), x, y + ph + 18);
    ctx.fillStyle = "#ffffc8";
    ctx.fillText(`Detected: ${this.face.getActionLabel()}`, x, y + ph + 38);
  }
}

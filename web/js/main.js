import { Game } from "./game.js";
import { FaceTracker } from "./face.js";
import { FaceAction } from "./config.js";

const canvas = document.getElementById("game");
const video = document.getElementById("cam");
const btnStart = document.getElementById("btn-start");
const btnRetry = document.getElementById("btn-retry");
const statusEl = document.getElementById("load-status");

const params = new URLSearchParams(location.search);
const debugMode = params.get("debug") === "1";

const face = new FaceTracker(video);
face.debugMode = debugMode;

const game = new Game(canvas, face);

function resize() {
  const wrap = canvas.parentElement;
  const scale = Math.min(wrap.clientWidth / 1280, wrap.clientHeight / 720, 1);
  canvas.width = 1280;
  canvas.height = 720;
  canvas.style.width = `${1280 * scale}px`;
  canvas.style.height = `${720 * scale}px`;
}
window.addEventListener("resize", resize);
resize();

statusEl.textContent = "카메라·얼굴 인식 모델 불러오는 중…";
const camOk = await face.init();
statusEl.textContent = camOk
  ? debugMode
    ? "DEBUG: W/M/E 키로 표정 테스트"
    : "준비 완료! 게임 시작을 누르세요."
  : "카메라를 사용할 수 없습니다. ?debug=1 로 키보드 테스트";

btnStart.hidden = !camOk && !debugMode;
if (debugMode && !camOk) face.status = "ok";

btnStart.addEventListener("click", () => {
  btnStart.hidden = true;
  btnRetry.hidden = true;
  game.startCountdown();
});

btnRetry.addEventListener("click", () => {
  btnRetry.hidden = true;
  game.startCountdown();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") return;
  if (!debugMode) return;
  if (e.key === "w" || e.key === "W") face.debugAction = FaceAction.WINK_LEFT;
  if (e.key === "m" || e.key === "M") face.debugAction = FaceAction.MOUTH_OPEN;
  if (e.key === "e" || e.key === "E") face.debugAction = FaceAction.EYES_WIDE;
});
document.addEventListener("keyup", (e) => {
  if (!debugMode) return;
  if (["w", "W", "m", "M", "e", "E"].includes(e.key)) face.debugAction = FaceAction.NONE;
});

function loop(ts) {
  if (!game._lastTs) game._lastTs = ts;
  let dt = (ts - game._lastTs) / 1000;
  game._lastTs = ts;
  if (dt > 0.05) dt = 0.05;

  game.update(dt, ts);
  game.draw();

  btnStart.hidden = game.phase !== "title";
  btnRetry.hidden = game.phase !== "gameover";

  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

window.addEventListener("beforeunload", () => face.stop());

/**
 * 브라우저 웹캠 + MediaPipe Face Landmarker 표정 인식
 */
import { CONFIG, FaceAction } from "./config.js";

const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];
const MOUTH_TOP = 13;
const MOUTH_BOTTOM = 14;
const FACE_TOP = 10;
const FACE_BOTTOM = 152;

function dist(lm, a, b, w, h) {
  const ax = lm[a].x * w;
  const ay = lm[a].y * h;
  const bx = lm[b].x * w;
  const by = lm[b].y * h;
  return Math.hypot(ax - bx, ay - by);
}

function eyeAspectRatio(lm, idx, w, h) {
  const v1 = dist(lm, idx[1], idx[5], w, h);
  const v2 = dist(lm, idx[2], idx[4], w, h);
  const horiz = dist(lm, idx[0], idx[3], w, h);
  return horiz < 1e-6 ? 0 : (v1 + v2) / (2 * horiz);
}

function mouthOpenRatio(lm, w, h) {
  const mouth = dist(lm, MOUTH_TOP, MOUTH_BOTTOM, w, h);
  const faceH = dist(lm, FACE_TOP, FACE_BOTTOM, w, h);
  return faceH < 1e-6 ? 0 : mouth / faceH;
}

class ActionSmoother {
  constructor(need) {
    this.need = need;
    this.wink = [];
    this.mouth = [];
    this.eyes = [];
  }

  reset() {
    this.wink = [];
    this.mouth = [];
    this.eyes = [];
  }

  push(arr, val) {
    arr.push(val);
    while (arr.length > this.need) arr.shift();
    return arr.length === this.need && arr.reduce((a, b) => a + b, 0) >= this.need;
  }

  update(wink, mouth, eyes) {
    if (this.push(this.wink, wink)) return FaceAction.WINK_LEFT;
    if (this.push(this.mouth, mouth)) return FaceAction.MOUTH_OPEN;
    if (this.push(this.eyes, eyes)) return FaceAction.EYES_WIDE;
    return FaceAction.NONE;
  }
}

export class FaceTracker {
  constructor(videoEl) {
    this.video = videoEl;
    this.status = "init"; // init | ok | no_face | no_camera | loading
    this.action = FaceAction.NONE;
    this.landmarker = null;
    this.smoother = new ActionSmoother(CONFIG.FACE.CONFIRM_FRAMES);
    this.earBaseline = null;
    this._lastDetect = 0;
    this.debugAction = FaceAction.NONE;
    this.debugMode = false;
  }

  async init() {
    this.status = "loading";
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      this.video.srcObject = stream;
      await this.video.play();
    } catch {
      this.status = "no_camera";
      return false;
    }

    try {
      const { FaceLandmarker, FilesetResolver } = await import(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm"
      );
      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
      );
      this.landmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath:
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
          delegate: "GPU",
        },
        runningMode: "VIDEO",
        numFaces: 1,
      });
    } catch (e) {
      console.warn("MediaPipe load failed", e);
      this.status = "ok";
      return true;
    }

    this.status = "no_face";
    return true;
  }

  stop() {
    const stream = this.video.srcObject;
    if (stream) stream.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    if (this.landmarker) {
      this.landmarker.close();
      this.landmarker = null;
    }
  }

  tick(now) {
    if (this.debugMode) {
      this.action = this.debugAction;
      this.status = "ok";
      return;
    }
    if (this.status === "no_camera" || this.status === "loading") return;
    if (!this.landmarker || now - this._lastDetect < CONFIG.FACE.DETECT_INTERVAL_MS) return;
    this._lastDetect = now;

    if (this.video.readyState < 2) return;

    const results = this.landmarker.detectForVideo(this.video, now);
    if (!results.faceLandmarks?.length) {
      this.status = "no_face";
      this.action = FaceAction.NONE;
      this.smoother.reset();
      return;
    }

    this.status = "ok";
    const lm = results.faceLandmarks[0];
    const w = this.video.videoWidth;
    const h = this.video.videoHeight;

    const leftEar = eyeAspectRatio(lm, LEFT_EYE, w, h);
    const rightEar = eyeAspectRatio(lm, RIGHT_EYE, w, h);
    const mouthRatio = mouthOpenRatio(lm, w, h);
    const avgEar = (leftEar + rightEar) / 2;

    if (this.earBaseline === null) this.earBaseline = avgEar;
    else if (avgEar > 0.05) this.earBaseline = this.earBaseline * 0.95 + avgEar * 0.05;

    const wink = leftEar < CONFIG.FACE.BLINK_THRESHOLD && rightEar > CONFIG.FACE.EYE_OPEN_MIN;
    const mouth = mouthRatio > CONFIG.FACE.MOUTH_OPEN_THRESHOLD;
    const eyesWide =
      this.earBaseline !== null &&
      avgEar > this.earBaseline * CONFIG.FACE.EYE_OPEN_THRESHOLD &&
      !wink &&
      !mouth;

    this.action = this.smoother.update(wink, mouth, eyesWide);
  }

  getActionLabel() {
    const map = {
      [FaceAction.NONE]: "—",
      [FaceAction.WINK_LEFT]: "😉 WINK",
      [FaceAction.MOUTH_OPEN]: "👄 MOUTH OPEN",
      [FaceAction.EYES_WIDE]: "👀 EYES WIDE",
    };
    return map[this.action] || "—";
  }

  getStatusLabel() {
    if (this.status === "ok") return "FACE DETECTED";
    if (this.status === "no_face") return "NO FACE";
    if (this.status === "no_camera") return "NO CAMERA";
    if (this.status === "loading") return "LOADING…";
    return "—";
  }
}

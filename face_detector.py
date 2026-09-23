"""
카메라(OpenCV) + MediaPipe Face Mesh 표정 인식
"""

from __future__ import annotations

import sys
from collections import deque
from enum import Enum
from typing import Deque, Optional

import pygame

import config

_cv2 = None
_mp_face_mesh = None


def _import_cv2():
    global _cv2
    if _cv2 is None:
        import cv2

        _cv2 = cv2
    return _cv2


def _get_face_mesh():
    """MediaPipe Face Mesh (0.10.x solutions API)"""
    global _mp_face_mesh
    if _mp_face_mesh is not None:
        return _mp_face_mesh
    try:
        import mediapipe as mp

        if not hasattr(mp, "solutions"):
            return None
        _mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return _mp_face_mesh
    except (ImportError, AttributeError, RuntimeError):
        return None


# Face Mesh 랜드마크 인덱스
_LEFT_EYE = (33, 160, 158, 133, 153, 144)
_RIGHT_EYE = (362, 385, 387, 263, 373, 380)
_MOUTH_TOP = 13
_MOUTH_BOTTOM = 14
_FACE_TOP = 10
_FACE_BOTTOM = 152


class FaceStatus(Enum):
    OK = "face_detected"
    NO_FACE = "no_face"
    NO_CAMERA = "no_camera"


class _ActionSmoother:
    """여러 프레임 연속 감지 시에만 동작 확정"""

    def __init__(self, confirm_frames: int) -> None:
        self._need = confirm_frames
        self._wink: Deque[bool] = deque(maxlen=confirm_frames)
        self._mouth: Deque[bool] = deque(maxlen=confirm_frames)
        self._eyes: Deque[bool] = deque(maxlen=confirm_frames)

    def reset(self) -> None:
        self._wink.clear()
        self._mouth.clear()
        self._eyes.clear()

    def update(self, wink: bool, mouth: bool, eyes: bool) -> str:
        self._wink.append(wink)
        self._mouth.append(mouth)
        self._eyes.append(eyes)

        if len(self._wink) == self._need and sum(self._wink) >= self._need:
            return config.FaceAction.WINK_LEFT
        if len(self._mouth) == self._need and sum(self._mouth) >= self._need:
            return config.FaceAction.MOUTH_OPEN
        if len(self._eyes) == self._need and sum(self._eyes) >= self._need:
            return config.FaceAction.EYES_WIDE
        return config.FaceAction.NONE


class FaceDetector:
    """
    process_frame_if_due()로 카메라·표정을 갱신한다.
    DEBUG MODE: W/M/E 키 시뮬레이션
    """

    def __init__(self, debug_mode: bool = False) -> None:
        self.debug_mode = debug_mode
        self._latest_action = config.FaceAction.NONE
        self._status = FaceStatus.NO_CAMERA if debug_mode else FaceStatus.NO_FACE
        self._preview_surface: Optional[pygame.Surface] = None
        self._cap = None
        self._face_mesh = None
        self._smoother = _ActionSmoother(config.ACTION_CONFIRM_FRAMES)
        self._ear_baseline: Optional[float] = None
        self._mediapipe_ok = False

    def start(self) -> None:
        if self.debug_mode:
            self._status = FaceStatus.OK
            return

        cv2 = _import_cv2()
        index = config.CAMERA_INDEX

        if sys.platform == "win32":
            self._cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(index)

        if not self._cap.isOpened():
            self._release_camera()
            self._status = FaceStatus.NO_CAMERA
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._face_mesh = _get_face_mesh()
        self._mediapipe_ok = self._face_mesh is not None
        self._smoother.reset()
        self._ear_baseline = None
        self._status = FaceStatus.NO_FACE

    def stop(self) -> None:
        self._release_camera()
        if self._face_mesh is not None:
            self._face_mesh.close()
            self._face_mesh = None
        self._preview_surface = None

    def _release_camera(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def process_frame_if_due(self, _dt: float) -> None:
        if self.debug_mode or self._cap is None:
            return

        cv2 = _import_cv2()
        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._status = FaceStatus.NO_CAMERA
            self._latest_action = config.FaceAction.NONE
            return

        if config.CAMERA_MIRROR:
            frame = cv2.flip(frame, 1)

        if self._mediapipe_ok and self._face_mesh is not None:
            self._detect_actions(frame, cv2)
        else:
            self._status = FaceStatus.OK

        self._preview_surface = self._frame_to_surface(frame, cv2)

    def _detect_actions(self, frame, cv2) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        result = self._face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            self._status = FaceStatus.NO_FACE
            self._latest_action = config.FaceAction.NONE
            self._smoother.reset()
            return

        self._status = FaceStatus.OK
        lm = result.multi_face_landmarks[0].landmark

        left_ear = _eye_aspect_ratio(lm, _LEFT_EYE, w, h)
        right_ear = _eye_aspect_ratio(lm, _RIGHT_EYE, w, h)
        mouth_ratio = _mouth_open_ratio(lm, w, h)
        avg_ear = (left_ear + right_ear) / 2.0

        if self._ear_baseline is None:
            self._ear_baseline = avg_ear
        elif avg_ear > 0.05:
            self._ear_baseline = self._ear_baseline * 0.95 + avg_ear * 0.05

        wink = (
            left_ear < config.BLINK_THRESHOLD
            and right_ear > config.EYE_OPEN_MIN
        )
        mouth = mouth_ratio > config.MOUTH_OPEN_THRESHOLD
        eyes_wide = (
            self._ear_baseline is not None
            and avg_ear > self._ear_baseline * config.EYE_OPEN_THRESHOLD
            and not wink
            and not mouth
        )

        self._latest_action = self._smoother.update(wink, mouth, eyes_wide)

    def _frame_to_surface(self, frame, cv2) -> pygame.Surface:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        return pygame.image.frombuffer(rgb.tobytes(), (w, h), "RGB")

    def handle_debug_key(self, key: int) -> None:
        if not self.debug_mode:
            return
        if key == pygame.K_w:
            self._latest_action = config.FaceAction.WINK_LEFT
        elif key == pygame.K_m:
            self._latest_action = config.FaceAction.MOUTH_OPEN
        elif key == pygame.K_e:
            self._latest_action = config.FaceAction.EYES_WIDE

    def release_action_on_key_up(self, key: int) -> None:
        if not self.debug_mode:
            return
        if key in (pygame.K_w, pygame.K_m, pygame.K_e):
            self._latest_action = config.FaceAction.NONE

    @property
    def latest_action(self) -> str:
        return self._latest_action

    @property
    def status(self) -> FaceStatus:
        return self._status

    @property
    def preview_surface(self) -> Optional[pygame.Surface]:
        return self._preview_surface

    def action_display_label(self) -> str:
        mapping = {
            config.FaceAction.NONE: "—",
            config.FaceAction.WINK_LEFT: "😉 WINK",
            config.FaceAction.MOUTH_OPEN: "👄 MOUTH OPEN",
            config.FaceAction.EYES_WIDE: "👀 EYES WIDE",
        }
        return mapping.get(self._latest_action, "—")

    def status_label(self) -> str:
        if self._status == FaceStatus.OK:
            return "FACE DETECTED"
        if self._status == FaceStatus.NO_FACE:
            return "NO FACE"
        return "NO CAMERA"


def _dist(lm, a: int, b: int, w: int, h: int) -> float:
    ax, ay = lm[a].x * w, lm[a].y * h
    bx, by = lm[b].x * w, lm[b].y * h
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _eye_aspect_ratio(lm, indices, w: int, h: int) -> float:
    """눈 세로/가로 비율 — 작을수록 감긴 눈"""
    v1 = _dist(lm, indices[1], indices[5], w, h)
    v2 = _dist(lm, indices[2], indices[4], w, h)
    horiz = _dist(lm, indices[0], indices[3], w, h)
    if horiz < 1e-6:
        return 0.0
    return (v1 + v2) / (2.0 * horiz)


def _mouth_open_ratio(lm, w: int, h: int) -> float:
    """입술 간격 / 얼굴 높이"""
    mouth = _dist(lm, _MOUTH_TOP, _MOUTH_BOTTOM, w, h)
    face_h = _dist(lm, _FACE_TOP, _FACE_BOTTOM, w, h)
    if face_h < 1e-6:
        return 0.0
    return mouth / face_h

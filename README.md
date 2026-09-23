# FACE FOOD FIGHT

하늘에서 떨어지는 음식을 **표정**으로 잡는 Raspberry Pi 5 + USB 웹캠 게임입니다.

## 현재 구현 단계

| 단계 | 내용 | 상태 |
|------|------|------|
| 1 | Pygame 음식 낙하, 시작/카운트다운, HUD | ✅ |
| 2 | 카테고리별 점수 판정 | 예정 |
| 3 | OpenCV 내장/USB 카메라 미리보기 | ✅ |
| 4~ | MediaPipe 표정, 효과음, 팀 순위 | 예정 |

## 웹版 (Vercel 링크 배포)

브라우저에서 링크로 플레이하는 버전은 **`web/`** 폴더입니다.

```bash
cd web
npx serve .
# http://localhost:3000 접속 → 카메라 허용 → 게임 시작
```

Vercel 배포: 저장소 연결 후 Deploy (자세한 내용은 `web/DEPLOY.md`).

## PC에서 빠르게 실행 (Windows / macOS / Linux)

```bash
cd project   # 이 README가 있는 폴더
python -m venv venv

# Windows
venv\Scripts\activate

# Raspberry Pi OS / Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

**노트북 내장 카메라**는 USB 없이 위 명령만으로 연결됩니다 (`config.py`의 `CAMERA_INDEX = 0`).  
Windows에서 권한 팝업이 뜨면 **카메라 허용**을 선택하세요. 영상이 안 나오면:

```bash
python main.py --camera-index 1
```

카메라 없이 게임 로직만 보려면:

```bash
python main.py --debug
```

- **W** — 윙크 (패스트푸드용, 2단계부터 판정)
- **M** — 입 벌리기 (과일)
- **E** — 눈 크게 뜨기 (채소)
- **ESC** — 종료

## Raspberry Pi 5 설치 (Raspberry Pi OS)

### 1. 시스템 패키지

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  v4l-utils
```

USB 웹캠 확인:

```bash
v4l2-ctl --list-devices
```

### 2. Python 가상환경

```bash
cd ~/FACE_FOOD_FIGHT   # 프로젝트 경로
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

MediaPipe는 Pi 아키텍처에 따라 wheel 설치가 실패할 수 있습니다. 실패 시 [MediaPipe 공식 문서](https://developers.google.com/mediapipe)의 Linux/ARM 안내를 참고하세요. **1단계만** 플레이할 때는 `pygame`만 설치해도 됩니다:

```bash
pip install pygame
```

### 3. 실행

HDMI 모니터에 연결한 뒤:

```bash
source venv/bin/activate
python3 main.py
```

전체 화면이 필요하면 `config.py`의 `SCREEN_WIDTH` / `SCREEN_HEIGHT`를 모니터 해상도에 맞게 조정하세요.

### 4. 자동 시작 (선택)

`~/.config/autostart/face-food-fight.desktop` 등으로 `main.py`를 등록할 수 있습니다.

## 프로젝트 구조

```
project/
├── main.py           # 진입점, --debug 옵션
├── game.py           # 화면 상태, 루프, UI
├── food.py           # 음식 생성·낙하·이미지/이모지
├── face_detector.py  # 카메라·얼굴 동작 (단계별 확장)
├── config.py         # 해상도, 난이도, 음식·동작 데이터
├── assets/
│   ├── foods/        # burger.png 등 (없으면 이모지)
│   ├── sounds/
│   └── images/
├── requirements.txt
└── README.md
```

## 설정 변경

`config.py` 상단 근처에서 다음을 조정할 수 있습니다.

- `GAME_DURATION_SEC` — 플레이 시간 (기본 60초)
- `DIFFICULTY_TIERS` — 구간별 낙하 속도·스폰 간격
- `FOOD_CATEGORIES` / `SPECIAL_FOODS` — 음식·필요 동작 추가
- `BLINK_THRESHOLD`, `MOUTH_OPEN_THRESHOLD`, `EYE_OPEN_THRESHOLD` — 얼굴 판정 (4~5단계)

## 1단계 조작

1. **게임 시작** 클릭
2. 3초 카운트다운 후 60초 동안 음식이 위에서 떨어짐
3. 노란 **판정 구역**에 들어온 음식에 동작 안내 표시 (점수 판정은 2단계)
4. 시간 종료 후 간단한 GAME OVER 화면

## 라이선스

팀 내부/교육용으로 자유롭게 수정하세요.

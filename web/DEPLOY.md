# FACE FOOD FIGHT — Vercel 웹 배포

브라우저에서 **링크만으로** 플레이하는 버전입니다. (웹캠 필요, **HTTPS** 필수)

## 1. Vercel에 올리기 (GitHub 연동)

1. GitHub에 이 저장소를 push합니다.
2. [vercel.com](https://vercel.com) → **Add New Project** → 저장소 선택
3. 설정:
   - **Root Directory**: 비워 두거나 프로젝트 루트
   - **Output Directory**: `web` (또는 `vercel.json`이 있으면 자동)
   - **Build Command**: 없음
4. **Deploy** → `https://프로젝트명.vercel.app` 주소가 생성됩니다.

## 2. CLI로 배포

```bash
npm i -g vercel
cd "프로젝트/Rasp"
vercel
# 프로덕션: vercel --prod
```

## 3. 로컬에서 웹版 테스트

카메라 API는 **localhost** 또는 **HTTPS**에서만 동작합니다.

```bash
cd web
npx serve .
# 또는 Python 3
python -m http.server 8080
```

브라우저에서 `http://localhost:8080` 접속 → 카메라 허용 → **게임 시작**

## 4. URL 옵션

| URL | 설명 |
|-----|------|
| `/` | 일반 (웹캠 + MediaPipe) |
| `/?debug=1` | W/M/E 키로 표정 테스트 (카메라 없음) |

## 5. Raspberry Pi Python版과 차이

| | 웹 (Vercel) | Python (Pi) |
|--|-------------|-------------|
| 실행 | 브라우저 링크 | `python main.py` |
| 카메라 | PC/폰 브라우저 | USB/내장 cam |
| 오프라인 | ❌ (모델 CDN) | ✅ |

## 6. 문제 해결

- **카메라 안 됨**: 주소가 `https://` 또는 `localhost`인지 확인
- **얼굴 인식 느림**: GPU 가속 브라우저(Chrome) 권장
- **MediaPipe 로드 실패**: 방화벽/CDN 차단 여부 확인

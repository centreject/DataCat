# AI 모델 서비스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spring이 호출하는 내부 모델 서비스(이미지 인식 · STT · 요약/용건 분류)를 API v1.3 계약대로 구현하고, 8GB VRAM(lite)과 24GB(full) 양쪽에서 돌아가게 한다.

**Architecture:** 단일 FastAPI 프로세스가 기동 시 세 모델을 로딩한다(`ModelRegistry`). 라우트는 모델 구현체가 아니라 Protocol(`VisionModel`/`SpeechModel`/`LanguageModel`)에만 의존하므로, 단위 테스트는 가짜 모델로 CPU에서 돌고 실제 모델 테스트는 `@pytest.mark.gpu`로 분리한다. 음성은 메모리에서만 처리한다(Zero-Storage).

**Tech Stack:** WSL2 Ubuntu, Python 3.11, FastAPI, pydantic-settings, Ultralytics(YOLO11s + YOLOE), faster-whisper, transformers(+bitsandbytes), PyTorch CUDA, pytest, Docker.

**Spec:** `API_v1_4.md` 4장, 7장, 12장, 16장 (모델 서비스 부분; 계획 작성 당시 v1.3, 이 계획의 결정을 반영해 v1.4로 개정). 모델 선정 근거와 아래 결정 사항은 2026-09-27 팀 대화·검토(grilling) 결과를 따른다.

## Global Constraints

**저장소 · 협업**
- 모노레포. 모델 서비스 코드는 모두 `model-service/` 아래에 둔다. 루트 `docker-compose.yml`은 인태님 관리이며, 모델 서비스 블록은 PR로 제안만 한다.
- 작업 브랜치는 `feature/ai-model`. `main`은 직접 수정하지 않는다.
- main 병합: **Phase가 끝날 때마다** `feature/ai-model` → main PR (Phase 1 끝, Phase 2 끝). 다른 팀원 코드는 병합된 main에서 받아 연동 테스트한다.
- API 명세 수정은 코드보다 먼저 **명세만 담은 작은 PR**로 올린다. 모든 PR은 올리기 전에 민중님 확인을 받는다.

**API 계약**
- Base path: `/internal/v1`. 엔드포인트: `POST /vision/detect`, `POST /speech/transcribe`, `POST /language/analyze`, `POST /audio/process`, 추가로 `GET /health`.
- 이미지 입력: `multipart/form-data` 필드 `image`, `image/jpeg`.
- 음성 입력: `multipart/form-data` 필드 `audio`, `audio/wav`, **PCM 16-bit, 16kHz, Mono**. 이외 형식은 400.
- 오류 응답: `{"code": "...", "message": "..."}`. 400 잘못된 요청, 500 내부 오류, 503 모델 사용 불가.
- Vision 응답은 Phase 1에서 `label`, `confidence`만. `label` 허용 값: `person`, `package` (`box`는 쓰지 않음). `bbox`/`facingCamera`는 인태님·덕민님 동의 전까지 넣지 않는다.
- `package` 범위: 택배 박스, 비닐 택배봉투, 배달 음식 봉지·용기, 보냉백(프레시백)을 모두 `package` 하나로. 사람이 들고 있는 물건도 구분하지 않는다.
- `purpose` 허용 값: `DELIVERY`, `INSPECTION`, `VISIT`, `ETC` (덕민님 승인 전 초안). 목록 밖 값은 `ETC`.
- `summary`: 명사형, 공백 포함 최대 20자. 초과 시 `s[:19] + "…"` (Spring과 동일 규칙).
- 빈 전사(발화 없음): `transcript=""`, `summary=""`, `purpose="ETC"`. 표시 문구는 Spring·앱이 정한다.
- Zero-Storage: 음성 바이트를 디스크(임시 파일 포함)에 쓰지 않는다. 로그에도 음성 데이터를 남기지 않는다.

**실행 · 성능**
- 프로필: 환경변수 `MODEL_PROFILE` = `full` | `lite` (기본 `lite`).
- uvicorn worker는 1개. 각 모델 래퍼는 추론을 `threading.Lock`으로 직렬화한다(GPU 동시 접근 방지).
- 지연 목표 — **full(시연 PC, 3090)**: `/audio/process` p95 ≤ 2.0초(5초 발화), `/vision/detect` p95 ≤ 0.3초. **lite(8GB)**: 세 모델 전체 로딩 성공 + `/audio/process` p95 ≤ 4.0초.
- 정확도 목표(full 기준, 잠정 — 첫 측정 후 조정): 사람 재현율 ≥ 95%, 택배 재현율 ≥ 85%, STT CER ≤ 15%, 용건 정확도 ≥ 90%, 요약 20자 초과 0%.

**데이터**
- 초기 테스트·평가 데이터는 공개 이미지와 TTS로 생성한 음성으로 만든다. 팀원 얼굴·목소리 등 실데이터는 커밋하지 않는다(`.gitignore`된 `data/` 또는 공유 드라이브).
- GPU 테스트와 평가 스크립트는 데이터 파일이 없으면 실패가 아니라 skip한다.

## Review Focus

1. **무음·잡음만 있는 음성** — Whisper가 "시청해 주셔서 감사합니다" 같은 문장을 지어내지 말고 빈 전사(`""`)를 돌려야 한다. → Task 5 필터 테스트, Task 5 GPU 테스트(무음 WAV).
2. **Pi 설정 실수로 온 스테레오/44.1kHz/32-bit WAV** — 크래시가 아니라 400 `INVALID_AUDIO`와 무엇이 틀렸는지 알려주는 메시지. → Task 2.
3. **LLM이 JSON이 아닌 출력, 목록 밖 purpose, 20자 초과 요약을 낼 때** — 규칙 기반 폴백 또는 정규화로 항상 계약에 맞는 응답. → Task 6, Task 7.
4. **모델 로딩 중에 들어온 요청** — 503 `MODEL_NOT_READY`, 서버는 죽지 않음. → Task 1.
5. **박스가 아닌 택배(비닐봉투·배달 음식 봉지·보냉백)** — 박스만 잡고 이것들을 놓치면 "물건 도착"이 누락된다. → Task 4 GPU 테스트, Task 10 비전 평가셋에 유형별 폴더.

---

## 파일 구조

```text
model-service/
├─ pyproject.toml            # 의존성, pytest 설정(gpu 마커)
├─ README.md                 # 실행법, 프로필, 명세 대비 변경점
├─ Dockerfile
├─ .gitignore                # data/, bench 임시 파일, 가중치
├─ app/
│  ├─ main.py                # create_app(), lifespan, 라우터 등록
│  ├─ config.py              # Settings, 프로필별 모델 설정
│  ├─ errors.py              # ApiError + 핸들러
│  ├─ schemas.py             # 요청/응답 pydantic 모델
│  ├─ protocols.py           # VisionModel / SpeechModel / LanguageModel
│  ├─ registry.py            # ModelRegistry, load_registry(settings)
│  ├─ media.py               # decode_jpeg, decode_wav (메모리 전용)
│  ├─ pipeline.py            # analyze_transcript, process_audio
│  ├─ routes.py              # 5개 엔드포인트
│  ├─ vision/yolo.py         # YoloVision
│  ├─ speech/filters.py      # clean_segments
│  ├─ speech/whisper.py      # WhisperSpeech
│  ├─ language/normalize.py  # truncate_summary, parse_llm_output
│  ├─ language/rules.py      # rule_analyze
│  └─ language/qwen.py       # QwenLanguage, build_messages
├─ tests/                    # 단위(가짜 모델) + gpu 마커 통합 테스트
│  └─ fixtures/              # make_fixtures.py (합성 wav/jpg 생성)
├─ bench/benchmark.py        # VRAM·지연 측정
├─ eval/                     # 정확도 평가 스크립트, 라벨(jsonl), 데이터 준비 스크립트
└─ data/                     # (gitignore) 공개·생성·실제 이미지/음성
```

---

### Task 0: 개발 환경 준비 (민중님이 직접 실행, 이 PC: RTX 3060 Ti 8GB)

**Files:** 없음 (로컬 환경)

- [ ] **Step 1:** PowerShell(관리자)에서 `wsl --install -d Ubuntu-22.04` → 재부팅 → Ubuntu 사용자 생성. 확인: WSL 안에서 `nvidia-smi`에 3060 Ti 표시(Windows 드라이버가 GPU를 WSL에 전달하므로 WSL 안에 드라이버를 설치하지 않는다).
- [ ] **Step 2:** WSL에서 Python 3.11 **정식판**을 deadsnakes PPA로 설치(Ubuntu 22.04 기본 저장소의 `python3.11`은 `3.11.0rc1` 릴리스 후보라 쓰지 않는다): `sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt update && sudo apt install -y python3.11 python3.11-venv python3.11-dev git`. 확인: `python3.11 --version` → `Python 3.11.x`(rc 아님). 저장소 전용 커밋 계정 설정(`git config user.name/user.email`). 그리고 `git clone https://github.com/centreject/DataCat.git ~/DataCat && cd ~/DataCat && git checkout feature/ai-model`. 이 세션의 작업 폴더를 `\\wsl$\Ubuntu-22.04\home\<user>\DataCat`로 옮긴다(이전 임시 clone은 폐기).
- [ ] **Step 3:** `python3.11 -m venv model-service/.venv`, `pip install torch --index-url https://download.pytorch.org/whl/cu124`. 확인: `python -c "import torch;print(torch.cuda.is_available())"` → `True`.
- [ ] **Step 4:** Docker Desktop 설치(WSL2 백엔드, Ubuntu 통합 켬). Task 11 전까지만 끝내면 된다. 확인: `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`.

---

### Task 1: 서비스 뼈대 — 설정, 오류 형식, 레지스트리, `/health`

**Files:**
- Create: `model-service/pyproject.toml`, `.gitignore`, `app/main.py`, `app/config.py`, `app/errors.py`, `app/protocols.py`, `app/registry.py`, `app/schemas.py`, `app/routes.py`
- Test: `tests/test_app.py`, `tests/conftest.py`

**Interfaces:**
- Produces:
  - `Settings(BaseSettings)`: `model_profile: Literal["full","lite"]="lite"`, `person_conf: float=0.4`, `package_conf: float=0.3`, `package_prompts: list[str]` (Task 4에서 값 확정), `stt_model: str="large-v3-turbo"`, `llm_model: str="Qwen/Qwen3-4B-Instruct-2507"`, `llm_max_new_tokens: int=64`. 프로필 파생값은 프로퍼티: `stt_compute_type` (`full`→`"float16"`, `lite`→`"int8_float16"`), `llm_quantize_4bit` (`lite`→`True`).
  - `ApiError(status: int, code: str, message: str)`; `install_error_handlers(app)`. 코드: `INVALID_IMAGE`(400), `INVALID_AUDIO`(400), `INVALID_REQUEST`(400), `MODEL_NOT_READY`(503), `INFERENCE_FAILED`(500). FastAPI 검증 오류도 `INVALID_REQUEST` 형식으로 변환.
  - `protocols.py`: `VisionModel.detect(image: PIL.Image.Image) -> list[Detection]`, `SpeechModel.transcribe(audio: np.ndarray) -> str` (float32, 16kHz), `LanguageModel.analyze(transcript: str) -> Analysis`.
  - `schemas.py`: `Detection(label: Literal["person","package"], confidence: float)`, `DetectResponse(detections: list[Detection])`, `TranscribeResponse(transcript: str)`, `AnalyzeRequest(transcript: str)`, `Analysis(summary: str, purpose: Literal["DELIVERY","INSPECTION","VISIT","ETC"])`, `AudioProcessResponse(transcript: str, purpose: str, summary: str)`.
  - `ModelRegistry` dataclass: `vision`, `stt`, `language` (각각 Optional), `ready: bool`. `load_registry(settings) -> ModelRegistry` (실제 모델은 Task 4·5·7에서 채움; 이 태스크에선 빈 레지스트리).
  - `create_app(registry_factory: Callable[[Settings], ModelRegistry] = load_registry) -> FastAPI` — lifespan에서 팩토리를 **백그라운드 스레드**로 실행해 로딩 중에도 `/health`가 응답하게 한다. `app.state.registry`에 저장.
  - `routes.py`: `require(registry, name) -> model` — 준비 안 됐으면 `ApiError(503,"MODEL_NOT_READY",...)`.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_app.py`)
  - `test_health_reports_loading_then_ok`: 팩토리가 `threading.Event`를 기다리게 한 앱 → `GET /health` = `{"status":"loading","profile":"lite"}`; 이벤트 set 후 → `{"status":"ok","profile":"lite"}`.
  - `test_detect_while_loading_returns_503`: 로딩 중 `POST /internal/v1/vision/detect` → 503, 본문 `{"code":"MODEL_NOT_READY","message":...}`.
  - `test_validation_error_uses_error_format`: `POST /internal/v1/language/analyze` 본문 `{}` → 400, `code == "INVALID_REQUEST"`.
  - `test_profile_derived_settings`: `Settings(model_profile="full").stt_compute_type == "float16"`, `Settings().llm_quantize_4bit is True`.
- [ ] **Step 2:** `pytest tests/test_app.py -v` → FAIL (모듈 없음)
- [ ] **Step 3:** 위 Interfaces대로 구현. `pyproject.toml`에 `[tool.pytest.ini_options] markers = ["gpu: needs CUDA and real weights"]`, 기본 `addopts = "-m 'not gpu'"`. `.gitignore`에 `data/`, `.venv/`, `*.pt`, `bench/results/*.tmp`.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): app skeleton, error format, health, profiles`

---

### Task 2: 입력 디코딩 — JPEG, WAV(메모리 전용)

**Files:**
- Create: `app/media.py`, `tests/fixtures/make_fixtures.py`
- Test: `tests/test_media.py`

**Interfaces:**
- Produces: `decode_jpeg(data: bytes) -> PIL.Image.Image` (RGB), `decode_wav(data: bytes) -> np.ndarray` (float32, [-1,1], 1차원). 표준 라이브러리 `wave` + `io.BytesIO`만 사용.
- `make_fixtures.py`: `tone_wav(seconds, rate=16000, channels=1, sampwidth=2) -> bytes`, `silence_wav(seconds) -> bytes`, `tiny_jpeg() -> bytes` — 테스트에서 import해서 씀(파일 커밋 불필요).

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_decode_wav_ok`: 1초 16k mono 16-bit → `shape == (16000,)`, `dtype == float32`, `abs().max() <= 1.0`.
  - `test_decode_wav_rejects_stereo` / `_rejects_44100` / `_rejects_32bit`: 각각 `ApiError` status 400, code `INVALID_AUDIO`, message에 각각 `"mono"`, `"16000"`, `"16-bit"` 포함.
  - `test_decode_wav_rejects_garbage`: `b"not a wav"` → `INVALID_AUDIO`.
  - `test_decode_wav_rejects_empty`: 0프레임 WAV → `INVALID_AUDIO`.
  - `test_decode_jpeg_ok` / `test_decode_jpeg_rejects_png`: PNG 바이트 → `INVALID_IMAGE`.
- [ ] **Step 2:** `pytest tests/test_media.py -v` → FAIL
- [ ] **Step 3:** 구현. JPEG는 `Image.open(...).format == "JPEG"` 확인 후 `.convert("RGB")`.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): in-memory JPEG/WAV decoding with validation`

---

### Task 3: `/vision/detect` 라우트 (가짜 모델로)

**Files:**
- Modify: `app/routes.py`
- Test: `tests/test_vision.py`

**Interfaces:**
- Consumes: `decode_jpeg`, `require`, `DetectResponse`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_detect_route_returns_contract`: 가짜 VisionModel이 `[Detection(label="person", confidence=0.94)]` 반환 → 응답 `{"detections":[{"label":"person","confidence":0.94}]}` (키가 정확히 이 둘).
  - `test_detect_route_empty`: 가짜가 `[]` → `{"detections": []}`.
  - `test_detect_route_rejects_non_jpeg` → 400 `INVALID_IMAGE`.
  - `test_detect_route_missing_field`: `image` 필드 없이 요청 → 400 `INVALID_REQUEST`.
- [ ] **Step 2:** `pytest tests/test_vision.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): vision detect endpoint`

---

### Task 4: 실제 비전 모델 `YoloVision` (Phase 1 마감 대상)

**Files:**
- Create: `app/vision/yolo.py`, `eval/prepare_images.py`
- Modify: `app/registry.py` (`load_registry`가 vision 로딩), `app/config.py` (`package_prompts` 기본값)
- Test: `tests/test_vision_gpu.py` (`@pytest.mark.gpu`)

**Interfaces:**
- Consumes: `VisionModel`, `Detection`, `Settings`.
- Produces: `YoloVision(settings: Settings)` implements `VisionModel`.
  - 사람: `yolo11s.pt` (COCO) 클래스 0(person)만, `conf >= settings.person_conf`.
  - 택배: `yoloe-11s-seg.pt`에 `set_classes(settings.package_prompts)`; 기본값 `["cardboard box", "parcel", "plastic mailer bag", "shopping bag", "food delivery bag", "takeout container", "insulated cooler bag"]` → 모두 `package`로 매핑, `conf >= settings.package_conf`. 파인튜닝 가중치가 생기면 설정값 `package_weights`로 교체(후속 계획).
  - 같은 label이 여러 개면 모두 반환(Spring은 존재 여부만 본다). 추론 fp16, `threading.Lock`으로 직렬화.
- `eval/prepare_images.py`: Open Images / COCO에서 person, box, plastic bag, 음식 용기 이미지와 사람 없는 실내 복도 이미지를 `data/images/<person|package_box|package_bag|package_food|package_cooler|empty>/`로 받는 스크립트.

- [ ] **Step 1:** `prepare_images.py` 구현 후 실행 → 폴더별 최소 30장.
- [ ] **Step 2: 실패하는 GPU 테스트 작성** — 폴더별로 대표 이미지 1장씩 읽음, 파일 없으면 `pytest.skip`.
  - `person/` → `person` 포함.
  - `package_box/`, `package_bag/`, `package_food/`, `package_cooler/` → 각각 `package` 포함.
  - `empty/` → `detections == []`.
- [ ] **Step 3:** `pytest -m gpu tests/test_vision_gpu.py -v` → FAIL
- [ ] **Step 4:** 구현.
- [ ] **Step 5:** `pytest -m gpu tests/test_vision_gpu.py -v` → PASS. 실패 유형이 있으면 `package_prompts`·임계값을 조정하고 기본값에 반영.
- [ ] **Step 6:** Commit — `feat(model-service): YOLO11 person + YOLOE package detector`
- [ ] **비상안(기록만):** YOLOE가 Phase 1 안에 목표에 못 미치면, Spring 규칙 "사람 없음 + ToF 감지 = 물건 도착"으로 대체 가능하다고 인태님께 알린다.

---

### Task 5: STT — 환각 필터, `/speech/transcribe`, `WhisperSpeech`

**Files:**
- Create: `app/speech/filters.py`, `app/speech/whisper.py`
- Modify: `app/routes.py`, `app/registry.py`
- Test: `tests/test_speech.py`, `tests/test_speech_gpu.py`

**Interfaces:**
- Consumes: `decode_wav`, `SpeechModel`, `TranscribeResponse`.
- Produces:
  - `clean_segments(segments: Iterable[tuple[str, float]], max_no_speech_prob: float = 0.6) -> str` — `(text, no_speech_prob)`. no_speech_prob 초과 세그먼트와 `HALLUCINATION_PHRASES`(최소: `"시청해 주셔서 감사합니다"`, `"시청해주셔서 감사합니다"`, `"구독과 좋아요"`, `"MBC 뉴스"`)를 포함하는 세그먼트를 버리고 공백 하나로 이어 `strip()`.
  - `WhisperSpeech(settings)` — `faster_whisper.WhisperModel(settings.stt_model, device="cuda", compute_type=settings.stt_compute_type)`. `transcribe(audio)` 호출 인자: `language="ko"`, `beam_size=1`, `vad_filter=True`, `condition_on_previous_text=False`, `initial_prompt="택배, 배달, 배송, 검침, 점검, 관리사무소, 방문"`. 결과를 `clean_segments`에 통과.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_clean_drops_hallucination`: `[("택배 왔습니다", 0.1), ("시청해 주셔서 감사합니다", 0.2)]` → `"택배 왔습니다"`.
  - `test_clean_drops_high_no_speech`: `[("음", 0.9)]` → `""`.
  - `test_transcribe_route`: 가짜 SpeechModel이 `"택배 왔습니다."` → `{"transcript": "택배 왔습니다."}`.
  - `test_transcribe_route_rejects_stereo` → 400 `INVALID_AUDIO`.
  - GPU: `test_silence_gives_empty` — `silence_wav(3)` → `""`. `test_korean_tts_sample` — Task 10에서 생성한 `data/audio/tts/delivery_01.wav`(없으면 skip) → `"택배"` 포함.
- [ ] **Step 2:** `pytest tests/test_speech.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` 그리고 `pytest -m gpu tests/test_speech_gpu.py -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): faster-whisper STT with hallucination filter`

---

### Task 6: 언어 — 정규화, 규칙 폴백, `/language/analyze`

**Files:**
- Create: `app/language/normalize.py`, `app/language/rules.py`, `app/pipeline.py`
- Modify: `app/routes.py`
- Test: `tests/test_language.py`

**Interfaces:**
- Consumes: `Analysis`, `AnalyzeRequest`, `LanguageModel`.
- Produces:
  - `truncate_summary(s: str, limit: int = 20) -> str` — `strip()` 후 `len > limit`이면 `s[:limit-1] + "…"`.
  - `parse_llm_output(raw: str) -> Analysis | None` — 첫 `{`~마지막 `}` 구간을 JSON 파싱. 실패하거나 `summary`가 비었으면 `None`. `purpose`는 대문자화, 목록 밖이면 `ETC`. `summary`는 `truncate_summary`.
  - `rule_analyze(transcript: str) -> Analysis` — **LLM 실패 시에만 쓰는 폴백.** 키워드 우선순위 DELIVERY > INSPECTION > VISIT, 없으면 ETC. 키워드: DELIVERY `택배, 배달, 배송, 소포, 음식, 물건`; INSPECTION `검침, 점검, 관리사무소, 관리실, 가스, 소독, 수리, 설치, 공사`; VISIT `친구, 나야, 엄마, 아빠, 언니, 오빠, 형, 누나, 놀러`. summary는 `truncate_summary(transcript)`.
  - `analyze_transcript(model: LanguageModel, transcript: str) -> Analysis` — 빈 전사(공백만 포함) → `Analysis(summary="", purpose="ETC")`, 모델을 부르지 않음. 모델 예외 → `rule_analyze`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_truncate_exact_20_kept`, `test_truncate_21_becomes_19_plus_ellipsis` (결과 길이 20, 끝 `"…"`).
  - `test_parse_valid`, `test_parse_with_surrounding_text` (`"결과: {...} 입니다"`), `test_parse_garbage_none`, `test_parse_unknown_purpose_is_etc` (`"purpose":"FOOD"` → `ETC`), `test_parse_lowercase_purpose` (`"delivery"` → `DELIVERY`).
  - `test_rules_delivery`: `"택배 문 앞에 두고 갑니다"` → `DELIVERY`. `test_rules_inspection`: `"가스 검침 왔습니다"` → `INSPECTION`. `test_rules_etc`: `"안녕하세요"` → `ETC`.
  - `test_empty_transcript_skips_model`: 호출되면 실패하는 가짜 모델 + `"  "` → `Analysis(summary="", purpose="ETC")`.
  - `test_model_exception_falls_back_to_rules`.
  - `test_analyze_route_contract`: 응답 키가 정확히 `{"summary","purpose"}`.
- [ ] **Step 2:** `pytest tests/test_language.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): language normalize, rule fallback, analyze endpoint`

---

### Task 7: 실제 sLM `QwenLanguage`

**Files:**
- Create: `app/language/qwen.py`
- Modify: `app/registry.py`
- Test: `tests/test_qwen.py`, `tests/test_qwen_gpu.py`

**Interfaces:**
- Consumes: `parse_llm_output`, `rule_analyze`, `Settings`.
- Produces:
  - `build_messages(transcript: str) -> list[dict]` — system 프롬프트(역할, purpose 정의 4개, "summary는 공백 포함 20자 이내 **명사형**(예: `택배 문 앞 보관`, `가스 검침 방문`)", "JSON 한 줄만 출력"), few-shot 4개(용건별 1개, summary 모두 명사형), user = transcript.
  - `QwenLanguage(settings)` implements `LanguageModel` — `AutoModelForCausalLM`, `settings.llm_quantize_4bit`이면 `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)`, 아니면 `torch_dtype=torch.bfloat16`. greedy(`do_sample=False`), `max_new_tokens=settings.llm_max_new_tokens`. `parse_llm_output` 결과가 `None`이면 `rule_analyze`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_build_messages_contains_all_purposes`: system 내용에 네 값 모두 포함, 마지막 메시지가 `{"role":"user","content": transcript}`.
  - GPU: `test_qwen_delivery` — `"택배 왔습니다. 문 앞에 놓고 갈게요."` → `purpose == "DELIVERY"`, `len(summary) <= 20`. `test_qwen_inspection` — `"관리사무소에서 소방 점검 나왔습니다"` → `INSPECTION`.
- [ ] **Step 2:** `pytest tests/test_qwen.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` 그리고 `MODEL_PROFILE=lite pytest -m gpu tests/test_qwen_gpu.py -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): Qwen3 analyzer with 4bit lite profile`

---

### Task 8: `/audio/process` 통합 + Zero-Storage 검증

**Files:**
- Modify: `app/pipeline.py`, `app/routes.py`
- Test: `tests/test_audio_process.py`

**Interfaces:**
- Consumes: `decode_wav`, `SpeechModel`, `analyze_transcript`.
- Produces: `process_audio(registry: ModelRegistry, wav: bytes) -> AudioProcessResponse` — decode → transcribe → analyze. 중간 결과를 반환하지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_process_audio_contract`: 가짜 STT `"택배 문 앞에 두고 갑니다."`, 가짜 LM `Analysis("택배 문 앞 보관","DELIVERY")` → 응답이 정확히 `{"transcript","purpose","summary"}`.
  - `test_process_audio_silence`: 가짜 STT `""` → `{"transcript":"","purpose":"ETC","summary":""}`.
  - `test_process_audio_writes_no_files`: `tempfile.mkstemp`, `tempfile.NamedTemporaryFile`, `tempfile.SpooledTemporaryFile`을 호출 시 예외를 던지게 monkeypatch + `tmp_path`를 cwd로 둔 상태에서 요청 → 200, 요청 전후 `tempfile.gettempdir()`와 cwd 파일 목록 동일. (Starlette 업로드가 1MB 이하 WAV를 메모리에 유지함을 이 테스트로 함께 고정; 5초 16k 16-bit ≈ 160KB.)
  - `test_process_audio_stt_not_ready` → 503.
- [ ] **Step 2:** `pytest tests/test_audio_process.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): audio process endpoint with zero-storage guarantee`

---

### Task 9: 벤치마크 — VRAM·지연

**Files:**
- Create: `bench/benchmark.py`, `bench/results/.gitkeep`

**Interfaces:**
- Consumes: `load_registry`, `Settings`, `process_audio`, fixture 생성 함수.
- Produces: CLI `python bench/benchmark.py --profile lite --runs 20` → stdout 마크다운 표 + `bench/results/<GPU이름>_<profile>.json`. 항목: GPU 이름, 총 VRAM, 모델별 로딩 후 `torch.cuda.max_memory_allocated`와 `nvidia-smi` 사용량, 로딩 시간, vision/stt/language/audio-process 각 p50·p95(ms). 첫 1회는 워밍업으로 제외. 표 하단에 해당 프로필의 목표(Global Constraints) 대비 PASS/FAIL 표시.

- [ ] **Step 1:** 구현 후 `python bench/benchmark.py --profile lite --runs 3` 스모크 실행 → 표 출력, JSON 생성.
- [ ] **Step 2:** 이 PC(3060 Ti 8GB)에서 `--profile lite --runs 20`. 판정: 전체 로딩 성공 + audio-process p95 ≤ 4000ms. 실패 시 `llm_model`을 `Qwen/Qwen3-1.7B`로 바꿔 재측정하고 lite 기본값을 결과에 맞게 수정.
- [ ] **Step 3:** 결과 JSON 커밋. Commit — `perf(model-service): VRAM/latency benchmark and 3060Ti lite results`
- [ ] **Step 4:** 시연 PC(3090) 관리자에게 `--profile full --runs 20` 실행 요청 → 결과 JSON을 받아 커밋. 판정: audio-process p95 ≤ 2000ms, vision p95 ≤ 300ms.

---

### Task 10: 평가 데이터 생성 + 정확도 평가

**Files:**
- Create: `eval/purpose_cases.jsonl`, `eval/make_tts_audio.py`, `eval/eval_language.py`, `eval/eval_stt.py`, `eval/eval_vision.py`, `eval/README.md`

**Interfaces:**
- `purpose_cases.jsonl`: 한 줄에 `{"transcript": str, "purpose": str}`. 초기 40건(용건별 10건, 구어체·말줄임·"택배 아니고 관리실에서 왔어요" 같은 반례 포함). 덕민님 분류 기획이 확정되면 100건으로 확장.
- `make_tts_audio.py`: `purpose_cases.jsonl`의 문장을 `edge-tts`(한국어 남·여 음성 각 1개 이상)로 합성 → 16kHz mono 16-bit WAV로 변환 → 복도 잡음(백색 잡음, SNR 10·20dB) 섞은 버전 추가 → `data/audio/tts/<id>.wav` + 정답 `<id>.txt`. 실제 INMP441 녹음이 생기면 `data/audio/real/`에 같은 형식으로 추가.
- `eval_language.py` → 전체 정확도, 용건별 precision/recall, 혼동 행렬, 20자 초과 비율, 폴백 발생 비율. `--rules-only` 옵션.
- `eval_stt.py` → `data/audio/<tts|real>/`별 CER(공백 제거 후 문자 편집거리 / 정답 길이).
- `eval_vision.py` → Task 4의 `data/images/` 폴더별 person·package 재현율, `empty/` 오탐률.
- 모든 스크립트는 결과 끝에 Global Constraints 정확도 목표 대비 PASS/FAIL을 출력한다.

- [ ] **Step 1:** 스크립트 구현, `make_tts_audio.py` 실행, `eval_language.py --rules-only`로 동작 확인.
- [ ] **Step 2:** lite 프로필로 세 평가 실행, 결과를 `eval/README.md`에 기록(날짜, 프로필, 모델, 수치). full 수치는 Task 9 Step 4와 함께 시연 PC에서 받는다.
- [ ] **Step 3:** Commit — `test(model-service): evaluation data generation and accuracy harness`

---

### Task 11: Docker 이미지 + 통합 안내

**Files:**
- Create: `model-service/Dockerfile`, `model-service/.dockerignore`, `model-service/README.md`

**Interfaces:**
- Dockerfile: `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` 기반, Python 3.11, 가중치는 이미지에 굽지 않고 볼륨 `/models`(`HF_HOME`, Ultralytics 가중치 경로)에 캐시. `CMD uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 1`. `HEALTHCHECK`는 `/health`가 `ok`일 때 성공.
- README: 실행법(venv / Docker), `MODEL_PROFILE`, 엔드포인트 curl 예시, **API v1.3 대비 변경점**(label `package`, 빈 전사 규칙, `/health`), 인태님 compose에 넣을 서비스 블록 예시(`gpus: all`, 포트 8000, 볼륨).

- [ ] **Step 1:** `docker build -t datacat-model model-service` → 성공.
- [ ] **Step 2:** `docker run --rm --gpus all -e MODEL_PROFILE=lite -p 8000:8000 -v datacat-models:/models datacat-model` 후 `/health`가 `ok`가 될 때까지 대기 → 구현된 엔드포인트 curl 스모크 통과.
- [ ] **Step 3:** Commit — `build(model-service): CUDA Dockerfile and integration README`

---

## 팀 협의 체크리스트 (코드 외 할 일)

각 항목은 보내기 전에 민중님 확인을 받는다.

- [ ] **인태님 — 저장소·병합 방식 제안 (즉시):** 모노레포 폴더 구조(`spring-server/`, `model-service/`, `pi/`, `app/`), 각자 브랜치 + Phase 종료마다 main 병합, 루트 compose는 인태님 관리.
- [x] **명세 PR (Task 4 전):** 명세만 담은 작은 PR — 완료: PR #1로 `API_v1_4.md` 병합, v1.2·v1.3 삭제 — 7.1 `label`을 `person`/`package`로 확정 및 package 범위 명시, 7.3·7.4 빈 전사 응답 규칙, 모델 서비스 `GET /health` 추가.
- [ ] **덕민님 — 요약 문체 확인 (Task 7 전):** 명사형 예시 5개(`택배 문 앞 보관`, `가스 검침 방문`, `관리실 소방 점검`, `친구 방문`, `음식 배달 도착`)로 앱 표시에 맞는지 확인. `purpose` 4개 값 최종 승인 요청.
- [ ] **인태님·덕민님 — 비전 선택 필드 제안 (Phase 2 초반):** 떠나는 택배 기사 대응용 `facingCamera`(YOLO11-pose)와 `bbox`. 동의 시 별도 계획으로 추가.
- [ ] **시연 PC 관리자 — full 벤치마크·평가 실행 요청 (Task 9·10 후).**

## 팀 일정과의 연결

| 팀 Phase | 필요한 태스크 | 종료 시 |
|---|---|---|
| Phase 1 (이미지 흐름, 2~3주) | Task 0 → 1 → 2 → 3 → 4, Task 11을 앞당겨 실행(스모크는 `/health`·`/vision/detect`만) | `feature/ai-model` → main PR |
| Phase 2 (음성 흐름, 4~5주) | Task 5 → 6 → 7 → 8 → 9 → 10, Task 11 갱신 | `feature/ai-model` → main PR |

## 이 계획 밖의 후속 작업 (별도 계획으로)

- 택배 전용 YOLO11 파인튜닝: 실제 마운트 각도로 촬영한 데이터와 공개 택배 데이터셋 수집 → 학습 → Task 10 비전 평가로 YOLOE 대비 개선 확인 → `package_weights` 교체.
- `facingCamera`/`bbox` 선택 필드: 팀 동의 시 YOLO11-pose 추가.
- `purpose` 최종 목록 확정(덕민님) 시 `Analysis.purpose`, 프롬프트, 규칙, 평가셋을 함께 갱신.
- STT·LLM 모델 교체 비교(예: Whisper large-v3, EXAONE, Qwen3-8B 4bit)는 Task 9·10 도구로 같은 조건에서 측정.

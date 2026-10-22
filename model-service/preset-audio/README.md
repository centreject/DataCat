# 현관 안내 음원 (프리셋 1~3)

Pi가 `raspberry-pi/sounds/`에서 틀 WAV 파일 후보. 16kHz·mono·16bit PCM, 앞 0.1초·뒤 0.2초 여유, 최대 음량 약 -1dBFS. **어떤 목소리·문구를 쓸지는 10/24 회의에서 정한다.** 정해지면 해당 파일을 아래 이름으로 Pi `sounds/`에 복사하면 끝(코드 수정 없음).

| Pi 파일 이름 | presetId | 후보 (이 폴더) | 문구 |
|---|---|---|---|
| `greeting.wav` | 1 | `greeting.wav` | 마이크에 말씀해 주세요. (지금 서버 문구) |
| | | `greeting_notice.wav` | 안녕하세요. 용건을 말씀해 주시면 집주인에게 전달됩니다. (녹음 알림 포함) |
| `completion.wav` | 2 | `completion.wav` | 접수되었습니다. (명세 10.1) |
| | | `completion_thanks.wav` | 전달했습니다. 감사합니다. (Pi 시험용) |
| `fallback.wav` | 3 | `fallback.wav` | 일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요. |

- 목소리: `F1/`(여성, 추천), `M2/`(남성). 앱에 보이는 서버 문구와 같은 문구의 파일을 고른다.
- 길이 1.8~5.6초. 안내가 끝나야 마이크가 열리므로(명세 5.3) 짧을수록 응대가 빠르다.

## 확인 (2026-10-22)

목소리 4개(F1·F2·M1·M2) × 문구 5개를 만들어 우리 음성 인식(Whisper)으로 다시 받아 적었다. F1은 5개 모두 문장부호 말고는 그대로 들렸다. F2 "마이크에 말씀해 주세요"는 "말씀해주세요"로만 들렸고, M1 오류 안내는 "없으 없습니다"로 더듬었다. 그래서 F1(여성)과 M2(남성)만 남겼다.

## 만든 방법과 라이선스

- 모델: [Supertonic 2](https://huggingface.co/Supertone/supertonic-2) (Supertone, ONNX, 한국어). 모델 라이선스 **OpenRAIL-M**: 상업·비상업 사용 가능, 특정인 흉내·속이는 용도·불법 용도 금지. 합성 목소리라 실제 사람의 음성권 문제 없음.
- 추론 코드: 공식 예제 `py/helper.py` ([supertone-oss-archive/supertonic](https://github.com/supertone-oss-archive/supertonic), MIT, 저장소는 보관 상태).
- 다시 만들기: 모델을 받아 `onnx/`, `voice_styles/`를 한 폴더에, `helper.py`를 `make_presets.py` 옆 `code/` 폴더에 두고
  `python -I make_presets.py <모델 폴더> <출력 폴더> F1 M2` (필요: `onnxruntime==1.23.1`, `numpy`). 잡음 시드가 고정이라 같은 문구·목소리면 같은 파일이 나온다. 문구를 바꾸면 `TEXTS`만 고친다.

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

## 기계 티 줄이기 비교 (2026-10-22)

목적: 목소리가 아니라 억양·쉼·말끝을 사람처럼. 학습 없이 세 가지를 시험했다.

| 방법 | 결과 |
|---|---|
| Qwen3-TTS 1.7B CustomVoice(Apache 2.0, 한국어 원어민 "Sohee") + 말투 지시(없음 / 영어 / 한국어 "친절한 안내원처럼, 말끝은 부드럽게") × 3번씩 = 45개 | 발음은 모두 정확(문장부호 제외 CER 0~0.8%). 자연스러움 점수 UTMOS 평균 3.70~3.76 |
| Supertonic 2 F1 / M2 (지금 후보) | 발음 정확(CER 0%). UTMOS 평균 **4.20** / 4.01 |
| 억양 직접 조정(pyworld/WORLD): 말끝 내리기, 높낮이 폭 넓히기, 말끝 늘이기 | **모두 나빠짐.** 분해 후 다시 합치는 것만으로 UTMOS −0.5~−0.9, 억양을 고친 효과는 ±0.1 안. 쓰지 않음 |

- UTMOS는 사람이 매긴 자연스러움 점수를 예측하는 공개 모델(MIT)인데 영어 음성으로 학습돼 한국어에는 참고용이다. 그래서 최종 선택은 사람이 듣고 한다.
- **이름을 가린 청취 세트:** `blind/` — 문구마다 A·B·C 세 개(Supertonic F1, Supertonic M2, Qwen3 Sohee 중 점수가 가장 높은 것)를 섞어 두었다. 모두 16kHz로 맞춰 Pi에서 나는 소리와 같다. 정답표는 AI 담당이 따로 보관(회의에서 고른 뒤 공개).
- 스크립트: `tools/` (생성 `gen_qwen.py`, 점수 `score_utmos.py`, 억양 조정 `tune_prosody.py`, 청취 세트 `blind.py`).

## 만든 방법과 라이선스

- 모델: [Supertonic 2](https://huggingface.co/Supertone/supertonic-2) (Supertone, ONNX, 한국어). 모델 라이선스 **OpenRAIL-M**: 상업·비상업 사용 가능, 특정인 흉내·속이는 용도·불법 용도 금지. 합성 목소리라 실제 사람의 음성권 문제 없음.
- 추론 코드: 공식 예제 `py/helper.py` ([supertone-oss-archive/supertonic](https://github.com/supertone-oss-archive/supertonic), MIT, 저장소는 보관 상태).
- 다시 만들기: 모델을 받아 `onnx/`, `voice_styles/`를 한 폴더에, `helper.py`를 `make_presets.py` 옆 `code/` 폴더에 두고
  `python -I make_presets.py <모델 폴더> <출력 폴더> F1 M2` (필요: `onnxruntime==1.23.1`, `numpy`). 잡음 시드가 고정이라 같은 문구·목소리면 같은 파일이 나온다. 문구를 바꾸면 `TEXTS`만 고친다.

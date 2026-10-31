# Raspberry Pi 단말

방문객 접근 감지(ToF), 사진 촬영, 안내 음성 출력, 발화 녹음을 맡는 현관 단말 코드다. Spring 서버에 연결해 실행하거나(`main.py --server URL`), 서버 없이 Pi 단독으로 실행한다(`main.py --offline`).

| 파일 | 역할 |
| --- | --- |
| `main.py` | 응대 흐름: 접근 감지 → 촬영 → 이벤트 생성 → 재확인 게이트 → 안내 → 녹음 → 완료 안내 |
| `api_client.py` | Spring 단말 API 클라이언트(명세 6장). 표준 라이브러리만 사용 |
| `distance_sensor.py` | 거리 측정, 접근(`APPROACH`)·이탈(`CLEAR`) 판정. `--sensor hcsr04\|tof` |
| `tof_sensor.py` | VL53L0X(I2C) 측정. 범위 밖은 최대 거리, 통신 오류만 측정 실패로 넘긴다 |
| `gate.py` | 재확인 게이트. 안내 재생 직전 방문객이 아직 있는지 판단(명세 5.3) |
| `camera.py` | USB 웹캠 JPEG 촬영(메모리로 반환) |
| `audio_output.py` | 안내 음성 출력(ALSA). `presetId` → `sounds/*.wav`, 재생이 끝나야 반환 |
| `audio_input.py` | VAD 녹음. 16kHz/16bit/mono WAV를 메모리로 반환, 파일 저장 안 함 |
| `cam_preview.py` | 웹캠 실시간 미리보기(설치 각도 맞추기용) |
| `SERVER_SETUP.md` | Raspberry Pi 4 환경 설정과 RTX 3090 서버 연동 구성 |

## 장비

| 항목 | 구성 | 상태(2026-10-18) |
| --- | --- | --- |
| 보드 | Raspberry Pi 4, Ubuntu 22.04, Python 3.10 | |
| 거리 센서 | VL53L0X ToF 모듈(VL53LXX-V2), I2C | 동작 확인 |
| 거리 센서(이전) | HC-SR04 초음파 | 코드 유지(`--sensor hcsr04`) |
| 카메라 | USB 웹캠(GEMBIRD AX2311), 640×480 | 동작 확인 |
| 마이크 | USB 핀마이크(JMTek) | 동작 확인 |
| 스피커 | 3.5mm 이어폰(임시) | 동작 확인 |
| 스피커(예정) | MAX98357A I2S 앰프 | 납땜 손상 의심으로 보류 |

기획서의 거리 센서는 VL53L5CX(8×8 멀티존)이고, 시제품은 한 점만 재는 VL53L0X를 쓴다. 서버에는 `triggerType=TOF`, 측정한 mm 값을 `distanceMm`으로 보낸다.

## 배선

전원을 끈 상태에서 연결한다.

### VL53L0X (I2C)

| 센서 | Raspberry Pi |
| --- | --- |
| VIN | 3.3V, 물리 핀 1 |
| GND | GND, 물리 핀 9 |
| SDA | GPIO2(SDA), 물리 핀 3 |
| SCL | GPIO3(SCL), 물리 핀 5 |

`sudo i2cdetect -y 1`에서 `29`가 보이면 인식된 것이다.

### HC-SR04 (이전 구성)

| HC-SR04 | Raspberry Pi |
| --- | --- |
| VCC | 5V, 물리 핀 2 |
| GND | GND, 물리 핀 6 |
| TRIG | GPIO24, 물리 핀 18 |
| ECHO | 분압 회로를 거쳐 GPIO23, 물리 핀 16 |

**5V ECHO 신호를 Pi GPIO에 직접 연결하면 안 된다.** ECHO–분기점 330Ω, 분기점–GND 470Ω으로 낮춰 GPIO23에 연결한다(약 2.94V). 배선 참고: [GPIO Zero DistanceSensor](https://gpiozero.readthedocs.io/en/stable/api_input.html#distancesensor-hc-sr04).

```text
HC-SR04 ECHO ── [330Ω] ──┬── GPIO23 (물리 핀 16)
                        │
                      [470Ω]
                        │
Pi GND ──────────────────┴── HC-SR04 GND
```

MAX98357A는 GPIO18·19·21(I2S)을 쓰므로 센서 핀과 겹치지 않는다.

## 설치

새 Pi에서는 설치 스크립트 한 번이면 아래 수동 설치와 같은 결과가 된다(패키지, I2C, 그룹 권한, 가상환경, 장치 확인).

```bash
cd raspberry-pi && ./setup.sh
```

수동 설치:

```bash
# I2C 활성화: /boot/firmware/config.txt 에 dtparam=i2c_arm=on (Ubuntu Pi 이미지 기본값)
sudo apt install -y i2c-tools python3-venv python3-rpi.gpio

# 장치 권한. 이 Ubuntu 이미지는 /dev/i2c-*를 i2c가 아니라 dialout 그룹에 준다(/lib/udev/rules.d/99-gpio.rules)
sudo usermod -aG dialout,video,audio $USER
# 다시 로그인해야 적용된다. 재로그인 전에 시험하려면 명령 앞에 sg <그룹> -c "..."를 붙인다.

python3 -m venv --system-site-packages .venv   # RPi.GPIO(apt)를 venv에서 쓰기 위해
.venv/bin/pip install -r requirements.txt
```

권한 문제는 증상이 서로 달라 헷갈린다.

| 증상 | 원인 |
| --- | --- |
| `PermissionError: '/dev/i2c-1'` | `dialout` 그룹 없음 |
| `arecord: no soundcards found` (카드가 있는데도) | `audio` 그룹 없음 |
| 웹캠 `/dev/video0`를 열 수 없음 | `video` 그룹 없음 |

## Docker로 실행

Pi에 Docker가 있으면 가상환경 없이 컨테이너로 실행할 수 있다. 호스트의 I2C 활성화(`dtparam=i2c_arm=on`)는 그대로 필요하다. Pi 4 실기에서 빌드(약 4분, 이미지 약 820MB)와 장치 동작(ToF·웹캠·마이크·3.5mm 출력)을 확인했다.

```bash
docker compose up -d --build                                       # main.py --offline 상시 실행
docker compose logs -f
docker compose run --rm pi python distance_sensor.py --sensor tof  # 장치별 시험
```

- 장치는 `/dev/i2c-1`, `/dev/gpiomem`, `/dev/video0`, `/dev/snd`를 넘긴다. 컨테이너는 root로 돌아 그룹 권한이 필요 없다.
- 컨테이너에서는 보드 자동 감지가 실패할 수 있어 `BLINKA_FORCEBOARD=RASPBERRY_PI_4B`로 지정한다.
- 프리셋 음원은 이미지에 넣지 않고 `./sounds`를 읽기 전용으로 붙인다.

참고: 이 이미지는 일반 PC Docker에서 그대로 실행되지 않는다.

- Pi에서 빌드한 이미지는 ARM64용이라 x86 PC에서는 `exec format error`(에뮬레이션 시 느리게 동작). 같은 Dockerfile을 PC에서 다시 빌드하면 PC용 이미지는 만들어진다.
- I2C·GPIO·웹캠·사운드 장치를 컨테이너에 넘기는 구성이라 해당 장치가 없는 PC에서는 컨테이너가 시작되지 않는다.
- PC에서는 단위 테스트(`python3 -m unittest`)로 로직을 확인하고, 서버 쪽 시험은 `datacat-stack/pi-sim.ps1`(feature/app-design)로 Pi 요청을 흉내 낸다.

## 장치별 시험

모든 명령은 이 폴더에서 실행한다. 사운드카드 번호는 USB 연결 순서로 바뀔 수 있어 코드에서는 카드 이름(`CARD=Headphones`, `CARD=Device`)을 쓴다.

```bash
# 장치 확인
i2cdetect -y 1                      # VL53L0X: 29
arecord -l; aplay -l                # 마이크: USB Audio Device, 이어폰: bcm2835 Headphones
ls /dev/video*                      # 웹캠: /dev/video0

# 거리 센서: 거리만 출력 / 접근·이탈 판정
.venv/bin/python distance_sensor.py --sensor tof
.venv/bin/python distance_sensor.py --sensor tof --threshold-cm 30 --release-cm 50

# 웹캠: 한 장 저장 / 실시간 미리보기(브라우저 http://localhost:8090, VSCode가 포트 연결)
.venv/bin/python camera.py cam_test.jpg
.venv/bin/python cam_preview.py

# 스피커: 삐 소리 / WAV 파일 / 프리셋(sounds/ 음원 필요)
.venv/bin/python audio_output.py
.venv/bin/python audio_output.py some.wav
.venv/bin/python audio_output.py 1

# 마이크: VAD 녹음 후 바로 재생(파일로 남기지 않음)
.venv/bin/python audio_input.py

# ALSA만으로 마이크→이어폰 확인
arecord -D plughw:CARD=Device,DEV=0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/t.wav && aplay -D plughw:CARD=Headphones,DEV=0 /tmp/t.wav
```

## 응대 흐름

```bash
.venv/bin/python main.py --server http://<Spring IP>:8080 [--threshold-cm 30 --release-cm 50]
.venv/bin/python main.py --offline   # 서버 없이
```

1. 감지 거리 안쪽 3회 연속 → `APPROACH`, 웹캠 촬영
2. 이벤트 생성 → (서버 흉내) `START_RECEPTION`
3. 재확인 게이트. 방문객이 떠났으면 안내 없이 `VISITOR_LEFT`로 종료
4. 안내 재생(presetId 1). **재생이 끝난 뒤에만 마이크를 연다**(명세 5.3, 법적 제약)
5. VAD 녹음. 5초 안에 발화가 없으면 `TIMEOUT`으로 종료
6. 음성 전송 → (서버 흉내) 녹음을 다시 들려줌 → 완료 안내(presetId 2)
7. 방문객이 떠나 `CLEAR`가 나올 때까지 다음 응대를 하지 않음

서버 요청 대기는 10초. 이벤트 생성·음성 전송이 실패하면(연결 실패, 503 등) 오류 안내(presetId 3)를 재생하고, 종료 알림 실패는 로그만 남긴다.

`--offline`의 서버 응답은 `main.py`의 `OfflineServer`가 명세의 정상 응답을 흉내 낸 것이다. 프리셋 음원(`sounds/greeting.wav`, `completion.wav`, `fallback.wav`)은 `model-service/preset-audio/final/`의 정식 음원(팀 합의)을 복사한 것이다. 파일이 없으면 삐 소리로 대신한다.

## 판정 규칙

- **접근:** 감지 거리 이내 값이 3회 연속(`--samples`) → `APPROACH` 한 번
- **이탈:** 해제 거리 이상이 3초(`--clear-s`) 이어지면 `CLEAR`. 기획서 복귀 안정화 시간(권장 3~5초)
- 두 거리 사이에서는 상태 유지. 중간에 한 번이라도 다시 가까워지면 처음부터 센다.
- **VL53L0X 범위 밖:** 앞이 비면 센서가 약 8190mm를 준다. 이것을 측정 실패로 두면 이탈을 확인하지 못하므로 최대 거리(120cm)로 바꾼다. 그래서 tof의 해제 거리는 120cm보다 작아야 한다.
- **측정 실패:** I2C 오류, 응답 지연(0.5초), 3cm 미만(VL53L0X) / 응답 없음, 2~400cm 밖(HC-SR04). 실패는 이탈로 보지 않는다.
- **재확인 게이트:** 0.06초 간격 5회 측정, 유효값의 과반이 해제 거리 안쪽이면 방문객 있음. 유효값이 없으면 이탈로 본다.

실측(손, 감지 30cm/해제 50cm): 접근·이탈 모두 정상. 손이 50cm 가까이 멀어지면 가끔 범위 밖(120cm)으로 튀지만 이탈은 30회 연속이 필요해 영향 없음. 사람 몸 기준 감지·해제 거리는 설치 위치에서 다시 정한다.

## VAD 녹음 규칙

| 항목 | 값 | 근거 |
| --- | --- | --- |
| 형식 | WAV, PCM 16-bit, 16kHz, mono | 명세 6.3 |
| 종료 | 발화 뒤 침묵 800ms | 명세 6.3(700~1,000ms) |
| 발화 시작 | 최근 300ms 중 180ms 이상 음성 | 문 닫는 소리 같은 짧은 잡음 무시 |
| 발화 없음 | 마이크 개방 후 5초 → `TIMEOUT` | 명세 6.4 |
| 최대 길이 | 30초 | 모델이 앞 30초만 전사(명세 7.2) |
| 저장 | 메모리에서만 처리, 오류 시에도 마이크 즉시 닫음 | Zero-Storage, 명세 11장 |

## 테스트

```bash
python3 -m unittest -v
```

GPIO·센서 없이 일반 PC에서도 판정 로직, ToF 값 변환, 재확인 게이트, VAD 종료 조건, 음성 출력 오류 처리, API 요청 형식을 검사한다(33개). 실제 장치 동작은 위 장치별 시험으로 확인한다.

## 실서버 연동 시험 (2026-10-18)

Pi 4 → 3090 서버(Spring `feature/image-upload` + 실제 모델 `lite` + MySQL, `datacat-stack` compose)로 응대 흐름 전체를 실행했다.

| 단계 | 결과 |
| --- | --- |
| ToF 접근 감지 → 촬영 | 정상. 접근 후 촬영 완료까지 1.1~2.2초 |
| `POST /device/events` | 정상. 서버 응답 0.08~1.2초 |
| 사람 사진 | `START_RECEPTION` → 재확인 게이트 → 안내 → 마이크 개방 → VAD 녹음(2.2초) 정상 |
| 사람 없는 사진 | `SILENT_STANDBY`, 응대 안 함 |
| `POST /device/events/{id}/audio` | 404(Spring 미구현) → 오류 안내(presetId 3) 재생 |
| 이탈 | `CLEAR` 후 감시 상태 복귀 |

- 카메라 방향이 틀어지면(책상을 향함, 뒤집힘) 사람이 있어도 `SILENT_STANDBY`. 설치 시 카메라를 똑바로, 센서와 같은 방향으로 둔다.
- 사람 피규어는 감지되지 않았고, 휴대폰 화면의 사람 얼굴 사진은 감지됐다.
- 같은 기기의 30초 이내 재요청은 서버가 기존 이벤트에 합친다(명세 6.1). 경우를 바꿔 시험할 때는 30초 간격을 둔다.
- 시험 사진·녹음은 저장소에 올리지 않는다(Zero-Storage, 촬영 공간 노출).

## 다음 작업

1. Spring `/audio`, `/end` 구현 후 연동 확인. 현재 Spring에는 `POST /device/events`(feature/image-upload)만 있어 음성 전송·종료 알림은 404
   - 2026-10-18 3090 실서버 확인: 사람 감지 → `START_RECEPTION`까지 정상
2. 프리셋 음원 3개(인사·완료·오류 안내) 준비
3. 설치 위치에서 감지·해제 거리 결정
4. MAX98357A 복구 시 `audio_output.py`의 `DEFAULT_DEVICE`만 I2S 카드로 변경
5. 촬영 지연 단축(실서버 시험에서 접근 후 촬영까지 약 2초, 카메라를 미리 열어 두는 방식 검토)

# Raspberry Pi 거리 센서

HC-SR04로 거리를 측정하는 기본 코드다. 감지 거리는 아직 정하지 않았으며, 기본 실행에서는 거리만 출력한다. 접근 감지는 실행 옵션으로 감지 거리와 해제 거리를 지정하면 사용할 수 있다.

## 장비

| 항목 | 구성 |
| --- | --- |
| 보드 | Raspberry Pi 3 Model B |
| 실행 환경 | Ubuntu 22.04, Python 3 |
| 거리 센서 | HC-SR04 |
| 마이크 | USB 마이크 |
| 스피커 | MAX98357 앰프 + 스피커 |
| 카메라 | USB 카메라, 영상 입력 확인 |

현재 코드는 거리 측정과 접근 상태 출력까지 구현했다. 마이크 녹음, 스피커 재생, 카메라 촬영, 서버 전송은 다음 단계에서 연결한다. 센서 코드의 실제 보드 실행은 확인이 필요하다.

## 배선

전원을 끈 상태에서 연결한다. 코드의 GPIO 번호는 BCM 기준이다.

| HC-SR04 | Raspberry Pi 연결 |
| --- | --- |
| VCC | 5V, 물리 핀 2 |
| GND | GND, 물리 핀 6 |
| TRIG | GPIO24, 물리 핀 18 |
| ECHO | 분압 회로를 거쳐 GPIO23, 물리 핀 16 |

**센서 전원은 5V이며, 5V ECHO 신호를 Pi GPIO에 직접 연결하면 안 된다.** 아래처럼 저항으로 전압을 낮춘다. 두 저항 사이에서 GPIO23으로 연결하며, 센서와 Pi는 GND를 공유한다.

```text
HC-SR04 ECHO ── [330Ω] ──┬── GPIO23 (물리 핀 16)
                        │
                      [470Ω]
                        │
Pi GND ──────────────────┴── HC-SR04 GND
```

이 구성의 GPIO 입력은 약 2.94V다. 배선 참고: [GPIO Zero 1.6.0 문서의 DistanceSensor 항목(PDF)](https://gpiozero.readthedocs.io/_/downloads/en/v1.6.0/pdf/).

## 실행

다음 명령은 Raspberry Pi의 Ubuntu 22.04에서 실행한다. [Ubuntu 제공 GPIO 패키지](https://packages.ubuntu.com/jammy/python3-rpi.gpio)를 사용한다.

```bash
sudo apt update
sudo apt install python3-rpi.gpio
cd raspberry-pi
python3 distance_sensor.py
```

기본 실행은 거리만 출력한다. 종료는 `Ctrl+C`다. GPIO 접근 권한 오류가 발생하면 같은 파일을 `sudo python3 distance_sensor.py`로 실행해 확인한다. 일반 PC에서는 GPIO 측정이 동작하지 않는다.

접근 감지를 시험할 때는 아래 두 옵션을 함께 지정한다. `N`, `M` 자리에 현장에서 정한 거리(cm)를 넣는다. 해제 거리 `M`은 감지 거리 `N`보다 크게 지정한다.

```text
python3 distance_sensor.py --threshold-cm N --release-cm M
```

- 감지 거리 이내 값이 3회 연속 측정되면 `APPROACH`를 한 번 출력한다.
- 감지 상태에서 해제 거리 이상 값이 3회 연속 측정되면 `CLEAR`를 출력하고 다음 접근을 기다린다.
- 두 거리 사이에서는 기존 상태를 유지한다. 연속 횟수는 `--samples`로 변경할 수 있다.
- 측정 사이에 0.1초 대기하며, ECHO의 상승·하강 대기는 각각 최대 0.03초로 제한한다.
- 응답 없음이나 2~400cm 범위 밖의 값은 측정 실패로 처리한다. 실패를 이탈로 간주하지 않으므로, 실패가 계속되면 자동으로 재감지 대기 상태가 되지 않는다.

초음파 센서는 물체까지의 거리를 측정한다. 사람 여부는 이 코드에서 판단하지 않는다. 설치 위치에서 거리값을 확인한 뒤 감지·해제 거리를 조정해야 한다. Python과 Linux의 실행 지연 때문에 측정값에 오차가 있을 수 있다.

## 테스트

GPIO 라이브러리 없이 일반 PC에서도 상태 전환과 ECHO 대기 시간 제한을 검사할 수 있다.

```bash
cd raspberry-pi
python3 -m unittest -v
```

단위 테스트는 실제 센서의 거리 정확도나 배선을 검증하지 않는다.

## 다음 작업

1. 보드에서 거리 측정값을 확인하고 감지·해제 거리를 정한다.
2. USB 마이크의 장치 인식과 녹음을 확인한다.
3. MAX98357의 I2S 설정과 음성 출력을 확인한다.
4. USB 카메라 촬영과 서버 이벤트 전송을 연결한다.

서버 연결은 [main의 API v1.5](https://github.com/centreject/DataCat/blob/main/API_v1_5.md)를 기준으로 맞춘다. 현재 명세의 `triggerType`은 `TOF`, `BUTTON`이므로 초음파 트리거 표기는 팀과 정해야 한다. 이후에는 거리 감지 → 이미지 전송 → 서버의 `START_RECEPTION` 응답 → 거리 재확인 → 안내 음성 재생 완료 → 녹음 순서로 연결한다.

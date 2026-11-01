# Raspberry Pi 4 (arm64) 단말 이미지. Pi에서 빌드·실행한다(docker-compose.yml 참고).
# 장치(I2C, 웹캠, 사운드, GPIO)는 컨테이너에 직접 넘긴다. 호스트의 I2C 활성화는 setup.sh와 같이 필요하다.
FROM python:3.10-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends alsa-utils i2c-tools libglib2.0-0 gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Blinka가 Pi 4의 핀 정의를 불러올 때 RPi.GPIO를 import한다(호스트는 apt 패키지, 컨테이너는 pip).
RUN pip install --no-cache-dir -r requirements.txt RPi.GPIO==0.7.1 \
    && apt-get purge -y gcc libc6-dev && apt-get autoremove -y

COPY *.py ./

# 컨테이너에서는 /sys/firmware가 가려져 보드 자동 감지가 실패할 수 있어 직접 지정한다.
ENV BLINKA_FORCEBOARD=RASPBERRY_PI_4B \
    BLINKA_FORCECHIP=BCM2XXX \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py", "--offline"]

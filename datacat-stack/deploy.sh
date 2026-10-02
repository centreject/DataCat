#!/usr/bin/env bash
# 서버 PC(리눅스)에서 최신 코드로 다시 띄운다.   사용: ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
git pull --ff-only || echo "git pull 건너뜀 (git 저장소가 아니거나 로컬 변경 있음)"
[ -f .env ] || { cp .env.example .env; echo ".env 를 새로 만들었어요. 비밀번호를 바꿔 주세요."; }
docker compose up -d --build
docker image prune -f >/dev/null
docker compose ps

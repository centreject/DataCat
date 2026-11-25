#!/usr/bin/env bash
# 안드로이드 앱(APK) 빌드 (맥·리눅스). 윈도우는 build-apk.ps1
#   ./build-apk.sh [서버주소]      기본 https://api.teamdatacat.com
set -euo pipefail
API="${1:-https://api.teamdatacat.com}"
APP="$(cd "$(dirname "$0")/../app/datacat_frontdoor" && pwd)"
[ -f "$APP/firebase/google-services.json" ] || echo "! firebase/google-services.json 이 없어요 → 푸시 없이 빌드" >&2
docker run --rm \
  -v "$APP:/app" \
  -v datacat-gradle:/root/.gradle \
  -v datacat-android-keys:/root/.android \
  -e DATACAT_API="$API" \
  -e APP_DIR=/app \
  ghcr.io/cirruslabs/flutter:stable \
  bash -c "tr -d '\r' < /app/tool/build_apk.sh > /tmp/build_apk.sh && bash /tmp/build_apk.sh"
echo "완성: $APP/dist/datacat-frontdoor.apk"

#!/usr/bin/env bash
# 안드로이드 앱(APK) 빌드 — Flutter 도커 이미지 안에서 실행된다.
#   직접 부르지 말고 datacat-stack/build-apk.ps1 (윈도우) 또는 build-apk.sh 를 쓰세요.
#
#   DATACAT_API   앱이 처음 연결할 서버 (기본 https://api.teamdatacat.com)
#   firebase/google-services.json 이 있으면 푸시가 켜진 앱이 나온다.
set -euo pipefail
cd "${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

API="${DATACAT_API:-https://api.teamdatacat.com}"

if [ ! -d android ]; then
  echo "▶ android 폴더 만들기 (처음 한 번)"
  flutter create . --platforms=android --org com.teamdatacat --project-name datacat_frontdoor
  rm -f test/widget_test.dart   # flutter create 기본 테스트는 이 앱과 맞지 않는다
fi

echo "▶ 패키지 받기"
flutter pub get

echo "▶ 안드로이드 설정 맞추기 (권한·앱 이름·최소 버전)"
dart tool/prepare_android.dart

DEFINES="$(dart tool/firebase_defines.dart)"

echo "▶ APK 빌드 (서버: $API)"
# shellcheck disable=SC2086
flutter build apk --release --dart-define=DATACAT_API="$API" $DEFINES

mkdir -p dist
cp build/app/outputs/flutter-apk/app-release.apk dist/datacat-frontdoor.apk
echo
echo "✔ 완성: app/datacat_frontdoor/dist/datacat-frontdoor.apk"

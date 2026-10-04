# DataCat 앱 — Flutter 웹 빌드를 nginx로 서빙
#
#   docker build -t datacat-app .                       (datacat-stack 의 compose 가 대신 실행)
#   pubspec.lock 이 요구하는 Flutter 버전보다 이미지가 오래됐다면:
#   --build-arg FLUTTER_IMAGE=ghcr.io/cirruslabs/flutter:<버전>

ARG FLUTTER_IMAGE=ghcr.io/cirruslabs/flutter:stable

# ── 1단계: 빌드 (Flutter SDK 포함, 결과물만 다음 단계로 넘김) ──
FROM ${FLUTTER_IMAGE} AS build
WORKDIR /app

# 패키지 목록이 안 바뀌면 이 단계는 캐시로 건너뛴다
COPY pubspec.yaml pubspec.lock* ./
RUN flutter pub get

COPY . .
# web/ 폴더가 없으면 (flutter create 를 안 한 경우) 여기서 만든다
RUN [ -d web ] || flutter create . --platforms=web --project-name datacat_frontdoor
ARG API_URL=same-origin
RUN flutter build web --release --dart-define=DATACAT_API=${API_URL}

# 서비스 워커를 "스스로 해제하는" 스크립트로 바꿔 둔다.
# Flutter 기본 서비스 워커는 화면을 브라우저에 저장해 두어, 새 버전을 배포해도
# 강력 새로고침으로 안 바뀌는 문제가 생긴다. 예전 버전을 연 브라우저도 한두 번 새로고침하면 풀린다.
# (페이지를 강제로 새로고침하지는 않는다 — 앱이 매번 서비스 워커를 등록하므로 무한 새로고침이 될 수 있다)
RUN printf '%s\n' \
  "self.addEventListener('install', () => self.skipWaiting());" \
  "self.addEventListener('activate', (e) => e.waitUntil(self.registration.unregister()));" \
  > build/web/flutter_service_worker.js

# ── 2단계: 실행 (nginx + 빌드 결과물, 약 50 MB) ──
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html
EXPOSE 80

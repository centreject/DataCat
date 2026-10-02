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

# ── 2단계: 실행 (nginx + 빌드 결과물, 약 50 MB) ──
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html
EXPOSE 80

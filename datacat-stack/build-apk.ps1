# 안드로이드 앱(APK) 빌드 — Flutter 를 설치하지 않아도 도커로 만든다.
#
#   .\build-apk.ps1                                   기본 서버 https://api.teamdatacat.com
#   .\build-apk.ps1 -Api http://192.168.0.12:8090     집 와이파이의 서버로 시험할 때
#
# 결과: app\datacat_frontdoor\dist\datacat-frontdoor.apk  → 휴대폰에 옮겨 설치
# 처음 한 번은 안드로이드 SDK·Gradle 을 받느라 10~20분 걸린다. 다음부터는 몇 분.
param([string]$Api = "https://api.teamdatacat.com")
$ErrorActionPreference = "Stop"

$app = (Resolve-Path (Join-Path $PSScriptRoot "..\app\datacat_frontdoor")).Path
if (-not (Test-Path (Join-Path $app "firebase\google-services.json"))) {
  Write-Warning "firebase\google-services.json 이 없어요. 푸시 없이 빌드합니다. (PUSH.md 1단계)"
}

docker run --rm `
  -v "${app}:/app" `
  -v datacat-gradle:/root/.gradle `
  -v datacat-android-keys:/root/.android `
  -e DATACAT_API=$Api `
  -e APP_DIR=/app `
  ghcr.io/cirruslabs/flutter:stable `
  bash -c "tr -d '\r' < /app/tool/build_apk.sh > /tmp/build_apk.sh && bash /tmp/build_apk.sh"

if ($LASTEXITCODE -ne 0) { throw "APK 빌드에 실패했어요. 위의 빨간 오류를 확인하세요." }
Write-Host ""
Write-Host "완성: $app\dist\datacat-frontdoor.apk" -ForegroundColor Green

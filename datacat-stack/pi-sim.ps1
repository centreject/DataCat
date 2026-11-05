# 라즈베리파이 대신 사진을 한 장 올려 보는 시험용 스크립트 (Spring 서버로 띄웠을 때)
#
#   .\pi-sim.ps1                           사람 방문 (거리센서)
#   .\pi-sim.ps1 -Kind package             물품만 있음
#   .\pi-sim.ps1 -Kind empty               아무것도 없음 (오탐)
#   .\pi-sim.ps1 -Kind person -Trigger BUTTON
#
# 모의 모델 서비스는 파일 이름(person, package, animal, empty)으로 결과를 정한다.
# 같은 기기에서 30초 안에 다시 보내면 서버가 같은 방문으로 합친다.
param(
  [ValidateSet('person', 'package', 'person_package', 'animal', 'empty')]
  [string]$Kind = 'person',
  [ValidateSet('TOF', 'BUTTON')]
  [string]$Trigger = 'TOF',
  [string]$Api = ''
)
$ErrorActionPreference = 'Stop'

if (-not $Api) {
  $port = '8080'
  $envFile = Join-Path $PSScriptRoot '.env'
  if (Test-Path $envFile) {
    $m = Select-String -Path $envFile -Pattern '^API_PORT=(\d+)'
    if ($m) { $port = $m.Matches[0].Groups[1].Value }
  }
  $Api = "http://localhost:$port"
}

# 시험용 사진 만들기 (단색이면 카메라 가림으로 판정되므로 무늬를 넣는다)
Add-Type -AssemblyName System.Drawing
$dir = Join-Path $env:TEMP 'datacat-pi-sim'
New-Item -ItemType Directory -Force $dir | Out-Null
$img = Join-Path $dir "$Kind.jpg"
$bmp = New-Object System.Drawing.Bitmap 640, 480
$g = [System.Drawing.Graphics]::FromImage($bmp)
$rand = New-Object System.Random
for ($i = 0; $i -lt 400; $i++) {
  $brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($rand.Next(256), $rand.Next(256), $rand.Next(256)))
  $g.FillRectangle($brush, $rand.Next(640), $rand.Next(480), $rand.Next(10, 80), $rand.Next(10, 80))
  $brush.Dispose()
}
$g.Dispose()
$bmp.Save($img, [System.Drawing.Imaging.ImageFormat]::Jpeg)
$bmp.Dispose()

$meta = Join-Path $dir 'metadata.json'
$now = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
@{ deviceId = 'door-01'; triggerType = $Trigger; distanceMm = 600; capturedAt = $now } |
  ConvertTo-Json -Compress | Set-Content -Path $meta -Encoding Ascii

Write-Host "보내는 곳: $Api/api/v1/device/events ($Kind, $Trigger)"
curl.exe -s -w "`nHTTP %{http_code}`n" `
  -F "metadata=<$meta;type=application/json" `
  -F "image=@$img;type=image/jpeg" `
  "$Api/api/v1/device/events"

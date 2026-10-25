// flutter create 가 만든 android 폴더를 이 앱에 맞게 고친다. 여러 번 실행해도 결과가 같다.
//   - 인터넷·알림 권한 (안드로이드 13 이상은 알림 권한을 따로 묻는다)
//   - 앱 이름 "DataCat 현관"
//   - 집 안 와이파이의 http:// 서버도 시험할 수 있게 평문 통신 허용
//   - Firebase 가 요구하는 최소 안드로이드 버전 (API 23 = 안드로이드 6.0)
//   - 앱 아이콘과 알림 아이콘 (tool/icon/android/res 를 복사)
import 'dart:io';

void main() {
  _copyIcons(Directory('tool/icon/android/res'), Directory('android/app/src/main/res'));
  _patchManifest(File('android/app/src/main/AndroidManifest.xml'));
  for (final name in ['build.gradle.kts', 'build.gradle']) {
    final f = File('android/app/$name');
    if (f.existsSync()) _patchGradle(f);
  }
}

void _patchManifest(File f) {
  if (!f.existsSync()) {
    stderr.writeln('AndroidManifest.xml 이 없어요. android 폴더를 지우고 다시 빌드해 보세요.');
    exit(1);
  }
  var s = f.readAsStringSync();
  for (final perm in ['android.permission.INTERNET', 'android.permission.POST_NOTIFICATIONS']) {
    if (!s.contains('"$perm"')) {
      s = s.replaceFirstMapped(
        RegExp(r'<manifest[^>]*>'),
        (m) => '${m[0]}\n    <uses-permission android:name="$perm"/>',
      );
    }
  }
  s = s.replaceFirst(RegExp(r'android:label="[^"]*"'), 'android:label="DataCat 현관"');
  if (!s.contains('usesCleartextTraffic')) {
    s = s.replaceFirst('<application', '<application\n        android:usesCleartextTraffic="true"');
  }
  // 푸시 알림이 상태 표시줄에 흰 네모로 나오지 않게 전용 알림 아이콘과 색을 지정한다
  if (!s.contains('default_notification_icon')) {
    s = s.replaceFirstMapped(
      RegExp(r'<application[^>]*>'),
      (m) => '${m[0]}\n'
          '        <meta-data android:name="com.google.firebase.messaging.default_notification_icon"\n'
          '            android:resource="@drawable/ic_stat_datacat"/>\n'
          '        <meta-data android:name="com.google.firebase.messaging.default_notification_color"\n'
          '            android:resource="@color/ic_launcher_background"/>',
    );
  }
  f.writeAsStringSync(s);
  print('  AndroidManifest.xml OK');
}

void _patchGradle(File f) {
  var s = f.readAsStringSync();
  s = s
      .replaceAll(RegExp(r'minSdk\s*=\s*flutter\.minSdkVersion'), 'minSdk = maxOf(flutter.minSdkVersion, 23)')
      .replaceAll(RegExp(r'minSdkVersion\s+flutter\.minSdkVersion'), 'minSdkVersion Math.max(flutter.minSdkVersion, 23)');
  f.writeAsStringSync(s);
  print('  ${f.path} OK');
}

void _copyIcons(Directory from, Directory to) {
  if (!from.existsSync()) return;
  var n = 0;
  for (final e in from.listSync(recursive: true)) {
    if (e is! File) continue;
    final rel = e.path.substring(from.path.length + 1);
    final dest = File('${to.path}/$rel');
    dest.parent.createSync(recursive: true);
    e.copySync(dest.path);
    n++;
  }
  print('  아이콘 $n개 OK');
}

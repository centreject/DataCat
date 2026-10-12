// firebase/google-services.json 에서 앱에 필요한 값만 뽑아 --dart-define 인자로 출력한다.
// 파일이 없으면 아무것도 출력하지 않는다 → 푸시 없이 빌드된다.
import 'dart:convert';
import 'dart:io';

const package = 'com.teamdatacat.datacat_frontdoor';

void main() {
  final f = File('firebase/google-services.json');
  if (!f.existsSync()) {
    stderr.writeln('! firebase/google-services.json 이 없어요 → 푸시 없이 빌드합니다. (PUSH.md 1단계)');
    return;
  }
  final j = jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
  final project = j['project_info'] as Map<String, dynamic>;
  final clients = (j['client'] as List).cast<Map<String, dynamic>>();
  String pkgOf(Map<String, dynamic> c) =>
      '${(c['client_info'] as Map)['android_client_info']?['package_name']}';
  final client = clients.firstWhere(
    (c) => pkgOf(c) == package,
    orElse: () => _fail('! google-services.json 에 $package 앱이 없어요. '
        'Firebase 에 이 패키지 이름으로 안드로이드 앱을 등록했는지 확인하세요.'),
  );
  final values = {
    'FCM_API_KEY': (client['api_key'] as List).first['current_key'],
    'FCM_APP_ID': (client['client_info'] as Map)['mobilesdk_app_id'],
    'FCM_SENDER_ID': project['project_number'],
    'FCM_PROJECT_ID': project['project_id'],
  };
  stderr.writeln('▶ Firebase 프로젝트 ${project['project_id']} 로 푸시를 켜고 빌드합니다.');
  stdout.write(values.entries.map((e) => '--dart-define=${e.key}=${e.value}').join(' '));
}

Never _fail(String message) {
  stderr.writeln(message);
  exit(1);
}

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'push_center.dart';

/// Firebase 프로젝트 값. `google-services.json`을 소스에 넣지 않고
/// 빌드할 때 `--dart-define`으로 받는다 (tool/build_apk.sh 가 json 에서 읽어 넘겨 준다).
abstract final class FirebaseConfig {
  static const apiKey = String.fromEnvironment('FCM_API_KEY');
  static const appId = String.fromEnvironment('FCM_APP_ID');
  static const senderId = String.fromEnvironment('FCM_SENDER_ID');
  static const projectId = String.fromEnvironment('FCM_PROJECT_ID');

  static bool get isSet =>
      apiKey.isNotEmpty && appId.isNotEmpty && senderId.isNotEmpty && projectId.isNotEmpty;

  static FirebaseOptions get options => const FirebaseOptions(
        apiKey: apiKey,
        appId: appId,
        messagingSenderId: senderId,
        projectId: projectId,
      );
}

/// 지금 환경에 맞는 [PushCenter]를 만든다. 안드로이드 + Firebase 설정이 있을 때만 실제 FCM을 쓴다.
PushCenter createPushCenter() {
  if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
    return PushCenter.disabled();
  }
  if (!FirebaseConfig.isSet) {
    return PushCenter.disabled(reason: PushStatus.notConfigured);
  }
  return PushCenter(FcmBackend());
}

class FcmBackend implements PushBackend {
  FirebaseMessaging get _fm => FirebaseMessaging.instance;

  @override
  String get platform => 'ANDROID';

  @override
  Future<bool> start() async {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(options: FirebaseConfig.options);
    }
    // 안드로이드 13 이상은 알림 권한을 따로 물어본다
    final s = await _fm.requestPermission();
    return s.authorizationStatus == AuthorizationStatus.authorized ||
        s.authorizationStatus == AuthorizationStatus.provisional;
  }

  @override
  Future<String?> token() => _fm.getToken();

  @override
  Stream<String> get tokenRefresh => _fm.onTokenRefresh;

  @override
  Stream<PushMessage> get foreground => FirebaseMessaging.onMessage.map(_convert);

  @override
  Stream<PushMessage> get opened => FirebaseMessaging.onMessageOpenedApp.map(_convert);

  @override
  Future<PushMessage?> initialMessage() async {
    final m = await _fm.getInitialMessage();
    return m == null ? null : _convert(m);
  }

  static PushMessage _convert(RemoteMessage m) => PushMessage.fromData(
        m.data,
        title: m.notification?.title,
        body: m.notification?.body,
      );
}

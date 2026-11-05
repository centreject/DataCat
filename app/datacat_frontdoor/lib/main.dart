import 'package:flutter/material.dart';

import 'app.dart';
import 'push/fcm_backend.dart';
import 'state/event_store.dart';
import 'state/policy.dart';
import 'state/settings.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settings = AppSettings();
  final policy = VisitPolicy();
  await Future.wait([settings.load(), policy.load()]);

  runApp(DataCatApp(
    settings: settings,
    store: EventStore(settings.createApi()),
    policy: policy,
    // 안드로이드 + Firebase 설정이 있으면 푸시를 켠다. 웹과 설정 없는 빌드는 꺼진 상태로 뜬다
    push: createPushCenter(),
  ));
}

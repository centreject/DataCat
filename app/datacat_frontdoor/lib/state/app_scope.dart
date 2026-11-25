import 'package:flutter/widgets.dart';

import '../push/push_center.dart';
import 'event_store.dart';
import 'policy.dart';
import 'settings.dart';

/// 앱 전역 상태를 위젯 트리에 내려준다.
/// 각 객체는 ChangeNotifier라서 화면은 ListenableBuilder로 변화를 구독한다.
class AppScope extends InheritedWidget {
  const AppScope({
    super.key,
    required this.settings,
    required this.store,
    required this.policy,
    required this.push,
    required super.child,
  });

  final AppSettings settings;
  final EventStore store;
  final VisitPolicy policy;

  /// 휴대폰 푸시 알림 상태
  final PushCenter push;

  static AppScope of(BuildContext context) {
    final scope = context.getInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope가 위젯 트리에 없어요.');
    return scope!;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) =>
      settings != oldWidget.settings ||
      store != oldWidget.store ||
      policy != oldWidget.policy ||
      push != oldWidget.push;
}

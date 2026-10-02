import 'package:flutter/widgets.dart';

import 'event_store.dart';
import 'settings.dart';

/// 앱 전역 상태를 위젯 트리에 내려준다.
/// 각 객체는 ChangeNotifier라서 화면은 ListenableBuilder로 변화를 구독한다.
class AppScope extends InheritedWidget {
  const AppScope({
    super.key,
    required this.settings,
    required this.store,
    required super.child,
  });

  final AppSettings settings;
  final EventStore store;

  static AppScope of(BuildContext context) {
    final scope = context.getInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope가 위젯 트리에 없어요.');
    return scope!;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) =>
      settings != oldWidget.settings || store != oldWidget.store;
}

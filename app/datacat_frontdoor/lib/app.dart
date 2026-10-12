import 'dart:async';

import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'data/models.dart';
import 'push/push_center.dart';
import 'state/app_scope.dart';
import 'state/event_store.dart';
import 'state/policy.dart';
import 'state/settings.dart';
import 'ui/event_detail_screen.dart';
import 'ui/shell.dart';

class DataCatApp extends StatefulWidget {
  const DataCatApp({
    super.key,
    required this.settings,
    required this.store,
    this.policy,
    this.push,
    this.autoRefresh = true,
  });

  final AppSettings settings;
  final EventStore store;

  /// 알림·응대 정책. 비우면 기본값으로 만든다 (테스트용).
  final VisitPolicy? policy;

  /// 휴대폰 푸시. 비우면 꺼진 상태로 만든다 (웹·테스트).
  final PushCenter? push;

  /// 15초마다 새 방문 확인
  final bool autoRefresh;

  @override
  State<DataCatApp> createState() => _DataCatAppState();
}

class _DataCatAppState extends State<DataCatApp> with WidgetsBindingObserver {
  late String _connectionKey = widget.settings.connectionKey;
  late final VisitPolicy _policy = widget.policy ?? VisitPolicy();
  late final PushCenter _push = widget.push ?? PushCenter.disabled();
  final _navigator = GlobalKey<NavigatorState>();
  StreamSubscription<int>? _openedSub;

  @override
  void initState() {
    super.initState();
    widget.settings.addListener(_onSettingsChanged);
    widget.store.arrivalFilter = _policy.shouldNotify;
    widget.store.refresh();

    // 푸시: 앱이 떠 있을 때 오면 바로 새 방문을 불러오고, 알림을 누르면 그 방문을 연다
    _push.onForeground = widget.store.checkForNew;
    _openedSub = _push.openedEvents.listen(_openEvent);
    _push.start(widget.store.api);
    if (widget.autoRefresh) {
      widget.store.startPolling();
      WidgetsBinding.instance.addObserver(this);
    }
  }

  @override
  void dispose() {
    widget.settings.removeListener(_onSettingsChanged);
    _openedSub?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    widget.store.stopPolling();
    super.dispose();
  }

  /// 앱이 화면 뒤로 가면 자동 새로고침을 멈추고, 돌아오면 바로 한 번 확인한다.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!widget.autoRefresh) return;
    if (state == AppLifecycleState.resumed) {
      widget.store.checkForNew();
      widget.store.startPolling();
    } else if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      widget.store.stopPolling();
    }
  }

  /// 데모 모드나 서버 주소가 바뀌면 연결을 새로 만들고 처음부터 불러온다.
  void _onSettingsChanged() {
    final key = widget.settings.connectionKey;
    if (key == _connectionKey) return;
    _connectionKey = key;
    widget.store.replaceApi(widget.settings.createApi());
    _push.attach(widget.store.api); // 새 서버에 푸시 토큰 다시 등록
  }

  /// 푸시 알림을 눌렀을 때 그 방문의 상세 화면을 연다.
  void _openEvent(int eventId) {
    final nav = _navigator.currentState;
    if (nav == null) {
      // 앱이 알림으로 막 시작돼 화면이 아직 없으면 다음 프레임에 연다
      WidgetsBinding.instance.addPostFrameCallback((_) => _openEvent(eventId));
      return;
    }
    final store = widget.store;
    final known = store.events.where((e) => e.eventId == eventId).firstOrNull;
    nav.popUntil((r) => r.isFirst);
    nav.push(MaterialPageRoute<void>(
      // 목록에 아직 없으면 번호만으로 열고, 상세 화면이 서버에서 내용을 불러온다
      builder: (_) => EventDetailScreen(initial: known ?? VisitEvent(eventId: eventId, occurredAt: DateTime.now())),
    ));
    store.checkForNew();
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      settings: widget.settings,
      store: widget.store,
      policy: _policy,
      push: _push,
      child: ListenableBuilder(
        listenable: widget.settings,
        builder: (context, _) => MaterialApp(
          title: 'DataCat 현관',
          navigatorKey: _navigator,
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: widget.settings.themeMode,
          // 해/달 버튼을 누르면 색이 0.45초 동안 부드럽게 넘어간다
          themeAnimationStyle: const AnimationStyle(
            duration: Duration(milliseconds: 450),
            curve: Curves.easeInOutCubic,
          ),
          home: const AppShell(),
        ),
      ),
    );
  }
}

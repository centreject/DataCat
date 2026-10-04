import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'state/app_scope.dart';
import 'state/event_store.dart';
import 'state/policy.dart';
import 'state/settings.dart';
import 'ui/shell.dart';

class DataCatApp extends StatefulWidget {
  const DataCatApp({
    super.key,
    required this.settings,
    required this.store,
    this.policy,
    this.autoRefresh = true,
  });

  final AppSettings settings;
  final EventStore store;

  /// 알림·응대 정책. 비우면 기본값으로 만든다 (테스트용).
  final VisitPolicy? policy;

  /// 15초마다 새 방문 확인
  final bool autoRefresh;

  @override
  State<DataCatApp> createState() => _DataCatAppState();
}

class _DataCatAppState extends State<DataCatApp> with WidgetsBindingObserver {
  late String _connectionKey = widget.settings.connectionKey;
  late final VisitPolicy _policy = widget.policy ?? VisitPolicy();

  @override
  void initState() {
    super.initState();
    widget.settings.addListener(_onSettingsChanged);
    widget.store.arrivalFilter = _policy.shouldNotify;
    widget.store.refresh();
    if (widget.autoRefresh) {
      widget.store.startPolling();
      WidgetsBinding.instance.addObserver(this);
    }
  }

  @override
  void dispose() {
    widget.settings.removeListener(_onSettingsChanged);
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
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      settings: widget.settings,
      store: widget.store,
      policy: _policy,
      child: ListenableBuilder(
        listenable: widget.settings,
        builder: (context, _) => MaterialApp(
          title: 'DataCat 현관',
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

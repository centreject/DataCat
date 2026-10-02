import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'state/app_scope.dart';
import 'state/event_store.dart';
import 'state/settings.dart';
import 'ui/shell.dart';

class DataCatApp extends StatefulWidget {
  const DataCatApp({super.key, required this.settings, required this.store});

  final AppSettings settings;
  final EventStore store;

  @override
  State<DataCatApp> createState() => _DataCatAppState();
}

class _DataCatAppState extends State<DataCatApp> {
  late String _connectionKey = widget.settings.connectionKey;

  @override
  void initState() {
    super.initState();
    widget.settings.addListener(_onSettingsChanged);
    widget.store.refresh();
  }

  @override
  void dispose() {
    widget.settings.removeListener(_onSettingsChanged);
    super.dispose();
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
      child: MaterialApp(
        title: 'DataCat 현관',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        home: const AppShell(),
      ),
    );
  }
}

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show Brightness, ThemeMode;
import 'package:shared_preferences/shared_preferences.dart';

import '../data/api.dart';
import '../data/demo_api.dart';

/// 서버 주소, 데모 모드, 화면 테마. 기기에 저장해 두고 앱을 다시 열어도 유지한다.
class AppSettings extends ChangeNotifier {
  AppSettings();

  static const _kBaseUrl = 'server.baseUrl';
  static const _kDemo = 'app.demoMode';
  static const _kTheme = 'app.themeMode';

  static const bool _hasBuildUrl = bool.hasEnvironment('DATACAT_API');
  /// 웹 빌드에서 `--dart-define=DATACAT_API=same-origin`이면 앱을 연 주소를 서버로 쓴다.
  /// (도커의 nginx가 /api/ 요청을 API 컨테이너로 넘겨 준다)
  static String get defaultBaseUrl {
    const v = String.fromEnvironment('DATACAT_API', defaultValue: 'http://localhost:8080');
    if (v == 'same-origin' && kIsWeb) return Uri.base.origin;
    return v;
  }

  SharedPreferences? _prefs;
  String _baseUrl = defaultBaseUrl;
  bool _demoMode = !_hasBuildUrl;
  ThemeMode _themeMode = ThemeMode.system;

  String get baseUrl => _baseUrl;
  bool get demoMode => _demoMode;

  /// 시스템 설정을 따를지, 라이트/다크로 고정할지
  ThemeMode get themeMode => _themeMode;

  /// 이 값이 바뀌면 서버 연결을 새로 만들어야 한다.
  String get connectionKey => _demoMode ? 'demo' : _baseUrl;

  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _prefs = prefs;
      _baseUrl = prefs.getString(_kBaseUrl) ?? _baseUrl;
      _demoMode = prefs.getBool(_kDemo) ?? _demoMode;
      _themeMode = switch (prefs.getString(_kTheme)) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };
    } catch (e) {
      // 저장소를 못 쓰는 환경이어도 기본값으로 앱은 뜬다.
      debugPrint('설정을 불러오지 못했어요: $e');
    }
  }

  Future<void> setBaseUrl(String value) async {
    final v = value.trim();
    if (v.isEmpty || v == _baseUrl) return;
    _baseUrl = v;
    notifyListeners();
    await _prefs?.setString(_kBaseUrl, v);
  }

  Future<void> setDemoMode(bool value) async {
    if (value == _demoMode) return;
    _demoMode = value;
    notifyListeners();
    await _prefs?.setBool(_kDemo, value);
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    if (mode == _themeMode) return;
    _themeMode = mode;
    notifyListeners();
    await _prefs?.setString(_kTheme, mode.name);
  }

  /// 해/달 버튼: 지금 보이는 밝기의 반대로 고정한다.
  Future<void> toggleTheme(Brightness current) =>
      setThemeMode(current == Brightness.dark ? ThemeMode.light : ThemeMode.dark);

  DataCatApi createApi() =>
      _demoMode ? DemoDataCatApi() : HttpDataCatApi(_baseUrl);
}

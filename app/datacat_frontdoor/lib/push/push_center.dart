import 'dart:async';

import 'package:flutter/foundation.dart';

import '../data/api.dart';

/// 푸시 알림의 지금 상태. 설정 화면에 그대로 보여 준다.
enum PushStatus {
  /// 웹 등 푸시를 받을 수 없는 환경
  unsupported,

  /// Firebase 설정 없이 빌드됨
  notConfigured,

  /// 권한 요청·토큰 발급 중
  starting,

  /// 사용자가 알림 권한을 거부함
  denied,

  /// 데모 모드라 서버에 등록하지 않음
  demo,

  /// 서버에 토큰 등록 완료
  registered,

  /// 토큰 발급이나 서버 등록 실패
  failed,
}

/// 푸시 한 건에서 앱이 쓰는 값. API 명세 11.1의 data(`eventId`, `tag`)와 알림 제목·본문.
@immutable
class PushMessage {
  const PushMessage({this.eventId, this.title, this.body});

  final int? eventId;
  final String? title;
  final String? body;

  factory PushMessage.fromData(Map<String, dynamic> data, {String? title, String? body}) {
    final raw = data['eventId'] ?? data['tag']?.toString().replaceFirst('event_', '');
    return PushMessage(eventId: int.tryParse('${raw ?? ''}'), title: title, body: body);
  }
}

/// 실제 푸시 서비스(FCM)와 앱 사이의 얇은 경계. 테스트에서는 가짜로 바꿔 끼운다.
abstract interface class PushBackend {
  /// API 명세 11.1 `platform` 값 (ANDROID / IOS)
  String get platform;

  /// 초기화하고 알림 권한을 요청한다. 권한이 있으면 true.
  Future<bool> start();

  Future<String?> token();
  Stream<String> get tokenRefresh;

  /// 앱이 화면에 떠 있을 때 도착한 푸시 (안드로이드는 이때 알림창에 띄우지 않는다)
  Stream<PushMessage> get foreground;

  /// 알림창의 푸시를 눌러 앱이 열렸을 때
  Stream<PushMessage> get opened;

  /// 앱이 완전히 꺼진 상태에서 알림을 눌러 시작됐다면 그 푸시
  Future<PushMessage?> initialMessage();
}

/// 푸시 토큰을 받아 지금 연결된 서버에 등록하고, 들어온 푸시를 앱에 전달한다.
///
/// 서버 주소가 바뀌면 [attach]로 새 서버에 다시 등록한다. 그래서 지금은 개인 서버(목업 API),
/// 나중에는 실제 Spring 서버로 주소만 바꾸면 그대로 이어진다.
class PushCenter extends ChangeNotifier {
  PushCenter(PushBackend backend) : _backend = backend;

  /// 푸시를 쓸 수 없는 환경 (웹, 테스트, Firebase 설정 없는 빌드)
  PushCenter.disabled({PushStatus reason = PushStatus.unsupported})
      : _backend = null,
        _status = reason;

  final PushBackend? _backend;
  PushStatus _status = PushStatus.starting;
  String _detail = '';
  String? _token;
  DataCatApi? _api;
  bool _started = false;
  bool _granted = false;
  int _attempt = 0;
  final List<StreamSubscription<Object?>> _subs = [];
  final _openedEvents = StreamController<int>.broadcast();

  /// 앱이 떠 있을 때 푸시가 오면 부른다 (새 방문을 바로 불러오게).
  VoidCallback? onForeground;

  PushStatus get status => _status;

  /// 실패 이유나 등록된 서버 이름
  String get detail => _detail;
  String? get token => _token;
  bool get isAvailable => _backend != null;

  /// 알림을 눌러 열어야 할 방문 번호
  Stream<int> get openedEvents => _openedEvents.stream;

  /// 처음 한 번: 권한 요청, 토큰 발급, 서버 등록, 수신 구독.
  Future<void> start(DataCatApi api) async {
    _api = api;
    final backend = _backend;
    if (backend == null || _started) return;
    _started = true;
    _set(PushStatus.starting);
    try {
      _granted = await backend.start();
    } catch (e) {
      _set(PushStatus.failed, '푸시를 시작하지 못했어요 ($e)');
      return;
    }
    if (!_granted) {
      _set(PushStatus.denied);
      return;
    }

    _subs
      ..add(backend.tokenRefresh.listen((t) {
        _token = t;
        _register();
      }))
      ..add(backend.foreground.listen((m) {
        onForeground?.call();
      }))
      ..add(backend.opened.listen(_emitOpened));

    // 꺼진 앱을 알림으로 열었다면 서버 등록을 기다리지 말고 바로 그 방문을 연다
    final initial = await backend.initialMessage().catchError((Object _) => null);
    if (initial != null) _emitOpened(initial);

    try {
      _token = await backend.token();
    } catch (e) {
      _set(PushStatus.failed, '푸시 토큰을 받지 못했어요 ($e)');
      return;
    }
    await _register();
  }

  /// 서버 주소나 데모 모드가 바뀌었을 때 새 서버에 다시 등록한다.
  Future<void> attach(DataCatApi api) async {
    _api = api;
    if (_backend == null || !_granted) return;
    await _register();
  }

  /// 설정 화면의 "다시 시도"
  Future<void> retry() async {
    if (_backend == null) return;
    if (!_started || !_granted || _token == null) {
      _started = false;
      for (final s in _subs) {
        await s.cancel();
      }
      _subs.clear();
      await start(_api!);
    } else {
      await _register();
    }
  }

  Future<void> _register() async {
    final api = _api;
    final token = _token;
    final backend = _backend;
    if (api == null || backend == null) return;
    if (token == null || token.isEmpty) {
      _set(PushStatus.failed, '푸시 토큰이 비어 있어요.');
      return;
    }
    // 늦게 끝난 이전 서버 등록 결과가 지금 상태를 덮어쓰지 않도록 번호를 매긴다
    final attempt = ++_attempt;
    if (api.isDemo) {
      _set(PushStatus.demo);
      return;
    }
    _set(PushStatus.starting);
    try {
      await api.registerPushToken(token: token, platform: backend.platform);
      if (attempt == _attempt) _set(PushStatus.registered, api.label);
    } on ApiException catch (e) {
      if (attempt == _attempt) _set(PushStatus.failed, e.message);
    }
  }

  void _emitOpened(PushMessage m) {
    final id = m.eventId;
    if (id != null) _openedEvents.add(id);
  }

  void _set(PushStatus s, [String detail = '']) {
    _status = s;
    _detail = detail;
    notifyListeners();
  }

  @override
  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    _openedEvents.close();
    super.dispose();
  }
}

extension PushStatusText on PushStatus {
  /// 설정 화면 한 줄 설명
  String describe(String detail) => switch (this) {
        PushStatus.unsupported => '웹에서는 푸시를 받을 수 없어요. 안드로이드 앱에서 켜져요.',
        PushStatus.notConfigured => '이 앱은 Firebase 설정 없이 빌드됐어요. build-apk 스크립트로 다시 빌드해 주세요.',
        PushStatus.starting => '준비하는 중이에요…',
        PushStatus.denied => '알림 권한이 꺼져 있어요. 휴대폰 설정 → 앱 → DataCat 현관 → 알림을 켜 주세요.',
        PushStatus.demo => '데모 모드에서는 서버에 등록하지 않아요. 데모 모드를 끄면 바로 등록돼요.',
        PushStatus.registered => '켜짐 · $detail 서버에 등록됐어요',
        PushStatus.failed => '등록하지 못했어요 · $detail',
      };
}

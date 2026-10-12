import 'dart:async';
import 'dart:convert';

import 'package:datacat_frontdoor/data/api.dart';
import 'package:datacat_frontdoor/data/demo_api.dart';
import 'package:datacat_frontdoor/push/push_center.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class FakeBackend implements PushBackend {
  FakeBackend({this.granted = true, this.initial});

  final bool granted;
  final PushMessage? initial;
  String currentToken = 'token-1';
  final refresh = StreamController<String>.broadcast();
  final fg = StreamController<PushMessage>.broadcast();
  final tapped = StreamController<PushMessage>.broadcast();

  @override
  String get platform => 'ANDROID';
  @override
  Future<bool> start() async => granted;
  @override
  Future<String?> token() async => currentToken;
  @override
  Stream<String> get tokenRefresh => refresh.stream;
  @override
  Stream<PushMessage> get foreground => fg.stream;
  @override
  Stream<PushMessage> get opened => tapped.stream;
  @override
  Future<PushMessage?> initialMessage() async => initial;
}

/// 받은 토큰 등록 요청을 기록하는 가짜 서버
({HttpDataCatApi api, List<Map<String, dynamic>> bodies}) fakeServer({int status = 201}) {
  final bodies = <Map<String, dynamic>>[];
  final client = MockClient((req) async {
    expect(req.method, 'POST');
    expect(req.url.path, '/api/v1/push-tokens');
    bodies.add(jsonDecode(req.body) as Map<String, dynamic>);
    return status == 201
        ? http.Response('{"registered":true}', 201)
        : http.Response.bytes(
            utf8.encode(jsonEncode({'code': 'INVALID_REQUEST', 'message': '토큰이 비었어요.'})),
            status,
          );
  });
  return (api: HttpDataCatApi('http://host:8080', client: client), bodies: bodies);
}

void main() {
  test('PushMessage는 eventId 또는 tag에서 방문 번호를 읽는다', () {
    expect(PushMessage.fromData({'eventId': '101'}).eventId, 101);
    expect(PushMessage.fromData({'tag': 'event_202'}).eventId, 202);
    expect(PushMessage.fromData({'type': 'VISIT_EVENT'}).eventId, isNull);
  });

  test('시작하면 토큰을 API 11.1 형식으로 서버에 등록한다', () async {
    final server = fakeServer();
    final push = PushCenter(FakeBackend());
    await push.start(server.api);

    expect(push.status, PushStatus.registered);
    expect(push.detail, 'host:8080');
    expect(server.bodies.single, {'deviceToken': 'token-1', 'platform': 'ANDROID'});
  });

  test('토큰이 바뀌면 다시 등록하고, 서버가 바뀌면 새 서버에 등록한다', () async {
    final backend = FakeBackend();
    final first = fakeServer();
    final push = PushCenter(backend);
    await push.start(first.api);

    backend.refresh.add('token-2');
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(first.bodies.map((b) => b['deviceToken']), ['token-1', 'token-2']);

    final second = fakeServer();
    await push.attach(second.api);
    expect(second.bodies.single['deviceToken'], 'token-2');
  });

  test('데모 모드에서는 서버에 등록하지 않는다', () async {
    final push = PushCenter(FakeBackend());
    await push.start(DemoDataCatApi(latency: Duration.zero));
    expect(push.status, PushStatus.demo);
  });

  test('권한 거부와 서버 오류를 상태로 알려 준다', () async {
    final denied = PushCenter(FakeBackend(granted: false));
    await denied.start(fakeServer().api);
    expect(denied.status, PushStatus.denied);

    final failing = PushCenter(FakeBackend());
    await failing.start(fakeServer(status: 400).api);
    expect(failing.status, PushStatus.failed);
    expect(failing.detail, '토큰이 비었어요.');
  });

  test('알림을 누르면 방문 번호를 내보내고, 앱이 떠 있을 때 오면 새로고침을 부른다', () async {
    final backend = FakeBackend(initial: const PushMessage(eventId: 7));
    final push = PushCenter(backend);
    final opened = <int>[];
    var refreshed = 0;
    push.openedEvents.listen(opened.add);
    push.onForeground = () => refreshed++;

    await push.start(fakeServer().api);
    backend.tapped.add(const PushMessage(eventId: 9));
    backend.fg.add(const PushMessage(eventId: 10));
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(opened, [7, 9]); // 앱을 연 알림 + 떠 있을 때 누른 알림
    expect(refreshed, 1);
  });

  test('푸시를 못 쓰는 환경은 처음부터 꺼진 상태', () async {
    final push = PushCenter.disabled();
    await push.start(DemoDataCatApi(latency: Duration.zero));
    expect(push.status, PushStatus.unsupported);
    expect(push.isAvailable, isFalse);
  });
}

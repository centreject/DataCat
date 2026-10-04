import 'dart:convert';

import 'package:datacat_frontdoor/core/format.dart';
import 'package:datacat_frontdoor/data/api.dart';
import 'package:datacat_frontdoor/data/category.dart';
import 'package:datacat_frontdoor/data/demo_api.dart';
import 'package:datacat_frontdoor/data/models.dart';
import 'package:datacat_frontdoor/state/event_store.dart';
import 'package:datacat_frontdoor/state/policy.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('VisitEvent.fromJson', () {
    test('API 9.2 상세 응답을 읽는다', () {
      final e = VisitEvent.fromJson({
        'eventId': 101,
        'deviceId': 'door-01',
        'triggerType': 'TOF',
        'eventType': null,
        'purpose': 'DELIVERY',
        'transcript': '택배 왔습니다. 문 앞에 놓고 갈게요.',
        'summary': '택배 배송 방문',
        'status': 'COMPLETED',
        'snapshotUrl': '/api/v1/events/101/snapshot',
        'occurredAt': '2026-09-20T22:30:00+09:00',
        'endedAt': '2026-09-20T22:30:30+09:00',
      });

      expect(e.eventId, 101);
      expect(e.trigger, TriggerType.tof);
      expect(e.status, EventStatus.completed);
      expect(e.hasTranscript, isTrue);
      expect(e.stay, const Duration(seconds: 30));
      expect(e.category, VisitCategory.delivery);
      expect(e.headline, '택배 배송 방문');
    });

    test('상황 분류 기획 17장 형식(한글 status)도 받아낸다', () {
      final e = VisitEvent.fromJson({
        'eventId': '7', // 문자열 id
        'mainCategory': '공공·긴급 방문',
        'subCategory': '긴급 상황',
        'responsePolicy': '긴급 알림',
        'status': '정상',
        'needsReview': true,
        'occurredAt': '2026-09-20T22:30:00+09:00',
      });

      expect(e.eventId, 7);
      expect(e.status, EventStatus.unknown);
      expect(e.processingStatus, '정상');
      expect(e.category, VisitCategory.emergency);
      expect(e.isUrgent, isTrue);
      expect(e.needsAttention, isTrue);
    });

    test('빈 전사문은 말이 없는 것으로 본다', () {
      final e = VisitEvent.fromJson({
        'eventId': 1,
        'transcript': '',
        'summary': '',
        'eventType': 'VISITOR_TIMEOUT',
        'status': 'COMPLETED',
        'occurredAt': '2026-09-20T22:30:00+09:00',
      });
      expect(e.hasTranscript, isFalse);
      expect(e.headline, '용건 없이 떠난 방문객');
      expect(e.scene, DoorScene.empty);
    });
  });

  group('분류 추정', () {
    VisitEvent ev({String? main, String? type, String? purpose}) => VisitEvent(
          eventId: 1,
          occurredAt: DateTime(2026),
          mainCategory: main,
          eventType: type,
          purpose: purpose,
        );

    test('mainCategory가 가장 우선한다', () {
      expect(ev(main: '수거', purpose: 'DELIVERY').category, VisitCategory.pickup);
      expect(ev(main: 'SAFETY_CHECK').category, VisitCategory.safety);
      expect(ev(main: '물품만 있음').category, VisitCategory.packageOnly);
    });

    test('없으면 eventType, 그다음 purpose', () {
      expect(ev(type: 'UNATTENDED_DELIVERY').category, VisitCategory.packageOnly);
      expect(ev(purpose: 'INSPECTION').category, VisitCategory.service);
      expect(ev(purpose: 'VISIT').category, VisitCategory.personal);
      expect(ev().category, VisitCategory.unknown);
    });
  });

  group('EventPage', () {
    test('totalElements로 다음 페이지 여부를 계산한다', () {
      final page = EventPage.fromJson(
        {'content': [], 'page': 0, 'size': 20, 'totalElements': 21},
        requestedSize: 20,
      );
      expect(page.hasMore, isTrue);
    });

    test('Spring Data 기본 형식(last)도 받는다', () {
      final page = EventPage.fromJson(
        {'content': [], 'number': 2, 'size': 20, 'last': true},
        requestedSize: 20,
      );
      expect(page.page, 2);
      expect(page.hasMore, isFalse);
    });
  });

  group('HttpDataCatApi', () {
    test('서버 주소를 같은 형태로 맞춘다', () {
      String n(String s) => HttpDataCatApi.normalizeBaseUrl(s).toString();
      expect(n('192.168.0.12:8080'), 'http://192.168.0.12:8080');
      expect(n('http://host:8080/'), 'http://host:8080');
      expect(n('https://api.datacat.dev/api/v1/'), 'https://api.datacat.dev');
    });

    test('상대 스냅샷 경로를 서버 주소에 붙인다', () {
      final api = HttpDataCatApi('http://10.0.0.5:8080');
      final e = VisitEvent(
        eventId: 1,
        occurredAt: DateTime(2026),
        snapshotUrl: '/api/v1/events/1/snapshot',
      );
      expect(api.snapshotUri(e).toString(), 'http://10.0.0.5:8080/api/v1/events/1/snapshot');
    });

    test('목록 요청 경로와 한글 응답', () async {
      late Uri requested;
      final client = MockClient((req) async {
        requested = req.url;
        return http.Response.bytes(
          utf8.encode(jsonEncode({
            'content': [
              {
                'eventId': 101,
                'summary': '택배 배송 방문',
                'status': 'COMPLETED',
                'occurredAt': '2026-09-20T22:30:00+09:00',
              },
            ],
            'page': 0,
            'size': 20,
            'totalElements': 1,
          })),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final api = HttpDataCatApi('http://host:8080', client: client);
      final page = await api.fetchEvents();

      expect(requested.path, '/api/v1/events');
      expect(requested.queryParameters, {'page': '0', 'size': '20'});
      expect(page.content.single.summary, '택배 배송 방문');
      expect(page.hasMore, isFalse);
    });

    test('오류 응답의 code/message를 그대로 전달한다', () async {
      final client = MockClient((_) async => http.Response.bytes(
            utf8.encode(jsonEncode({'code': 'NOT_FOUND', 'message': '이벤트가 없습니다.'})),
            404,
          ));
      final api = HttpDataCatApi('http://host:8080', client: client);

      await expectLater(
        api.fetchEvent(999),
        throwsA(isA<ApiException>()
            .having((e) => e.code, 'code', 'NOT_FOUND')
            .having((e) => e.message, 'message', '이벤트가 없습니다.')
            .having((e) => e.statusCode, 'statusCode', 404)),
      );
    });

    test('연결 실패는 오프라인 오류로 바꾼다', () async {
      final client = MockClient((_) async => throw http.ClientException('refused'));
      final api = HttpDataCatApi('http://host:8080', client: client);
      await expectLater(
        api.fetchEvents(),
        throwsA(isA<ApiException>().having((e) => e.isOffline, 'isOffline', isTrue)),
      );
    });
  });

  group('KFormat', () {
    final now = DateTime(2026, 10, 2, 21, 0);

    test('시각', () {
      expect(KFormat.clock(DateTime(2026, 1, 1, 0, 5)), '오전 12:05');
      expect(KFormat.clock(DateTime(2026, 1, 1, 22, 30)), '오후 10:30');
    });

    test('상대 시각', () {
      expect(KFormat.relative(now.subtract(const Duration(seconds: 10)), now: now), '방금');
      expect(KFormat.relative(now.subtract(const Duration(minutes: 12)), now: now), '12분 전');
      expect(KFormat.relative(now.subtract(const Duration(hours: 3)), now: now), '3시간 전');
      expect(KFormat.relative(DateTime(2026, 10, 1, 19, 40), now: now), '어제 오후 7:40');
    });

    test('날짜 머리', () {
      expect(KFormat.dayLabel(DateTime(2026, 9, 27), now: now), '9월 27일 (일)');
      expect(KFormat.dayLabel(DateTime(2025, 12, 3), now: now), '2025년 12월 3일 (수)');
    });

    test('머문 시간', () {
      expect(KFormat.duration(const Duration(seconds: 22)), '22초');
      expect(KFormat.duration(const Duration(minutes: 3, seconds: 10)), '3분 10초');
    });
  });

  group('VisitPolicy', () {
    VisitEvent ev(String main, {String? policy}) =>
        VisitEvent(eventId: 1, occurredAt: DateTime(2026), mainCategory: main, responsePolicy: policy);

    test('분류별 알림 켜고 끄기', () {
      final p = VisitPolicy()..notifyPackages = false;
      expect(p.shouldNotify(ev('물품만 있음')), isFalse);
      expect(p.shouldNotify(ev('배송')), isTrue);
      expect(p.shouldNotify(ev('영업·홍보 방문')), isFalse); // 기본값 꺼짐
    });

    test('방해 금지 시간에는 긴급만 알린다 (자정 넘김)', () {
      final p = VisitPolicy()
        ..quietHoursEnabled = true
        ..quietStart = 23
        ..quietEnd = 7;
      final night = DateTime(2026, 10, 4, 2);
      final noon = DateTime(2026, 10, 4, 12);
      expect(p.inQuietHours(night), isTrue);
      expect(p.inQuietHours(noon), isFalse);
      expect(p.shouldNotify(ev('배송'), now: night), isFalse);
      expect(p.shouldNotify(ev('공공·긴급 방문', policy: '긴급 알림'), now: night), isTrue);
      expect(p.shouldNotify(ev('안전 확인 필요'), now: night), isTrue);
    });
  });

  group('EventStore 자동 새로고침', () {
    test('새로 생긴 방문만 새 방문으로 표시한다', () async {
      final demo = DemoDataCatApi(latency: Duration.zero);
      final store = EventStore(demo);
      await store.refresh();
      final before = store.events.length;
      expect(store.unseenIds, isEmpty);

      final e = demo.simulateVisit();
      await store.checkForNew();

      expect(store.events.length, before + 1);
      expect(store.events.first.eventId, e.eventId);
      expect(store.unseenIds, {e.eventId});

      store.markSeen(e.eventId);
      expect(store.unseenIds, isEmpty);
      store.dispose();
    });

    test('알림을 끈 분류는 알림 띠에서 빠진다', () async {
      final demo = DemoDataCatApi(latency: Duration.zero);
      final store = EventStore(demo)..arrivalFilter = (e) => false;
      await store.refresh();
      demo.simulateVisit();
      await store.checkForNew();
      expect(store.unseenIds, hasLength(1));
      expect(store.unseenAlerts, isEmpty);
      store.dispose();
    });
  });
}

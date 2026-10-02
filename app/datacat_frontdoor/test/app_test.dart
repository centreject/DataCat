import 'package:datacat_frontdoor/app.dart';
import 'package:datacat_frontdoor/data/demo_api.dart';
import 'package:datacat_frontdoor/state/event_store.dart';
import 'package:datacat_frontdoor/state/settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

// 화면에 반복 애니메이션(연결 표시 점, 스켈레톤)이 있어 pumpAndSettle 대신
// 정해진 시간만큼 pump한다.
const _afterLoad = Duration(milliseconds: 600);

Future<EventStore> _pumpApp(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});
  final settings = AppSettings();
  await settings.load();
  final store = EventStore(DemoDataCatApi(latency: const Duration(milliseconds: 100)));
  await tester.pumpWidget(DataCatApp(settings: settings, store: store));
  await tester.pump(_afterLoad);
  return store;
}

void main() {
  testWidgets('홈: 가장 최근 방문과 오늘 요약을 보여준다', (tester) async {
    final store = await _pumpApp(tester);

    expect(store.events, isNotEmpty);
    expect(find.text('우리집 현관'), findsOneWidget);
    expect(find.text('데모 모드'), findsOneWidget);
    // 데모의 가장 최근 방문
    expect(find.text('치킨 배달 문 앞 보관'), findsOneWidget);
    expect(find.text('오늘 전체'), findsOneWidget);
  });

  testWidgets('기록 탭: 필터로 확인 필요한 기록만 본다', (tester) async {
    await _pumpApp(tester);

    await tester.tap(find.text('기록'));
    await tester.pump(_afterLoad);
    expect(find.text('방문 기록'), findsOneWidget);
    expect(find.text('오늘'), findsWidgets);

    await tester.tap(find.bySemanticsLabel(RegExp(r'^확인 필요 \d+건$')));
    await tester.pump(_afterLoad);
    expect(find.text('가스 안전점검 재방문 예정'), findsOneWidget);
    expect(find.text('치킨 배달 문 앞 보관'), findsNothing);
  });

  testWidgets('상세: 남긴 말과 처리 과정을 보여준다', (tester) async {
    // 상세 화면은 위쪽 사진이 커서 기본 테스트 화면(800×600)에서는 아래가 잘린다.
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await _pumpApp(tester);

    await tester.tap(find.text('치킨 배달 문 앞 보관'));
    await tester.pump(const Duration(milliseconds: 400)); // 화면 전환
    await tester.pump(_afterLoad); // 상세 불러오기

    expect(find.text('방문객이 남긴 말'), findsOneWidget);
    expect(find.textContaining('배민 주문하신 치킨'), findsOneWidget);
    expect(find.text('호출벨이 눌렸어요'), findsOneWidget);
  });

  testWidgets('설정: 데모 모드를 끄면 실제 서버 연결로 바뀐다', (tester) async {
    final store = await _pumpApp(tester);
    expect(store.api.isDemo, isTrue);

    await tester.tap(find.text('설정').last);
    await tester.pump(_afterLoad);
    await tester.tap(find.byType(Switch));
    await tester.pump();

    expect(store.api.isDemo, isFalse);

    // 테스트 환경에는 서버가 없으니 요청 타임아웃까지 흘려보내 타이머를 정리한다.
    await tester.pump(const Duration(seconds: 9));
    expect(store.error, isNotNull);
  });
}

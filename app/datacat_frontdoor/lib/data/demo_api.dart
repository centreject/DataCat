import 'api.dart';
import 'models.dart';

/// 서버 없이 화면을 확인하기 위한 예시 기록.
///
/// 상황 분류 기획서의 대표 사례(음식 배달, 물품만 있음, 점검, 무응답 이탈,
/// 서버 장애 등)를 하나씩 담아 두어 각 화면 상태를 모두 볼 수 있게 했다.
class DemoDataCatApi implements DataCatApi {
  DemoDataCatApi({
    DateTime? now,
    this.latency = const Duration(milliseconds: 450),
  }) : _events = _buildEvents(now ?? DateTime.now());

  final Duration latency;
  final List<VisitEvent> _events;

  @override
  String get label => '데모';

  @override
  bool get isDemo => true;

  @override
  Future<EventPage> fetchEvents({int page = 0, int size = 20}) async {
    await Future<void>.delayed(latency);
    final start = (page * size).clamp(0, _events.length);
    final end = (start + size).clamp(0, _events.length);
    return EventPage(
      content: _events.sublist(start, end),
      page: page,
      size: size,
      hasMore: end < _events.length,
      totalElements: _events.length,
    );
  }

  @override
  Future<VisitEvent> fetchEvent(int eventId) async {
    await Future<void>.delayed(latency);
    for (final e in _events) {
      if (e.eventId == eventId) return e;
    }
    throw const ApiException('기록을 찾을 수 없어요.', code: 'NOT_FOUND', statusCode: 404);
  }

  @override
  Future<List<Preset>> fetchPresets() async {
    await Future<void>.delayed(latency);
    return const [
      Preset(presetId: 1, type: 'GREETING', text: '마이크에 말씀해 주세요.'),
      Preset(
        presetId: 2,
        type: 'COMPLETION',
        text: '접수되었습니다. 추가 용건이 있으시면 벨을 다시 눌러주세요.',
      ),
      Preset(
        presetId: 3,
        type: 'FALLBACK',
        text: '일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요.',
      ),
    ];
  }

  /// 데모에는 실제 사진이 없으므로 현관 그림을 쓴다.
  @override
  Uri? snapshotUri(VisitEvent event) => null;

  static List<VisitEvent> _buildEvents(DateTime now) {
    DateTime ago(Duration d) => now.subtract(d);
    DateTime daysAgoAt(int days, int hour, int minute) =>
        DateTime(now.year, now.month, now.day - days, hour, minute);

    var id = 112;
    VisitEvent e({
      required DateTime at,
      required Duration stay,
      TriggerType trigger = TriggerType.tof,
      EventStatus status = EventStatus.completed,
      String? eventType,
      String? purpose,
      String? summary,
      String? transcript,
      String? main,
      String? sub,
      String? policy,
      String? processing,
      String? reason,
      bool review = false,
    }) =>
        VisitEvent(
          eventId: id--,
          deviceId: 'door-01',
          occurredAt: at,
          endedAt: at.add(stay),
          trigger: trigger,
          status: status,
          eventType: eventType,
          purpose: purpose,
          summary: summary,
          transcript: transcript,
          mainCategory: main,
          subCategory: sub,
          responsePolicy: policy,
          processingStatus: processing,
          reason: reason,
          needsReview: review,
        );

    final events = <VisitEvent>[
      e(
        at: ago(const Duration(minutes: 4)),
        stay: const Duration(seconds: 22),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'DELIVERY',
        summary: '치킨 배달 문 앞 보관',
        transcript: '배민 주문하신 치킨 왔습니다. 문 앞에 두고 갈게요.',
        main: '배송',
        sub: '음식 배달',
        policy: '일반 접수',
        processing: '정상',
        reason: '음식명(치킨)과 배달 앱 이름이 함께 언급됨',
      ),
      e(
        at: ago(const Duration(minutes: 52)),
        stay: const Duration(seconds: 3),
        eventType: 'UNATTENDED_DELIVERY',
        main: '물품만 있음',
        sub: '택배',
        policy: '무응답',
        processing: '무응답',
        reason: '사람 없음 + 물품 감지 → 출력 없이 스냅샷만 기록',
      ),
      e(
        at: ago(const Duration(hours: 2, minutes: 15)),
        stay: const Duration(seconds: 41),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'INSPECTION',
        summary: '가스 안전점검 재방문 예정',
        transcript: '안녕하세요, 도시가스 안전점검 나왔습니다. '
            '안 계셔서 다음 주 화요일 오전에 다시 방문드릴게요.',
        main: '작업 방문',
        sub: '검침·안전점검',
        policy: '일반 접수',
        processing: '정상',
        reason: '예약 여부를 확인할 수 없어 사용자 확인 필요',
        review: true,
      ),
      e(
        at: ago(const Duration(hours: 5, minutes: 8)),
        stay: const Duration(seconds: 9),
        eventType: 'VISITOR_TIMEOUT',
        main: '기타·판단 불가',
        policy: '무응답',
        processing: '무응답',
        reason: '안내 음성 출력 후 발화 없이 이탈',
      ),
      e(
        at: daysAgoAt(1, 19, 40),
        stay: const Duration(seconds: 18),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'VISIT',
        summary: '친구 민지, 전화 요청',
        transcript: '민지인데요, 연락이 안 돼서 와봤어. 이따 전화 줘!',
        main: '개인 방문',
        sub: '지인',
        policy: '일반 접수',
        processing: '정상',
        reason: '이름과 함께 지인임을 밝힘',
      ),
      e(
        at: daysAgoAt(1, 14, 12),
        stay: const Duration(seconds: 35),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'ETC',
        summary: '인터넷 통신사 변경 권유',
        transcript: '안녕하세요, 이번에 이 동 인터넷 바꾸시면 '
            '석 달 무료로 해드리고 있어서요. 전단지 꽂아두고 갈게요.',
        main: '영업·홍보 방문',
        sub: '판매·영업',
        policy: '일반 접수',
        processing: '정상',
        reason: '통신사 변경·가입 권유 표현',
      ),
      e(
        at: daysAgoAt(1, 11, 3),
        stay: const Duration(seconds: 2),
        eventType: 'UNATTENDED_DELIVERY',
        main: '물품만 있음',
        sub: '택배',
        policy: '무응답',
        processing: '무응답',
        reason: '사람 없음 + 물품 감지',
      ),
      e(
        at: daysAgoAt(1, 9, 20),
        stay: const Duration(seconds: 5),
        status: EventStatus.failed,
        policy: '장애 안내',
        processing: '서버 장애',
        reason: '분석 서버 응답 시간 초과 — 기기가 오류 안내 후 세션을 닫음',
      ),
      e(
        at: daysAgoAt(2, 21, 5),
        stay: const Duration(seconds: 27),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'DELIVERY',
        summary: '반품 상품 회수',
        transcript: '반품 회수하러 왔습니다. 문 앞에 있는 박스 가져갈게요.',
        main: '수거',
        sub: '반품·교환 수거',
        policy: '일반 접수',
        processing: '정상',
        reason: '반품·회수 표현',
      ),
      e(
        at: daysAgoAt(2, 16, 30),
        stay: const Duration(minutes: 3, seconds: 10),
        eventType: 'VISITOR_ACCEPTED',
        main: '안전 확인 필요',
        sub: '장시간 체류',
        policy: '일반 접수',
        processing: '무응답',
        reason: '3분 넘게 머물렀지만 용건을 말하지 않음',
        review: true,
      ),
      e(
        at: daysAgoAt(2, 10, 15),
        stay: const Duration(seconds: 14),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'DELIVERY',
        summary: '호수 착오, 505호 배송',
        transcript: '아 죄송합니다, 503호가 아니라 505호네요.',
        main: '잘못 방문',
        sub: '주소 착오',
        policy: '일반 접수',
        processing: '정상',
        reason: '동·호수가 다르다고 말함',
      ),
      e(
        at: daysAgoAt(3, 18, 2),
        stay: const Duration(seconds: 12),
        trigger: TriggerType.button,
        eventType: 'VISITOR_ACCEPTED',
        purpose: 'DELIVERY',
        summary: '택배 문 앞 보관',
        transcript: '택배입니다. 문 앞에 놓고 갈게요.',
        main: '배송',
        sub: '택배',
        policy: '일반 접수',
        processing: '정상',
        reason: '택배·문 앞 보관 표현',
      ),
    ];

    events.sort((a, b) => b.occurredAt.compareTo(a.occurredAt));
    return events;
  }
}

// API 명세 v1.4 (9장 앱 API, 10장 프리셋)와
// 상황 분류 기획 17장 "서버가 반환할 값"을 함께 담는 데이터 모델.
//
// 서버가 아직 분류 필드(mainCategory 등)를 보내지 않아도 동작하도록
// 모든 확장 필드는 선택값으로 둔다.

enum TriggerType {
  tof('현관 앞 감지'),
  button('호출벨'),
  unknown('알 수 없음');

  const TriggerType(this.label);
  final String label;

  static TriggerType parse(Object? raw) => switch (raw) {
        'TOF' => TriggerType.tof,
        'BUTTON' => TriggerType.button,
        _ => TriggerType.unknown,
      };
}

/// API 5.2 EventStatus. 실제로 응답에 등장하는 세 값만 다룬다.
enum EventStatus {
  waitingAudio,
  completed,
  failed,
  unknown;

  static EventStatus? tryParse(Object? raw) => switch (raw) {
        'WAITING_AUDIO' => EventStatus.waitingAudio,
        'COMPLETED' => EventStatus.completed,
        'FAILED' => EventStatus.failed,
        _ => null,
      };
}

class VisitEvent {
  const VisitEvent({
    required this.eventId,
    required this.occurredAt,
    this.deviceId = '',
    this.trigger = TriggerType.unknown,
    this.status = EventStatus.unknown,
    this.eventType,
    this.purpose,
    this.summary,
    this.transcript,
    this.snapshotUrl,
    this.endedAt,
    this.mainCategory,
    this.subCategory,
    this.responsePolicy,
    this.processingStatus,
    this.reason,
    this.needsReview = false,
  });

  final int eventId;
  final String deviceId;
  final TriggerType trigger;
  final EventStatus status;

  /// Spring이 최종 판정한 상황 (API 8장). 기획 확정 전에는 null일 수 있다.
  final String? eventType;

  /// 자연어 모델의 용건 분석 결과 (DELIVERY / INSPECTION / VISIT / ETC)
  final String? purpose;
  final String? summary;
  final String? transcript;
  final String? snapshotUrl;
  final DateTime occurredAt;
  final DateTime? endedAt;

  // ── 상황 분류 기획 17장 (서버 구현 시 채워짐) ──
  final String? mainCategory;
  final String? subCategory;
  final String? responsePolicy;

  /// 기획서의 "처리 상태" (정상, 무응답, STT 실패 …). API의 status와 구분한다.
  final String? processingStatus;
  final String? reason;
  final bool needsReview;

  bool get hasTranscript => (transcript ?? '').trim().isNotEmpty;
  bool get hasSummary => (summary ?? '').trim().isNotEmpty;
  Duration? get stay => endedAt?.difference(occurredAt);

  factory VisitEvent.fromJson(Map<String, dynamic> json) {
    final rawStatus = json['status'];
    final apiStatus = EventStatus.tryParse(rawStatus);
    return VisitEvent(
      eventId: _int(json['eventId']) ?? 0,
      deviceId: _str(json['deviceId']) ?? '',
      trigger: TriggerType.parse(json['triggerType']),
      status: apiStatus ?? EventStatus.unknown,
      eventType: _str(json['eventType']),
      purpose: _str(json['purpose']),
      summary: _str(json['summary']),
      transcript: _str(json['transcript']),
      snapshotUrl: _str(json['snapshotUrl']),
      occurredAt: _date(json['occurredAt']) ?? DateTime.now(),
      endedAt: _date(json['endedAt']),
      mainCategory: _str(json['mainCategory']),
      subCategory: _str(json['subCategory']),
      responsePolicy: _str(json['responsePolicy']),
      // 기획서 형식처럼 status에 "정상", "무응답" 같은 처리 상태가 오면 여기로 보낸다.
      processingStatus: _str(json['processingStatus']) ??
          (apiStatus == null ? _str(rawStatus) : null),
      reason: _str(json['reason']),
      needsReview: json['needsReview'] == true,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is VisitEvent &&
      other.eventId == eventId &&
      other.status == status &&
      other.summary == summary &&
      other.transcript == transcript &&
      other.endedAt == endedAt;

  @override
  int get hashCode => Object.hash(eventId, status, summary, transcript, endedAt);
}

class EventPage {
  const EventPage({
    required this.content,
    required this.page,
    required this.size,
    required this.hasMore,
    this.totalElements,
  });

  final List<VisitEvent> content;
  final int page;
  final int size;
  final bool hasMore;
  final int? totalElements;

  /// `{content, page, size, totalElements}` 형식(API 9.1)과
  /// Spring Data 기본 형식(`number`, `last`)을 모두 받는다.
  factory EventPage.fromJson(Object? json, {required int requestedSize}) {
    if (json is List) {
      final items = _events(json);
      return EventPage(
        content: items,
        page: 0,
        size: requestedSize,
        hasMore: items.length >= requestedSize,
      );
    }
    final map = json is Map<String, dynamic> ? json : const <String, dynamic>{};
    final items = _events(map['content']);
    final page = _int(map['page']) ?? _int(map['number']) ?? 0;
    final size = _int(map['size']) ?? requestedSize;
    final total = _int(map['totalElements']);
    final last = map['last'];
    final hasMore = last is bool
        ? !last
        : total != null
            ? (page + 1) * size < total
            : items.length >= size;
    return EventPage(
      content: items,
      page: page,
      size: size,
      hasMore: hasMore,
      totalElements: total,
    );
  }

  static List<VisitEvent> _events(Object? raw) => raw is List
      ? raw
          .whereType<Map<String, dynamic>>()
          .map(VisitEvent.fromJson)
          .toList()
      : <VisitEvent>[];
}

class Preset {
  const Preset({required this.presetId, required this.type, required this.text});

  final int presetId;
  final String type;
  final String text;

  String get typeLabel => switch (type) {
        'GREETING' => '첫 안내',
        'COMPLETION' => '접수 완료',
        'FALLBACK' || 'ERROR' => '오류 안내',
        _ => type,
      };

  factory Preset.fromJson(Map<String, dynamic> json) => Preset(
        presetId: _int(json['presetId']) ?? 0,
        type: _str(json['type']) ?? '',
        text: _str(json['text']) ?? '',
      );
}

// ── 파싱 도우미: 서버 값이 숫자/문자열 어느 쪽으로 와도 받아낸다 ──

int? _int(Object? v) => switch (v) {
      final int i => i,
      final num n => n.toInt(),
      final String s => int.tryParse(s),
      _ => null,
    };

String? _str(Object? v) {
  if (v == null) return null;
  final s = v.toString();
  return s.isEmpty ? null : s;
}

DateTime? _date(Object? v) =>
    v is String ? DateTime.tryParse(v)?.toLocal() : null;

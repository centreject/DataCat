import '../domain/door_event.dart';
import '../domain/event_repository.dart';

class MockEventRepository implements EventRepository {
  @override
  Future<List<DoorEvent>> fetchEvents() async {
    final now = DateTime.now();
    final events = [
      DoorEvent(
        id: 'demo-parcel',
        occurredAt: now.subtract(const Duration(minutes: 10)),
        situation: SituationType.parcel,
        summary: '택배 배송을 위해 방문했습니다.',
        transcript: '안녕하세요. 택배 왔습니다. 문 앞에 놓고 갈게요.',
      ),
      DoorEvent(
        id: 'demo-food',
        occurredAt: now.subtract(const Duration(hours: 2)),
        situation: SituationType.foodDelivery,
        summary: '주문한 음식을 전달했습니다.',
        transcript: '주문하신 음식 배달 왔습니다.',
      ),
      DoorEvent(
        id: 'demo-review',
        occurredAt: now.subtract(const Duration(days: 1)),
        situation: SituationType.safetyReview,
        summary: '장시간 체류가 감지되어 사용자 확인이 필요합니다.',
      ),
    ]..sort((a, b) => b.occurredAt.compareTo(a.occurredAt));
    return List.unmodifiable(events);
  }
}

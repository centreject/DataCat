import 'door_event.dart';

abstract interface class EventRepository {
  /// Returns events ordered by occurrence time, newest first.
  Future<List<DoorEvent>> fetchEvents();
}

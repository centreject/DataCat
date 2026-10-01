enum SituationType {
  objectOnly,
  parcel,
  foodDelivery,
  pickup,
  publicVisit,
  maintenance,
  personalVisit,
  promotion,
  wrongVisit,
  safetyReview,
  unknown,
}

class DoorEvent {
  const DoorEvent({
    required this.id,
    required this.occurredAt,
    required this.situation,
    required this.summary,
    this.transcript,
  });

  final String id;
  final DateTime occurredAt;
  final SituationType situation;
  final String summary;
  final String? transcript;
}

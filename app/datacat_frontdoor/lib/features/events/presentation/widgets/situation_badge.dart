import 'package:flutter/material.dart';

import '../../domain/door_event.dart';

extension SituationPresentation on SituationType {
  String get label => switch (this) {
    SituationType.objectOnly => '물품만 있음',
    SituationType.parcel => '택배·우편',
    SituationType.foodDelivery => '음식 배달',
    SituationType.pickup => '수거',
    SituationType.publicVisit => '공공 방문',
    SituationType.maintenance => '작업·관리 방문',
    SituationType.personalVisit => '개인 방문',
    SituationType.promotion => '영업·홍보 방문',
    SituationType.wrongVisit => '잘못 방문',
    SituationType.safetyReview => '안전 확인 필요',
    SituationType.unknown => '기타·판단 불가',
  };

  IconData get icon => switch (this) {
    SituationType.parcel ||
    SituationType.objectOnly => Icons.inventory_2_outlined,
    SituationType.foodDelivery => Icons.restaurant_outlined,
    SituationType.pickup => Icons.local_shipping_outlined,
    SituationType.maintenance => Icons.build_outlined,
    SituationType.safetyReview => Icons.warning_amber_rounded,
    SituationType.unknown => Icons.more_horiz,
    _ => Icons.person_outline,
  };
}

class SituationBadge extends StatelessWidget {
  const SituationBadge({required this.situation, super.key});

  final SituationType situation;

  @override
  Widget build(BuildContext context) {
    final warning = situation == SituationType.safetyReview;
    return Row(
      children: [
        CircleAvatar(
          backgroundColor: warning
              ? const Color(0xFFFFE4AD)
              : const Color(0xFFE8F2E9),
          child: Icon(
            situation.icon,
            color: warning ? const Color(0xFF895800) : const Color(0xFF5E8768),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            situation.label,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
      ],
    );
  }
}

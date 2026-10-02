import 'package:flutter/material.dart';

import 'models.dart';

/// 상황 분류 기획의 상위 분류 10종을 앱 화면용으로 옮긴 것.
///
/// 서버가 `mainCategory`를 보내면 그것을 그대로 쓰고,
/// 아직 없으면 `eventType` → `purpose` 순서로 가장 가까운 분류를 추정한다.
enum VisitCategory {
  packageOnly('물품 도착', Icons.inventory_2_outlined, Color(0xFFB07A3B)),
  delivery('배송', Icons.local_shipping_outlined, Color(0xFF1F7A68)),
  pickup('수거', Icons.move_up_outlined, Color(0xFF6D7A2E)),
  personal('개인 방문', Icons.waving_hand_outlined, Color(0xFF3A6DB5)),
  service('작업 방문', Icons.handyman_outlined, Color(0xFF6A58A6)),
  emergency('공공·긴급', Icons.emergency_outlined, Color(0xFFC7433A)),
  sales('영업·홍보', Icons.campaign_outlined, Color(0xFF8B7A6B)),
  wrongVisit('잘못 방문', Icons.wrong_location_outlined, Color(0xFF7B8490)),
  safety('안전 확인', Icons.shield_outlined, Color(0xFFCF6B24)),
  unknown('기타', Icons.help_outline, Color(0xFF8D8F94));

  const VisitCategory(this.label, this.icon, this.tone);

  final String label;
  final IconData icon;

  /// 라이트 테마 기준 색. 다크 테마에서는 [Palette.tone]이 밝기를 올려 쓴다.
  final Color tone;

  /// 배송 탭에 묶이는 분류
  bool get isDeliveryLike =>
      this == packageOnly || this == delivery || this == pickup;

  static VisitCategory of(VisitEvent e) {
    final fromMain = _fromMain(e.mainCategory);
    if (fromMain != null) return fromMain;

    switch (e.eventType) {
      case 'UNATTENDED_DELIVERY':
        return packageOnly;
      case 'VISITOR_TIMEOUT':
        return unknown;
    }

    return switch (e.purpose) {
      'DELIVERY' => delivery,
      'INSPECTION' => service,
      'VISIT' => personal,
      'PICKUP' => pickup,
      _ => unknown,
    };
  }

  static VisitCategory? _fromMain(String? raw) {
    if (raw == null) return null;
    final key = raw.replaceAll(RegExp(r'[\s·・_\-]'), '').toUpperCase();
    return _aliases[key];
  }

  static final Map<String, VisitCategory> _aliases = {
    for (final entry in <VisitCategory, List<String>>{
      packageOnly: ['PACKAGE_ONLY', '물품만있음', '물품도착'],
      delivery: ['DELIVERY', '배송'],
      pickup: ['PICKUP', '수거'],
      personal: ['PERSONAL_VISIT', 'PERSONAL', '개인방문'],
      service: ['SERVICE_VISIT', 'SERVICE', 'WORK_VISIT', '작업방문'],
      emergency: ['PUBLIC_EMERGENCY', 'EMERGENCY', '공공긴급방문', '공공긴급'],
      sales: ['SALES_PROMOTION', 'SALES', '영업홍보방문', '영업홍보'],
      wrongVisit: ['WRONG_VISIT', '잘못방문'],
      safety: ['SAFETY_CHECK', 'SAFETY', '안전확인필요', '안전확인'],
      unknown: ['UNKNOWN', 'ETC', '기타판단불가', '기타'],
    }.entries)
      for (final alias in entry.value)
        alias.replaceAll('_', ''): entry.key,
  };
}

/// 현관 그림에 무엇을 그릴지 (스냅샷이 없을 때 대신 보여준다)
enum DoorScene { empty, package, person, personWithPackage }

extension VisitEventView on VisitEvent {
  VisitCategory get category => VisitCategory.of(this);

  bool get visitorLeftSilently => eventType == 'VISITOR_TIMEOUT';

  bool get isUrgent =>
      category == VisitCategory.emergency ||
      responsePolicy == 'EMERGENCY_ALERT' ||
      responsePolicy == '긴급 알림';

  /// 사용자가 한 번 들여다봐야 하는 기록
  bool get needsAttention =>
      needsReview ||
      isUrgent ||
      category == VisitCategory.safety ||
      status == EventStatus.failed;

  /// 목록과 상세 화면의 제목. 요약이 있으면 요약, 없으면 상황을 설명하는 문장.
  String get headline {
    if (hasSummary) return summary!.trim();
    if (status == EventStatus.failed) return '처리하지 못한 방문';
    if (status == EventStatus.waitingAudio) return '방문객의 말을 듣는 중';
    if (visitorLeftSilently) return '용건 없이 떠난 방문객';
    if (category == VisitCategory.packageOnly) return '문 앞에 물품이 놓였어요';
    return '용건이 기록되지 않은 방문';
  }

  DoorScene get scene {
    if (status == EventStatus.failed || visitorLeftSilently) {
      return DoorScene.empty;
    }
    return switch (category) {
      VisitCategory.packageOnly => DoorScene.package,
      VisitCategory.delivery || VisitCategory.pickup =>
        DoorScene.personWithPackage,
      _ => DoorScene.person,
    };
  }
}

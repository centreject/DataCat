import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../data/category.dart';
import '../data/models.dart';

/// 현관이 부재 중에 어떻게 응대할지 (기획서 1.2 "사용자가 정한 정책 범위")
enum ReceptionMode {
  /// 사람이 오면 안내 음성 → 녹음 → 요약까지 (기본)
  voice('음성으로 용건 받기', '사람이 오면 안내 음성 후 용건을 녹음해 요약해요'),

  /// 사람이 와도 말을 걸지 않고 스냅샷만 남김
  silent('기록만 남기기', '안내 음성 없이 스냅샷과 시각만 기록해요');

  const ReceptionMode(this.label, this.description);
  final String label;
  final String description;
}

/// 알림·응대 정책.
///
/// 아직 서버 API(정책 저장)가 없어서 이 기기에만 저장한다.
/// 서버가 준비되면 [toJson] 형태로 그대로 보내면 된다.
class VisitPolicy extends ChangeNotifier {
  static const _prefix = 'policy.';

  SharedPreferences? _prefs;

  bool notifyPackages = true; // 물품 도착 (사람 없음)
  bool notifyDeliveries = true; // 배송·수거 방문
  bool notifyVisitors = true; // 개인·작업·공공 방문
  bool notifySales = false; // 영업·홍보, 잘못 방문
  bool quietHoursEnabled = false;
  int quietStart = 23; // 시 (0~23)
  int quietEnd = 7;
  ReceptionMode reception = ReceptionMode.voice;

  Future<void> load() async {
    try {
      final p = await SharedPreferences.getInstance();
      _prefs = p;
      notifyPackages = p.getBool('${_prefix}packages') ?? notifyPackages;
      notifyDeliveries = p.getBool('${_prefix}deliveries') ?? notifyDeliveries;
      notifyVisitors = p.getBool('${_prefix}visitors') ?? notifyVisitors;
      notifySales = p.getBool('${_prefix}sales') ?? notifySales;
      quietHoursEnabled = p.getBool('${_prefix}quiet') ?? quietHoursEnabled;
      quietStart = p.getInt('${_prefix}quietStart') ?? quietStart;
      quietEnd = p.getInt('${_prefix}quietEnd') ?? quietEnd;
      reception = ReceptionMode.values.asNameMap()[p.getString('${_prefix}reception')] ?? reception;
    } catch (e) {
      debugPrint('정책을 불러오지 못했어요: $e');
    }
  }

  /// 값을 바꾸고 저장한다. 예) policy.update(() => policy.notifySales = true)
  Future<void> update(VoidCallback change) async {
    change();
    notifyListeners();
    final p = _prefs;
    if (p == null) return;
    await Future.wait([
      p.setBool('${_prefix}packages', notifyPackages),
      p.setBool('${_prefix}deliveries', notifyDeliveries),
      p.setBool('${_prefix}visitors', notifyVisitors),
      p.setBool('${_prefix}sales', notifySales),
      p.setBool('${_prefix}quiet', quietHoursEnabled),
      p.setInt('${_prefix}quietStart', quietStart),
      p.setInt('${_prefix}quietEnd', quietEnd),
      p.setString('${_prefix}reception', reception.name),
    ]);
  }

  /// 긴급·안전 확인은 정책과 상관없이 항상 알린다 (분류 문서 8·11장)
  bool shouldNotify(VisitEvent e, {DateTime? now}) {
    if (e.isUrgent || e.category == VisitCategory.safety) return true;
    if (inQuietHours(now ?? DateTime.now())) return false;
    return switch (e.category) {
      VisitCategory.packageOnly => notifyPackages,
      VisitCategory.delivery || VisitCategory.pickup => notifyDeliveries,
      VisitCategory.sales || VisitCategory.wrongVisit => notifySales,
      _ => notifyVisitors,
    };
  }

  bool inQuietHours(DateTime t) {
    if (!quietHoursEnabled || quietStart == quietEnd) return false;
    final h = t.hour;
    return quietStart < quietEnd
        ? h >= quietStart && h < quietEnd
        : h >= quietStart || h < quietEnd; // 23시 ~ 7시처럼 자정을 넘는 경우
  }

  Map<String, Object> toJson() => {
        'notify': {
          'packages': notifyPackages,
          'deliveries': notifyDeliveries,
          'visitors': notifyVisitors,
          'sales': notifySales,
        },
        'quietHours': {'enabled': quietHoursEnabled, 'start': quietStart, 'end': quietEnd},
        'reception': reception.name.toUpperCase(),
      };
}

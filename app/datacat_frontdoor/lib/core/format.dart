/// 한국어 날짜·시간 표기. intl 패키지 없이 앱에 필요한 형식만 다룬다.
abstract final class KFormat {
  static const _weekdays = ['월', '화', '수', '목', '금', '토', '일'];

  /// 오전 / 오후
  static String meridiem(DateTime t) => t.hour < 12 ? '오전' : '오후';

  /// 10:30 (12시간제)
  static String hm(DateTime t) {
    final h12 = t.hour % 12 == 0 ? 12 : t.hour % 12;
    return '$h12:${t.minute.toString().padLeft(2, '0')}';
  }

  /// 오후 10:30
  static String clock(DateTime t) => '${meridiem(t)} ${hm(t)}';

  static String weekday(DateTime t) => _weekdays[t.weekday - 1];

  /// 10월 2일 금요일
  static String fullDate(DateTime t) =>
      '${t.month}월 ${t.day}일 ${weekday(t)}요일';

  static DateTime dayOf(DateTime t) => DateTime(t.year, t.month, t.day);

  static bool isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  /// 오늘 / 어제 / 9월 28일 (일) / 2025년 12월 3일 (수)
  static String dayLabel(DateTime t, {DateTime? now}) {
    final today = dayOf(now ?? DateTime.now());
    final diff = today.difference(dayOf(t)).inDays;
    if (diff == 0) return '오늘';
    if (diff == 1) return '어제';
    final md = '${t.month}월 ${t.day}일 (${weekday(t)})';
    return t.year == today.year ? md : '${t.year}년 $md';
  }

  /// 방금 / 12분 전 / 3시간 전 / 어제 오후 7:40 / 9월 28일 (일) 오전 9:20
  static String relative(DateTime t, {DateTime? now}) {
    final n = now ?? DateTime.now();
    final diff = n.difference(t);
    if (diff.inSeconds < 60) return '방금';
    if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
    if (isSameDay(t, n)) return '${diff.inHours}시간 전';
    return '${dayLabel(t, now: n)} ${clock(t)}';
  }

  /// 22초 / 3분 / 3분 10초
  static String duration(Duration d) {
    final secs = d.inSeconds.abs();
    if (secs < 60) return '$secs초';
    final m = secs ~/ 60;
    final s = secs % 60;
    return s == 0 ? '$m분' : '$m분 $s초';
  }
}

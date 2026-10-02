import 'package:flutter/material.dart';

import '../data/category.dart';

/// 디자인 토큰.
///
/// 방향: 종이 위의 잉크. 따뜻한 미색 바탕에 거의 검은 글자,
/// 색은 "분류"와 "상태"를 알릴 때만 쓴다. 장식용 색은 없다.
@immutable
class Palette extends ThemeExtension<Palette> {
  const Palette({
    required this.isDark,
    required this.paper,
    required this.card,
    required this.sunken,
    required this.ink,
    required this.inkSoft,
    required this.inkFaint,
    required this.line,
    required this.accent,
    required this.live,
    required this.attention,
    required this.danger,
  });

  final bool isDark;

  /// 화면 바탕
  final Color paper;

  /// 카드·입력칸 바탕
  final Color card;

  /// 한 단계 들어간 면 (인용문, 스켈레톤, 그림 바탕)
  final Color sunken;

  final Color ink;
  final Color inkSoft;
  final Color inkFaint;
  final Color line;

  /// 링크·포커스
  final Color accent;

  /// 정상 연결
  final Color live;

  /// 확인 필요
  final Color attention;

  /// 긴급·오류
  final Color danger;

  static const light = Palette(
    isDark: false,
    paper: Color(0xFFF4F1EA),
    card: Color(0xFFFFFFFF),
    sunken: Color(0xFFEAE6DD),
    ink: Color(0xFF1B1D1F),
    inkSoft: Color(0xFF5E636B),
    inkFaint: Color(0xFF9A9EA5),
    line: Color(0xFFE2DDD2),
    accent: Color(0xFF1E5B52),
    live: Color(0xFF2E9E6A),
    attention: Color(0xFFB7791F),
    danger: Color(0xFFC0392B),
  );

  static const dark = Palette(
    isDark: true,
    paper: Color(0xFF121413),
    card: Color(0xFF1B1E1D),
    sunken: Color(0xFF242826),
    ink: Color(0xFFECEAE4),
    inkSoft: Color(0xFFA9AEB3),
    inkFaint: Color(0xFF6E7378),
    line: Color(0xFF2C302E),
    accent: Color(0xFF7CC8B6),
    live: Color(0xFF4CC38A),
    attention: Color(0xFFE0A84A),
    danger: Color(0xFFEF6F61),
  );

  /// 분류 색. 다크 테마에서는 바탕과 대비가 나도록 밝게 올린다.
  Color tone(VisitCategory category) {
    if (!isDark) return category.tone;
    final hsl = HSLColor.fromColor(category.tone);
    return hsl.withLightness(0.70).withSaturation(hsl.saturation * 0.85).toColor();
  }

  @override
  Palette copyWith({
    bool? isDark,
    Color? paper,
    Color? card,
    Color? sunken,
    Color? ink,
    Color? inkSoft,
    Color? inkFaint,
    Color? line,
    Color? accent,
    Color? live,
    Color? attention,
    Color? danger,
  }) =>
      Palette(
        isDark: isDark ?? this.isDark,
        paper: paper ?? this.paper,
        card: card ?? this.card,
        sunken: sunken ?? this.sunken,
        ink: ink ?? this.ink,
        inkSoft: inkSoft ?? this.inkSoft,
        inkFaint: inkFaint ?? this.inkFaint,
        line: line ?? this.line,
        accent: accent ?? this.accent,
        live: live ?? this.live,
        attention: attention ?? this.attention,
        danger: danger ?? this.danger,
      );

  @override
  Palette lerp(ThemeExtension<Palette>? other, double t) {
    if (other is! Palette) return this;
    Color c(Color a, Color b) => Color.lerp(a, b, t)!;
    return Palette(
      isDark: t < 0.5 ? isDark : other.isDark,
      paper: c(paper, other.paper),
      card: c(card, other.card),
      sunken: c(sunken, other.sunken),
      ink: c(ink, other.ink),
      inkSoft: c(inkSoft, other.inkSoft),
      inkFaint: c(inkFaint, other.inkFaint),
      line: c(line, other.line),
      accent: c(accent, other.accent),
      live: c(live, other.live),
      attention: c(attention, other.attention),
      danger: c(danger, other.danger),
    );
  }
}

/// 간격과 모서리. 4의 배수만 쓴다.
abstract final class Gap {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 28;

  /// 화면 좌우 여백
  static const double page = 20;
}

abstract final class Corner {
  static const small = BorderRadius.all(Radius.circular(12));
  static const medium = BorderRadius.all(Radius.circular(16));
  static const large = BorderRadius.all(Radius.circular(24));
  static const pill = BorderRadius.all(Radius.circular(999));
}

extension ThemeContext on BuildContext {
  Palette get palette => Theme.of(this).extension<Palette>()!;
  TextTheme get text => Theme.of(this).textTheme;
}

abstract final class AppTheme {
  static ThemeData light() => _build(Palette.light, Brightness.light);
  static ThemeData dark() => _build(Palette.dark, Brightness.dark);

  static ThemeData _build(Palette p, Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1E5B52),
      brightness: brightness,
    ).copyWith(
      primary: p.accent,
      surface: p.paper,
      onSurface: p.ink,
      onSurfaceVariant: p.inkSoft,
      outline: p.line,
      outlineVariant: p.line,
      surfaceContainerLowest: p.card,
      surfaceContainerLow: p.card,
      surfaceContainer: p.card,
      surfaceContainerHigh: p.sunken,
      surfaceContainerHighest: p.sunken,
      error: p.danger,
    );

    final base = ThemeData(colorScheme: scheme, useMaterial3: true);
    final t = base.textTheme.apply(bodyColor: p.ink, displayColor: p.ink);

    return base.copyWith(
      scaffoldBackgroundColor: p.paper,
      extensions: [p],
      textTheme: t.copyWith(
        headlineMedium: t.headlineMedium?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.8,
          height: 1.25,
        ),
        headlineSmall: t.headlineSmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
          height: 1.3,
        ),
        titleLarge: t.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
        ),
        titleMedium: t.titleMedium?.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
          height: 1.35,
        ),
        bodyLarge: t.bodyLarge?.copyWith(height: 1.55, letterSpacing: -0.1),
        bodyMedium: t.bodyMedium?.copyWith(height: 1.5, color: p.inkSoft),
        bodySmall: t.bodySmall?.copyWith(height: 1.45, color: p.inkSoft),
        labelLarge: t.labelLarge?.copyWith(fontWeight: FontWeight.w600),
        labelMedium: t.labelMedium?.copyWith(fontWeight: FontWeight.w600),
      ),
      dividerTheme: DividerThemeData(color: p.line, thickness: 1, space: 1),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: p.paper,
        surfaceTintColor: Colors.transparent,
        indicatorColor: p.ink.withValues(alpha: p.isDark ? 0.14 : 0.07),
        elevation: 0,
        height: 68,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 12,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
            color: states.contains(WidgetState.selected) ? p.ink : p.inkFaint,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            size: 24,
            color: states.contains(WidgetState.selected) ? p.ink : p.inkFaint,
          ),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: p.ink,
        contentTextStyle: TextStyle(color: p.paper, fontSize: 14),
        shape: const RoundedRectangleBorder(borderRadius: Corner.small),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: p.ink,
          foregroundColor: p.paper,
          minimumSize: const Size(0, 48),
          shape: const RoundedRectangleBorder(borderRadius: Corner.small),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: p.ink,
          minimumSize: const Size(0, 48),
          side: BorderSide(color: p.line, width: 1.2),
          shape: const RoundedRectangleBorder(borderRadius: Corner.small),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: p.accent,
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      switchTheme: SwitchThemeData(
        trackColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? p.accent : p.sunken,
        ),
        thumbColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? p.card : p.inkFaint,
        ),
        trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: p.ink,
        linearTrackColor: p.sunken,
      ),
    );
  }
}

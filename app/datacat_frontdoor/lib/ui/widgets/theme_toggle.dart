import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../state/app_scope.dart';

/// 화면 오른쪽 위의 해/달 버튼.
///
/// 라이트일 때는 달(누르면 어두워짐), 다크일 때는 해(누르면 밝아짐)를 보여준다.
/// 아이콘은 돌면서 바뀌고, 화면 색은 MaterialApp 의 테마 애니메이션으로 부드럽게 넘어간다.
class ThemeToggle extends StatelessWidget {
  const ThemeToggle({super.key, this.size = 40});

  final double size;

  @override
  Widget build(BuildContext context) {
    final settings = AppScope.of(context).settings;
    final p = context.palette;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Tooltip(
      message: isDark ? '라이트 모드로 바꾸기' : '다크 모드로 바꾸기',
      child: Semantics(
        button: true,
        label: isDark ? '라이트 모드로 바꾸기' : '다크 모드로 바꾸기',
        excludeSemantics: true,
        child: Material(
          color: p.card,
          shape: CircleBorder(side: BorderSide(color: p.line)),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => settings.toggleTheme(Theme.of(context).brightness),
            child: SizedBox.square(
              dimension: size,
              child: Center(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 450),
                  switchInCurve: Curves.easeOutBack,
                  switchOutCurve: Curves.easeIn,
                  transitionBuilder: (child, anim) => RotationTransition(
                    turns: Tween(begin: -0.35, end: 0.0).animate(anim),
                    child: ScaleTransition(
                      scale: anim,
                      child: FadeTransition(opacity: anim, child: child),
                    ),
                  ),
                  child: isDark
                      ? _Sun(key: const ValueKey('sun'), color: p.attention, size: size * 0.5)
                      : Icon(Icons.dark_mode_rounded,
                          key: const ValueKey('moon'), size: size * 0.5, color: p.ink),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 해: 가운데 원 + 짧은 빛살 8개 (아이콘 폰트보다 또렷하게 그린다)
class _Sun extends StatelessWidget {
  const _Sun({super.key, required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) =>
      CustomPaint(size: Size.square(size), painter: _SunPainter(color));
}

class _SunPainter extends CustomPainter {
  _SunPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    canvas.drawCircle(c, r * 0.42, Paint()..color = color);
    final ray = Paint()
      ..color = color
      ..strokeWidth = r * 0.16
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 8; i++) {
      final a = i * math.pi / 4;
      final d = Offset(math.cos(a), math.sin(a));
      canvas.drawLine(c + d * (r * 0.66), c + d * (r * 0.92), ray);
    }
  }

  @override
  bool shouldRepaint(_SunPainter old) => old.color != color;
}

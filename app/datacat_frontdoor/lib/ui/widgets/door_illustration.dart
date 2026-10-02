import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../data/category.dart';

/// 스냅샷이 없을 때(데모 모드, 이미지 로딩 실패) 보여주는 현관 그림.
///
/// 문, 바닥, 그리고 상황에 따라 사람·물품의 실루엣만 단순한 도형으로 그린다.
/// 얼굴이나 신원을 암시하는 요소는 일부러 넣지 않았다.
class DoorIllustration extends StatelessWidget {
  const DoorIllustration({super.key, required this.scene, required this.tone});

  final DoorScene scene;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return CustomPaint(
      painter: _DoorPainter(
        scene: scene,
        tone: tone,
        base: p.sunken,
        ink: p.ink,
        isDark: p.isDark,
      ),
      child: const SizedBox.expand(),
    );
  }
}

class _DoorPainter extends CustomPainter {
  _DoorPainter({
    required this.scene,
    required this.tone,
    required this.base,
    required this.ink,
    required this.isDark,
  });

  final DoorScene scene;
  final Color tone;
  final Color base;
  final Color ink;
  final bool isDark;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final unit = h; // 세로 기준으로 비율을 맞춘다
    final floorY = h * 0.80;

    // 벽
    final wall = Rect.fromLTWH(0, 0, w, floorY);
    canvas.drawRect(
      wall,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color.alphaBlend(tone.withValues(alpha: isDark ? 0.10 : 0.14), base),
            Color.alphaBlend(tone.withValues(alpha: isDark ? 0.04 : 0.05), base),
          ],
        ).createShader(wall),
    );

    // 바닥
    canvas.drawRect(
      Rect.fromLTWH(0, floorY, w, h - floorY),
      Paint()..color = Color.alphaBlend(tone.withValues(alpha: 0.12), base),
    );
    canvas.drawLine(
      Offset(0, floorY),
      Offset(w, floorY),
      Paint()
        ..color = ink.withValues(alpha: 0.10)
        ..strokeWidth = 1.5,
    );

    // 문
    final doorW = unit * 0.42;
    final doorLeft = w * 0.62 - doorW / 2;
    final door = RRect.fromRectAndCorners(
      Rect.fromLTWH(doorLeft, floorY - unit * 0.66, doorW, unit * 0.66),
      topLeft: Radius.circular(unit * 0.03),
      topRight: Radius.circular(unit * 0.03),
    );
    canvas.drawRRect(
      door,
      Paint()..color = Color.alphaBlend(ink.withValues(alpha: 0.04), base),
    );
    canvas.drawRRect(
      door,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = ink.withValues(alpha: 0.16),
    );
    canvas.drawCircle(
      Offset(doorLeft + doorW * 0.18, floorY - unit * 0.32),
      unit * 0.016,
      Paint()..color = ink.withValues(alpha: 0.28),
    );

    // 현관 기기 (문 옆 벽의 작은 초인종)
    final device = RRect.fromRectAndRadius(
      Rect.fromCenter(
        center: Offset(doorLeft + doorW + unit * 0.07, floorY - unit * 0.40),
        width: unit * 0.055,
        height: unit * 0.10,
      ),
      Radius.circular(unit * 0.02),
    );
    canvas.drawRRect(device, Paint()..color = ink.withValues(alpha: 0.55));
    canvas.drawCircle(
      device.center.translate(0, unit * 0.025),
      unit * 0.008,
      Paint()..color = tone,
    );

    final figure = Paint()..color = tone.withValues(alpha: isDark ? 0.75 : 0.62);
    final box = Paint()..color = tone.withValues(alpha: 0.90);
    final tape = Paint()..color = base.withValues(alpha: 0.55);

    void drawPerson(double cx) {
      final headR = unit * 0.075;
      final bodyTop = floorY - unit * 0.40;
      canvas.drawCircle(Offset(cx, bodyTop - headR * 1.25), headR, figure);
      canvas.drawRRect(
        RRect.fromRectAndCorners(
          Rect.fromLTWH(cx - unit * 0.12, bodyTop, unit * 0.24, unit * 0.40),
          topLeft: Radius.circular(unit * 0.11),
          topRight: Radius.circular(unit * 0.11),
        ),
        figure,
      );
    }

    void drawBox(double cx, double bottom, double s) {
      final r = Rect.fromLTWH(cx - s / 2, bottom - s * 0.72, s, s * 0.72);
      canvas.drawRRect(
        RRect.fromRectAndRadius(r, Radius.circular(s * 0.06)),
        box,
      );
      canvas.drawRect(
        Rect.fromLTWH(cx - s * 0.07, r.top, s * 0.14, r.height),
        tape,
      );
    }

    switch (scene) {
      case DoorScene.empty:
        break;
      case DoorScene.package:
        drawBox(doorLeft + doorW * 0.30, floorY, unit * 0.20);
      case DoorScene.person:
        drawPerson(w * 0.28);
      case DoorScene.personWithPackage:
        drawPerson(w * 0.26);
        drawBox(w * 0.26 + unit * 0.21, floorY, unit * 0.17);
    }
  }

  @override
  bool shouldRepaint(_DoorPainter old) =>
      old.scene != scene ||
      old.tone != tone ||
      old.base != base ||
      old.ink != ink ||
      old.isDark != isDark;
}

import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../data/category.dart';

/// 분류 표시. 색은 분류마다 하나, 바탕은 그 색을 옅게 깐다.
class CategoryBadge extends StatelessWidget {
  const CategoryBadge({
    super.key,
    required this.category,
    this.detail,
    this.onImage = false,
    this.dense = false,
  });

  final VisitCategory category;

  /// 세부 유형 (예: 음식 배달)
  final String? detail;

  /// 사진 위에 얹을 때는 어두운 반투명 바탕에 흰 글자
  final bool onImage;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final tone = p.tone(category);
    final fg = onImage ? Colors.white : tone;
    final bg = onImage
        ? Colors.black.withValues(alpha: 0.42)
        : tone.withValues(alpha: p.isDark ? 0.18 : 0.11);
    final label = detail == null || detail!.isEmpty
        ? category.label
        : '${category.label} · $detail';

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 8 : 10,
        vertical: dense ? 3 : 5,
      ),
      decoration: BoxDecoration(color: bg, borderRadius: Corner.pill),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(category.icon, size: dense ? 13 : 15, color: fg),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: fg,
                fontSize: dense ? 12 : 13,
                fontWeight: FontWeight.w600,
                height: 1.2,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 상태 꼬리표 (확인 필요, 긴급, 서버 장애 …)
class StatusTag extends StatelessWidget {
  const StatusTag({super.key, required this.label, required this.color, this.icon});

  final String label;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: Corner.pill,
        border: Border.all(color: color.withValues(alpha: 0.55)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 13, color: color),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              height: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

/// 숨 쉬듯 깜빡이는 점. 연결 상태처럼 "살아 있음"을 알릴 때만 쓴다.
class PulseDot extends StatefulWidget {
  const PulseDot({super.key, required this.color, this.animate = true, this.size = 8});

  final Color color;
  final bool animate;
  final double size;

  @override
  State<PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<PulseDot> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  );

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(PulseDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.animate != widget.animate) _sync();
  }

  void _sync() {
    // 접근성 설정에서 애니메이션을 끈 경우는 build에서 처리한다.
    if (widget.animate) {
      _c.repeat();
    } else {
      _c
        ..stop()
        ..value = 0;
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final s = widget.size;
    final dot = Container(
      width: s,
      height: s,
      decoration: BoxDecoration(color: widget.color, shape: BoxShape.circle),
    );
    if (!widget.animate || reduceMotion) {
      return SizedBox.square(dimension: s * 2.2, child: Center(child: dot));
    }
    return SizedBox.square(
      dimension: s * 2.2,
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, child) {
          final t = Curves.easeOut.transform(_c.value);
          return Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: s + s * 1.2 * t,
                height: s + s * 1.2 * t,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: widget.color.withValues(alpha: 0.35 * (1 - t)),
                ),
              ),
              child!,
            ],
          );
        },
        child: dot,
      ),
    );
  }
}

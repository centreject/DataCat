import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../core/theme.dart';
import '../../data/api.dart';
import '../../state/event_store.dart';
import 'badges.dart';

/// 섹션 제목. 오른쪽에 선택적으로 동작 버튼.
class SectionHeader extends StatelessWidget {
  const SectionHeader({super.key, required this.title, this.action, this.onAction});

  final String title;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.page, Gap.xxl, Gap.sm, Gap.xs),
      child: Row(
        children: [
          Expanded(
            child: Semantics(
              header: true,
              child: Text(title, style: context.text.titleLarge?.copyWith(fontSize: 19)),
            ),
          ),
          if (action != null)
            TextButton(onPressed: onAction, child: Text(action!)),
        ],
      ),
    );
  }
}

/// 서버 연결 상태를 한 줄로. 데모 / 동기화됨 / 연결 끊김.
class ConnectionPill extends StatelessWidget {
  const ConnectionPill({super.key, required this.store, this.onTap});

  final EventStore store;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final api = store.api;
    final (Color color, String text, bool alive) = switch (store) {
      _ when api.isDemo => (p.accent, '데모 모드', false),
      _ when store.error != null => (p.danger, '연결 끊김', false),
      _ when store.lastSync == null => (p.inkFaint, '연결 중', false),
      _ => (p.live, '${api.label} · ${KFormat.clock(store.lastSync!)}', true),
    };

    return Semantics(
      button: onTap != null,
      label: '서버 상태: $text',
      excludeSemantics: true,
      child: Material(
        color: p.card,
        shape: StadiumBorder(side: BorderSide(color: p.line)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(6, 6, 12, 6),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                PulseDot(color: color, animate: alive, size: 7),
                const SizedBox(width: 2),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 170),
                  child: Text(
                    text,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      color: p.inkSoft,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// 빈 화면 / 오류 화면 공용 틀
class MessageView extends StatelessWidget {
  const MessageView({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.tone,
  });

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final Color? tone;

  factory MessageView.error(ApiException error, {VoidCallback? onRetry, VoidCallback? onSettings}) {
    final offline = error.isOffline;
    return MessageView(
      icon: offline ? Icons.wifi_off_rounded : Icons.error_outline_rounded,
      title: offline ? '서버에 닿지 않아요' : '기록을 불러오지 못했어요',
      message: offline
          ? '${error.message}\n같은 네트워크에 있는지, 설정의 서버 주소가 맞는지 확인해 주세요.'
          : error.message,
      actionLabel: offline && onSettings != null ? '서버 주소 확인' : '다시 시도',
      onAction: offline && onSettings != null ? onSettings : onRetry,
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 48),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(color: p.sunken, shape: BoxShape.circle),
            child: Icon(icon, size: 28, color: tone ?? p.inkSoft),
          ),
          const SizedBox(height: Gap.xl),
          Text(title, style: context.text.titleLarge, textAlign: TextAlign.center),
          const SizedBox(height: Gap.sm),
          Text(message, style: context.text.bodyMedium, textAlign: TextAlign.center),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: Gap.xl),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    );
  }
}

/// 목록이 처음 뜨는 동안 보여줄 자리 표시. 실제 레이아웃과 같은 모양을 쓴다.
class SkeletonBlock extends StatefulWidget {
  const SkeletonBlock({super.key, this.width, this.height = 14, this.radius = Corner.small});

  final double? width;
  final double height;
  final BorderRadius radius;

  @override
  State<SkeletonBlock> createState() => _SkeletonBlockState();
}

class _SkeletonBlockState extends State<SkeletonBlock> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
    lowerBound: 0.45,
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _c,
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(color: context.palette.sunken, borderRadius: widget.radius),
      ),
    );
  }
}

class SkeletonTile extends StatelessWidget {
  const SkeletonTile({super.key});

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: Gap.page, vertical: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 48, child: SkeletonBlock(width: 36, height: 28)),
          SizedBox(width: Gap.sm),
          SkeletonBlock(width: 64, height: 64),
          SizedBox(width: Gap.md + 2),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SkeletonBlock(width: 84, height: 20, radius: Corner.pill),
                SizedBox(height: 10),
                SkeletonBlock(height: 16),
                SizedBox(height: 6),
                SkeletonBlock(width: 120, height: 16),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 이미 목록이 있는 상태에서 새로고침이 실패했을 때 위에 얹는 얇은 알림
class InlineNotice extends StatelessWidget {
  const InlineNotice({
    super.key,
    required this.icon,
    required this.text,
    required this.color,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String text;
  final Color color;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 6, 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: context.palette.isDark ? 0.14 : 0.08),
        borderRadius: Corner.medium,
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(fontSize: 13.5, color: context.palette.ink, height: 1.4),
            ),
          ),
          if (actionLabel != null)
            TextButton(onPressed: onAction, child: Text(actionLabel!)),
        ],
      ),
    );
  }
}

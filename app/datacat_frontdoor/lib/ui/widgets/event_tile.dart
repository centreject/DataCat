import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../core/theme.dart';
import '../../data/category.dart';
import '../../data/models.dart';
import '../../state/app_scope.dart';
import 'badges.dart';
import 'snapshot_view.dart';

/// 목록의 한 줄. 왼쪽에 시각, 가운데 스냅샷, 오른쪽에 분류와 요약.
class EventTile extends StatelessWidget {
  const EventTile({super.key, required this.event, required this.onTap});

  final VisitEvent event;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final t = event.occurredAt;
    final attention = event.needsAttention;
    final isNew = AppScope.of(context).store.isUnseen(event.eventId);

    return Semantics(
      button: true,
      label: '${isNew ? '새 방문, ' : ''}${KFormat.clock(t)}, ${event.category.label}, ${event.headline}'
          '${attention ? ', 확인 필요' : ''}',
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: Gap.page, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 48,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 2),
                    Text(
                      KFormat.meridiem(t),
                      style: TextStyle(fontSize: 11, color: p.inkFaint, height: 1.2),
                    ),
                    Text(
                      KFormat.hm(t),
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: p.ink,
                        height: 1.3,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                    if (isNew) ...[
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(color: p.accent, borderRadius: Corner.pill),
                        child: Text(
                          'NEW',
                          style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: p.card, letterSpacing: 0.4),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: Gap.sm),
              SizedBox.square(
                dimension: 64,
                child: SnapshotView(event: event, borderRadius: Corner.small),
              ),
              const SizedBox(width: Gap.md + 2),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: CategoryBadge(
                            category: event.category,
                            detail: event.subCategory,
                            dense: true,
                          ),
                        ),
                        if (attention) ...[
                          const SizedBox(width: 6),
                          Icon(
                            event.isUrgent ? Icons.priority_high_rounded : Icons.circle,
                            size: event.isUrgent ? 16 : 8,
                            color: event.isUrgent ? p.danger : p.attention,
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      event.headline,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.text.titleMedium,
                    ),
                    if (event.status == EventStatus.failed ||
                        event.visitorLeftSilently) ...[
                      const SizedBox(height: 2),
                      Text(
                        event.reason ?? event.processingStatus ?? '',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.text.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

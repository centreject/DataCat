import 'package:flutter/material.dart';

import '../../../../shared/design/app_dimensions.dart';

import '../../domain/door_event.dart';
import 'situation_badge.dart';

String formatEventTime(DateTime time) {
  final local = time.toLocal();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '${local.month}월 ${local.day}일 $hour:$minute';
}

class EventCard extends StatelessWidget {
  const EventCard({
    required this.event,
    required this.onTap,
    this.featured = false,
    super.key,
  });

  final DoorEvent event;
  final VoidCallback onTap;
  final bool featured;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
      ),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppDimensions.cardPadding,),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (featured) ...[
                AspectRatio(
                  aspectRatio: AppDimensions.photoAspectRatio,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: Theme.of(context)
                          .colorScheme
                          .surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(
                        AppDimensions.imageRadius,
                      ),
                    ),
                    child: const Center(
                      child: Icon(
                        Icons.image_outlined,
                        size: AppDimensions.minTouchSize,
                        semanticLabel: '방문 사진 준비 중',
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
              ],
              SituationBadge(situation: event.situation),
              const SizedBox(height: 12),
              Text(event.summary),
              const SizedBox(height: 8),
              Text(formatEventTime(event.occurredAt)),
              if (featured) ...[
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: onTap,
                    child: const Text('상세 보기'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

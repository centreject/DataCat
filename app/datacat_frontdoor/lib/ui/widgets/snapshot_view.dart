import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../data/category.dart';
import '../../data/models.dart';
import '../../state/app_scope.dart';
import 'door_illustration.dart';

/// 방문 기록의 스냅샷. 이미지가 없거나 불러오지 못하면 현관 그림을 보여준다.
class SnapshotView extends StatelessWidget {
  const SnapshotView({
    super.key,
    required this.event,
    this.borderRadius = BorderRadius.zero,
  });

  final VisitEvent event;
  final BorderRadius borderRadius;

  @override
  Widget build(BuildContext context) {
    final uri = AppScope.of(context).store.api.snapshotUri(event);
    final fallback = DoorIllustration(
      scene: event.scene,
      tone: context.palette.tone(event.category),
    );

    final Widget child = uri == null
        ? fallback
        : Image.network(
            uri.toString(),
            fit: BoxFit.cover,
            width: double.infinity,
            height: double.infinity,
            gaplessPlayback: true,
            errorBuilder: (_, _, _) => fallback,
            loadingBuilder: (context, image, progress) => progress == null
                ? image
                : Stack(
                    fit: StackFit.expand,
                    children: [
                      fallback,
                      const Center(
                        child: SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      ),
                    ],
                  ),
          );

    return ClipRRect(borderRadius: borderRadius, child: child);
  }
}

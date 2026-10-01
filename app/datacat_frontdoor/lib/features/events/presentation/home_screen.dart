import 'package:flutter/material.dart';

import '../../../shared/design/app_dimensions.dart';
import '../../../shared/design/responsive_content.dart';
import '../domain/door_event.dart';
import 'event_detail_screen.dart';
import 'widgets/event_card.dart';
import 'widgets/event_data_view.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({
    required this.events,
    required this.onRetry,
    super.key,
  });

  final Future<List<DoorEvent>> events;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return EventDataView(
      events: events,
      onRetry: onRetry,
      builder: (context, data) => ResponsiveContent(
        builder: (context, pagePadding) => ListView(
          padding: pagePadding,
          children: [
            Text(
              '문앞',
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: AppDimensions.spaceSmall),
            const Text('데모 모드 · 실제 기기 연결 전'),
            const SizedBox(height: AppDimensions.spaceSection),
            Text(
              '최근 상황',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 14),
            EventCard(
              event: data.first,
              featured: true,
              onTap: () => Navigator.of(context).push<void>(
                MaterialPageRoute(
                  builder: (_) => EventDetailScreen(
                    event: data.first,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
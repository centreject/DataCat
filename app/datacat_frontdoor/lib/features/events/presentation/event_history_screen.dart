import 'package:flutter/material.dart';

import '../../../shared/design/app_dimensions.dart';
import '../../../shared/design/responsive_content.dart';
import '../domain/door_event.dart';
import 'event_detail_screen.dart';
import 'widgets/event_card.dart';
import 'widgets/event_data_view.dart';

class EventHistoryScreen extends StatelessWidget {
  const EventHistoryScreen({
    required this.events,
    required this.onRetry,
    super.key,
  });

  final Future<List<DoorEvent>> events;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ResponsiveContent(
      builder: (context, pagePadding) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: pagePadding,
            child: Text(
              '상황 기록',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ),
          Expanded(
            child: EventDataView(
              events: events,
              onRetry: onRetry,
              builder: (context, data) => ListView.separated(
                padding: EdgeInsets.fromLTRB(
                  pagePadding.left,
                  0,
                  pagePadding.right,
                  pagePadding.bottom,
                ),
                itemCount: data.length,
                separatorBuilder: (_, _) => const SizedBox(
                  height: AppDimensions.spaceSmall,
                ),
                itemBuilder: (context, index) {
                  final event = data[index];

                  return EventCard(
                    event: event,
                    onTap: () => Navigator.of(context).push<void>(
                      MaterialPageRoute(
                        builder: (_) => EventDetailScreen(
                          event: event,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
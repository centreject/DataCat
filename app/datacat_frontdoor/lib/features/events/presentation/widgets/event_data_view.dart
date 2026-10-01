import 'package:flutter/material.dart';

import '../../domain/door_event.dart';

class EventDataView extends StatelessWidget {
  const EventDataView({
    required this.events,
    required this.onRetry,
    required this.builder,
    super.key,
  });

  final Future<List<DoorEvent>> events;
  final VoidCallback onRetry;
  final Widget Function(BuildContext, List<DoorEvent>) builder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<DoorEvent>>(
      future: events,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('상황 기록을 불러오지 못했어요.'),
                const SizedBox(height: 12),
                FilledButton(onPressed: onRetry, child: const Text('다시 시도')),
              ],
            ),
          );
        }
        final data = snapshot.data ?? const <DoorEvent>[];
        if (data.isEmpty) {
          return const Center(child: Text('아직 방문 기록이 없어요.'));
        }
        return builder(context, data);
      },
    );
  }
}

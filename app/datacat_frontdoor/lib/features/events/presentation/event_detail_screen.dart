import 'package:flutter/material.dart';

import '../../../shared/design/app_dimensions.dart';
import '../../../shared/design/responsive_content.dart';

import '../domain/door_event.dart';
import 'widgets/event_card.dart';
import 'widgets/situation_badge.dart';

class EventDetailScreen extends StatelessWidget {
  const EventDetailScreen({required this.event, super.key});

  final DoorEvent event;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('상황 상세')),
      body: SafeArea(
        child: ResponsiveContent(
          builder: (context, pagePadding) => ListView(
            padding: pagePadding,
            children: [
                SituationBadge(situation: event.situation),
                const SizedBox(height: AppDimensions.spaceMedium),
                Text(formatEventTime(event.occurredAt)),
                const SizedBox(height: AppDimensions.spaceSection),
                Text('방문 내용', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                Text(event.transcript ?? '전사된 음성 내용이 없습니다.'),
                const SizedBox(height: AppDimensions.spaceSection),
                Text('요약', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                Text(event.summary),
                const SizedBox(height: AppDimensions.spaceSection),
                const Text('데모 데이터 · 실제 방문 기록이 아닙니다.'),
            ],
          ),
        ),
      ),
    );
  }
}

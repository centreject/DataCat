import 'package:flutter/material.dart';

import '../features/events/domain/event_repository.dart';
import 'app_shell.dart';
import 'app_theme.dart';

class MunapApp extends StatelessWidget {
  const MunapApp({required this.eventRepository, super.key});

  final EventRepository eventRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '문앞',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: AppShell(eventRepository: eventRepository),
    );
  }
}

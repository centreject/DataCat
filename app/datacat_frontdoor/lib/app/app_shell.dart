import 'package:flutter/material.dart';

import '../shared/design/app_dimensions.dart';

import '../features/events/domain/door_event.dart';
import '../features/events/domain/event_repository.dart';
import '../features/events/presentation/event_history_screen.dart';
import '../features/events/presentation/home_screen.dart';
import '../features/settings/presentation/settings_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({required this.eventRepository, super.key});

  final EventRepository eventRepository;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;
  late Future<List<DoorEvent>> _events;

  @override
  void initState() {
    super.initState();
    _events = widget.eventRepository.fetchEvents();
  }

  void _reload() {
    setState(() {
      _events = widget.eventRepository.fetchEvents();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: AppDimensions.contentMaxWidth,
            ),
            child: IndexedStack(
              index: _selectedIndex,
              children: [
                HomeScreen(events: _events, onRetry: _reload),
                EventHistoryScreen(events: _events, onRetry: _reload),
                const SettingsScreen(),
              ],
            ),
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() => _selectedIndex = index);
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: '홈'),
          NavigationDestination(icon: Icon(Icons.history), label: '기록'),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            label: '설정',
          ),
        ],
      ),
    );
  }
}

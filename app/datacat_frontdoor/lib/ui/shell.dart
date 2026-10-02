import 'package:flutter/material.dart';

import '../core/theme.dart';
import 'history_screen.dart';
import 'home_screen.dart';
import 'settings_screen.dart';

/// 아래 탭 세 개: 홈 / 기록 / 설정. 탭을 옮겨도 스크롤 위치가 유지된다.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;

  void _go(int i) => setState(() => _index = i);

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          HomeScreen(onOpenHistory: () => _go(1), onOpenSettings: () => _go(2)),
          HistoryScreen(onOpenSettings: () => _go(2)),
          const SettingsScreen(),
        ],
      ),
      bottomNavigationBar: DecoratedBox(
        decoration: BoxDecoration(border: Border(top: BorderSide(color: p.line))),
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: _go,
          labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.door_front_door_outlined),
              selectedIcon: Icon(Icons.door_front_door),
              label: '홈',
            ),
            NavigationDestination(
              icon: Icon(Icons.view_agenda_outlined),
              selectedIcon: Icon(Icons.view_agenda),
              label: '기록',
            ),
            NavigationDestination(
              icon: Icon(Icons.tune_rounded),
              selectedIcon: Icon(Icons.tune_rounded),
              label: '설정',
            ),
          ],
        ),
      ),
    );
  }
}

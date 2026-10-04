import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/format.dart';
import '../core/theme.dart';
import '../data/category.dart';
import '../data/models.dart';
import '../state/app_scope.dart';
import 'event_detail_screen.dart';
import 'history_screen.dart';
import 'home_screen.dart';
import 'settings_screen.dart';

/// 아래 탭 세 개: 홈 / 기록 / 설정. 탭을 옮겨도 스크롤 위치가 유지된다.
/// 자동 새로고침으로 새 방문이 들어오면 화면 위에 알림 띠를 띄운다.
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      // 상태 표시줄 아이콘 색도 테마에 맞춘다 (모바일)
      value: isDark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
      child: Scaffold(
        body: Stack(
          children: [
            IndexedStack(
              index: _index,
              children: [
                HomeScreen(onOpenHistory: () => _go(1), onOpenSettings: () => _go(2)),
                HistoryScreen(onOpenSettings: () => _go(2)),
                const SettingsScreen(),
              ],
            ),
            const Positioned(left: 0, right: 0, top: 0, child: _ArrivalBanner()),
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
      ),
    );
  }
}

/// "새 방문" 알림 띠. 정책에서 알림을 끈 분류는 띄우지 않는다.
class _ArrivalBanner extends StatelessWidget {
  const _ArrivalBanner();

  @override
  Widget build(BuildContext context) {
    final scope = AppScope.of(context);
    final store = scope.store;

    return ListenableBuilder(
      listenable: Listenable.merge([store, scope.policy]),
      builder: (context, _) {
        final alerts = store.unseenAlerts;
        final visible = alerts.isNotEmpty;
        return IgnorePointer(
          ignoring: !visible,
          child: AnimatedSlide(
            offset: visible ? Offset.zero : const Offset(0, -1.2),
            duration: const Duration(milliseconds: 380),
            curve: visible ? Curves.easeOutBack : Curves.easeInCubic,
            child: AnimatedOpacity(
              opacity: visible ? 1 : 0,
              duration: const Duration(milliseconds: 240),
              child: SafeArea(
                bottom: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(Gap.lg, Gap.sm, Gap.lg, 0),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 520),
                      child: visible ? _BannerCard(alerts: alerts) : const SizedBox(height: 56),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _BannerCard extends StatelessWidget {
  const _BannerCard({required this.alerts});

  final List<VisitEvent> alerts;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final store = AppScope.of(context).store;
    final latest = alerts.first;
    final urgent = alerts.any((e) => e.isUrgent || e.category == VisitCategory.safety);
    final accent = urgent ? p.danger : p.tone(latest.category);
    final title = alerts.length == 1 ? '새 방문 · ${latest.category.label}' : '새 방문 ${alerts.length}건';

    void open() {
      store.markAllSeen();
      Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => EventDetailScreen(initial: latest)),
      );
    }

    return Semantics(
      liveRegion: true,
      label: '$title, ${latest.headline}',
      child: Material(
        color: p.card,
        elevation: 6,
        shadowColor: Colors.black.withValues(alpha: 0.25),
        shape: RoundedRectangleBorder(borderRadius: Corner.medium, side: BorderSide(color: p.line)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: open,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(Gap.md, 10, 4, 10),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: p.isDark ? 0.22 : 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(urgent ? Icons.priority_high_rounded : latest.category.icon, size: 19, color: accent),
                ),
                const SizedBox(width: Gap.md),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '$title  ·  ${KFormat.relative(latest.occurredAt)}',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: accent),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        latest.headline,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: p.ink),
                      ),
                    ],
                  ),
                ),
                TextButton(onPressed: open, child: const Text('보기')),
                IconButton(
                  tooltip: '닫기',
                  onPressed: store.markAllSeen,
                  icon: Icon(Icons.close_rounded, size: 20, color: p.inkFaint),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

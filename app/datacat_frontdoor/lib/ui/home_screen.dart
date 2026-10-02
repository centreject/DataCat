import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/theme.dart';
import '../data/category.dart';
import '../data/models.dart';
import '../state/app_scope.dart';
import 'event_detail_screen.dart';
import 'widgets/badges.dart';
import 'widgets/common.dart';
import 'widgets/event_tile.dart';
import 'widgets/snapshot_view.dart';

/// 첫 화면: 가장 최근 방문 한 건을 크게, 오늘 요약, 확인할 것, 최근 기록.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.onOpenHistory, required this.onOpenSettings});

  final VoidCallback onOpenHistory;
  final VoidCallback onOpenSettings;

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context).store;

    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final events = store.events;
        final slivers = <Widget>[
          SliverSafeArea(
            bottom: false,
            sliver: SliverToBoxAdapter(
              child: _Header(trailing: ConnectionPill(store: store, onTap: onOpenSettings)),
            ),
          ),
        ];

        if (store.isFirstLoad) {
          slivers.add(const SliverToBoxAdapter(child: _HomeSkeleton()));
        } else if (events.isEmpty && store.error != null) {
          slivers.add(SliverFillRemaining(
            hasScrollBody: false,
            child: Center(
              child: MessageView.error(
                store.error!,
                onRetry: store.refresh,
                onSettings: onOpenSettings,
              ),
            ),
          ));
        } else if (events.isEmpty) {
          slivers.add(const SliverFillRemaining(
            hasScrollBody: false,
            child: Center(
              child: MessageView(
                icon: Icons.door_front_door_outlined,
                title: '아직 방문 기록이 없어요',
                message: '현관 기기가 방문을 감지하면\n이곳에 가장 먼저 나타나요.',
              ),
            ),
          ));
        } else {
          slivers.addAll(_content(context, events, store.error != null, store.refresh));
        }

        slivers.add(const SliverToBoxAdapter(child: SizedBox(height: Gap.xxl)));

        return RefreshIndicator(
          onRefresh: store.refresh,
          color: context.palette.ink,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: slivers,
          ),
        );
      },
    );
  }

  List<Widget> _content(
    BuildContext context,
    List<VisitEvent> events,
    bool syncFailed,
    Future<void> Function() retry,
  ) {
    final p = context.palette;
    final latest = events.first;
    final attention = events.where((e) => e.needsAttention && e != latest).take(3).toList();
    final recent = events.skip(1).where((e) => !attention.contains(e)).take(5).toList();

    return [
      if (syncFailed)
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(Gap.page, 0, Gap.page, Gap.md),
          sliver: SliverToBoxAdapter(
            child: InlineNotice(
              icon: Icons.cloud_off_rounded,
              text: '최신 기록을 받아오지 못했어요. 마지막으로 받은 기록을 보여드려요.',
              color: p.danger,
              actionLabel: '재시도',
              onAction: retry,
            ),
          ),
        ),
      SliverPadding(
        padding: const EdgeInsets.symmetric(horizontal: Gap.page),
        sliver: SliverToBoxAdapter(
          child: _LatestVisitCard(event: latest, onTap: () => _open(context, latest)),
        ),
      ),
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(Gap.page, Gap.md, Gap.page, 0),
        sliver: SliverToBoxAdapter(child: _TodayStrip(events: events)),
      ),
      if (attention.isNotEmpty) ...[
        const SliverToBoxAdapter(child: SectionHeader(title: '확인이 필요해요')),
        SliverList.list(
          children: [
            for (final e in attention) EventTile(event: e, onTap: () => _open(context, e)),
          ],
        ),
      ],
      if (recent.isNotEmpty) ...[
        SliverToBoxAdapter(
          child: SectionHeader(title: '최근 기록', action: '전체 보기', onAction: onOpenHistory),
        ),
        SliverList.list(
          children: [
            for (final e in recent) EventTile(event: e, onTap: () => _open(context, e)),
          ],
        ),
      ],
    ];
  }

  static void _open(BuildContext context, VisitEvent e) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => EventDetailScreen(initial: e)),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.trailing});

  final Widget trailing;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.page, Gap.lg, Gap.page, Gap.xl),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  KFormat.fullDate(now),
                  style: context.text.labelLarge?.copyWith(color: context.palette.inkSoft),
                ),
                const SizedBox(height: 2),
                Semantics(
                  header: true,
                  child: Text('우리집 현관', style: context.text.headlineMedium),
                ),
              ],
            ),
          ),
          Padding(padding: const EdgeInsets.only(top: 4), child: trailing),
        ],
      ),
    );
  }
}

/// 가장 최근 방문. 스냅샷을 크게 깔고 아래쪽에 요약을 얹는다.
class _LatestVisitCard extends StatelessWidget {
  const _LatestVisitCard({required this.event, required this.onTap});

  final VisitEvent event;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Semantics(
      button: true,
      label: '가장 최근 방문, ${KFormat.relative(event.occurredAt)}, '
          '${event.category.label}, ${event.headline}',
      excludeSemantics: true,
      child: Material(
        color: p.sunken,
        borderRadius: Corner.large,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: AspectRatio(
            aspectRatio: 4 / 3.4,
            child: Stack(
              fit: StackFit.expand,
              children: [
                SnapshotView(event: event),
                const DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      stops: [0.35, 1],
                      colors: [Color(0x00000000), Color(0xB3000000)],
                    ),
                  ),
                ),
                Positioned(
                  left: Gap.lg,
                  top: Gap.lg,
                  child: _Overline(
                    text: event.status == EventStatus.waitingAudio ? '지금 응대 중' : '가장 최근 방문',
                    live: event.status == EventStatus.waitingAudio,
                  ),
                ),
                Positioned(
                  left: Gap.xl,
                  right: Gap.xl,
                  bottom: Gap.xl,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: CategoryBadge(
                              category: event.category,
                              detail: event.subCategory,
                              onImage: true,
                            ),
                          ),
                          const SizedBox(width: Gap.sm),
                          Text(
                            KFormat.relative(event.occurredAt),
                            style: const TextStyle(
                              color: Color(0xCCFFFFFF),
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        event.headline,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: context.text.headlineSmall?.copyWith(color: Colors.white),
                      ),
                      if (event.hasTranscript) ...[
                        const SizedBox(height: 6),
                        Text(
                          '“${event.transcript!.trim()}”',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Color(0xB3FFFFFF), fontSize: 14),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Overline extends StatelessWidget {
  const _Overline({required this.text, this.live = false});

  final String text;
  final bool live;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(6, 4, 10, 4),
      decoration: const BoxDecoration(
        color: Color(0x66000000),
        borderRadius: Corner.pill,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          PulseDot(color: live ? const Color(0xFFFF6B5B) : Colors.white, animate: live, size: 6),
          Text(
            text,
            style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

/// 오늘 몇 번, 어떤 방문이 있었는지 세 칸으로.
class _TodayStrip extends StatelessWidget {
  const _TodayStrip({required this.events});

  final List<VisitEvent> events;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final now = DateTime.now();
    final today = events.where((e) => KFormat.isSameDay(e.occurredAt, now)).toList();
    final deliveries = today.where((e) => e.category.isDeliveryLike).length;
    final visitors = today.length - deliveries;
    final attention = today.where((e) => e.needsAttention).length;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: Gap.lg),
      decoration: BoxDecoration(
        color: p.card,
        borderRadius: Corner.medium,
        border: Border.all(color: p.line),
      ),
      child: Row(
        children: [
          _Stat(value: today.length, label: '오늘 전체'),
          _divider(p),
          _Stat(value: deliveries, label: '배송·물품'),
          _divider(p),
          _Stat(value: visitors, label: '방문'),
          _divider(p),
          _Stat(
            value: attention,
            label: '확인 필요',
            color: attention > 0 ? p.attention : null,
          ),
        ],
      ),
    );
  }

  Widget _divider(Palette p) => Container(width: 1, height: 28, color: p.line);
}

class _Stat extends StatelessWidget {
  const _Stat({required this.value, required this.label, this.color});

  final int value;
  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Expanded(
      child: Semantics(
        label: '$label $value건',
        excludeSemantics: true,
        child: Column(
          children: [
            Text(
              '$value',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: color ?? (value == 0 ? p.inkFaint : p.ink),
                height: 1.1,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
            const SizedBox(height: 4),
            Text(label, style: TextStyle(fontSize: 12, color: p.inkSoft)),
          ],
        ),
      ),
    );
  }
}

class _HomeSkeleton extends StatelessWidget {
  const _HomeSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        Padding(
          padding: EdgeInsets.symmetric(horizontal: Gap.page),
          child: AspectRatio(
            aspectRatio: 4 / 3.4,
            child: SkeletonBlock(radius: Corner.large),
          ),
        ),
        SizedBox(height: Gap.md),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: Gap.page),
          child: SkeletonBlock(height: 76, radius: Corner.medium),
        ),
        SizedBox(height: Gap.xl),
        SkeletonTile(),
        SkeletonTile(),
      ],
    );
  }
}

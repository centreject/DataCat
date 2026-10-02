import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/theme.dart';
import '../data/category.dart';
import '../data/models.dart';
import '../state/app_scope.dart';
import '../state/event_store.dart';
import 'event_detail_screen.dart';
import 'widgets/common.dart';
import 'widgets/event_tile.dart';

enum HistoryFilter {
  all('전체'),
  deliveries('배송·물품'),
  visitors('방문'),
  attention('확인 필요');

  const HistoryFilter(this.label);
  final String label;

  bool matches(VisitEvent e) => switch (this) {
        HistoryFilter.all => true,
        HistoryFilter.deliveries => e.category.isDeliveryLike,
        HistoryFilter.visitors => !e.category.isDeliveryLike,
        HistoryFilter.attention => e.needsAttention,
      };
}

/// 날짜별로 묶은 전체 방문 기록. 끝에 닿으면 다음 페이지를 불러온다.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.onOpenSettings});

  final VoidCallback onOpenSettings;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final _scroll = ScrollController();
  HistoryFilter _filter = HistoryFilter.all;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_maybeLoadMore);
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _maybeLoadMore() {
    if (!_scroll.hasClients) return;
    final store = AppScope.of(context).store;
    // 실패했을 때는 사용자가 '다시 시도'를 누를 때까지 자동으로 재요청하지 않는다.
    if (store.moreError != null) return;
    final pos = _scroll.position;
    if (pos.pixels > pos.maxScrollExtent - 480) {
      store.loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppScope.of(context).store;
    final p = context.palette;

    return ListenableBuilder(
      listenable: store,
      builder: (context, _) {
        final all = store.events;
        final shown = all.where(_filter.matches).toList();

        // 필터를 걸어 화면이 짧아지면 스크롤이 안 생겨 다음 페이지를 못 부른다.
        // 그릴 때마다 한 번 확인해 준다.
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _maybeLoadMore();
        });

        final items = <Object>[]; // DateTime(날짜 머리) 또는 VisitEvent
        DateTime? day;
        for (final e in shown) {
          final d = KFormat.dayOf(e.occurredAt);
          if (day != d) {
            items.add(d);
            day = d;
          }
          items.add(e);
        }

        return RefreshIndicator(
          onRefresh: store.refresh,
          color: p.ink,
          child: CustomScrollView(
            controller: _scroll,
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverAppBar(
                pinned: true,
                backgroundColor: p.paper,
                surfaceTintColor: Colors.transparent,
                scrolledUnderElevation: 0,
                toolbarHeight: 64,
                titleSpacing: Gap.page,
                title: Text('방문 기록', style: context.text.headlineSmall),
                bottom: PreferredSize(
                  preferredSize: const Size.fromHeight(56),
                  child: _FilterBar(
                    selected: _filter,
                    counts: {
                      for (final f in HistoryFilter.values) f: all.where(f.matches).length,
                    },
                    onSelect: (f) => setState(() => _filter = f),
                  ),
                ),
              ),
              if (store.isFirstLoad)
                SliverList.list(children: const [
                  SkeletonTile(),
                  SkeletonTile(),
                  SkeletonTile(),
                  SkeletonTile(),
                ])
              else if (all.isEmpty && store.error != null)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: MessageView.error(
                      store.error!,
                      onRetry: store.refresh,
                      onSettings: widget.onOpenSettings,
                    ),
                  ),
                )
              else if (shown.isEmpty)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: MessageView(
                      icon: Icons.inbox_outlined,
                      title: all.isEmpty ? '아직 방문 기록이 없어요' : '해당하는 기록이 없어요',
                      message: all.isEmpty
                          ? '현관 기기가 방문을 감지하면 이곳에 쌓여요.'
                          : '불러온 기록 중에는 "${_filter.label}"에 맞는 방문이 없어요.',
                    ),
                  ),
                )
              else
                SliverList.builder(
                  itemCount: items.length,
                  itemBuilder: (context, i) {
                    final item = items[i];
                    if (item is DateTime) return _DayHeader(day: item);
                    final e = item as VisitEvent;
                    return EventTile(
                      event: e,
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => EventDetailScreen(initial: e)),
                      ),
                    );
                  },
                ),
              if (all.isNotEmpty) SliverToBoxAdapter(child: _ListFooter(store: store)),
            ],
          ),
        );
      },
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({required this.selected, required this.counts, required this.onSelect});

  final HistoryFilter selected;
  final Map<HistoryFilter, int> counts;
  final ValueChanged<HistoryFilter> onSelect;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(Gap.page, 6, Gap.page, 14),
        itemCount: HistoryFilter.values.length,
        separatorBuilder: (_, _) => const SizedBox(width: Gap.sm),
        itemBuilder: (context, i) {
          final f = HistoryFilter.values[i];
          return _FilterPill(
            label: f.label,
            count: counts[f] ?? 0,
            selected: f == selected,
            highlight: f == HistoryFilter.attention && (counts[f] ?? 0) > 0,
            onTap: () => onSelect(f),
          );
        },
      ),
    );
  }
}

class _FilterPill extends StatelessWidget {
  const _FilterPill({
    required this.label,
    required this.count,
    required this.selected,
    required this.highlight,
    required this.onTap,
  });

  final String label;
  final int count;
  final bool selected;
  final bool highlight;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final fg = selected ? p.paper : p.ink;
    return Semantics(
      selected: selected,
      button: true,
      label: '$label $count건',
      excludeSemantics: true,
      child: Material(
        color: selected ? p.ink : p.card,
        shape: StadiumBorder(side: BorderSide(color: selected ? p.ink : p.line)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label, style: TextStyle(color: fg, fontWeight: FontWeight.w600, fontSize: 14)),
                const SizedBox(width: 6),
                Text(
                  '$count',
                  style: TextStyle(
                    color: highlight && !selected ? p.attention : fg.withValues(alpha: 0.6),
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
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

class _DayHeader extends StatelessWidget {
  const _DayHeader({required this.day});

  final DateTime day;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.page, Gap.xl, Gap.page, Gap.xs),
      child: Semantics(
        header: true,
        child: Row(
          children: [
            Text(
              KFormat.dayLabel(day),
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: p.ink),
            ),
            const SizedBox(width: Gap.md),
            Expanded(child: Container(height: 1, color: p.line)),
          ],
        ),
      ),
    );
  }
}

class _ListFooter extends StatelessWidget {
  const _ListFooter({required this.store});

  final EventStore store;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final s = store;
    final Widget child;
    if (s.loadingMore) {
      child = const SizedBox.square(
        dimension: 20,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    } else if (s.moreError != null) {
      child = TextButton.icon(
        onPressed: s.loadMore,
        icon: const Icon(Icons.refresh_rounded, size: 18),
        label: const Text('이어서 불러오기 실패 · 다시 시도'),
      );
    } else if (!s.hasMore) {
      child = Text('모든 기록을 불러왔어요', style: TextStyle(fontSize: 13, color: p.inkFaint));
    } else {
      child = const SizedBox(height: 20);
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: Gap.xxl),
      child: Center(child: child),
    );
  }
}

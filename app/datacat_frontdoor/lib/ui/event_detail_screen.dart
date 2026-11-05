import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/theme.dart';
import '../data/api.dart';
import '../data/category.dart';
import '../data/models.dart';
import '../state/app_scope.dart';
import 'widgets/badges.dart';
import 'widgets/snapshot_view.dart';
import 'widgets/theme_toggle.dart';

/// 방문 한 건의 전체 기록.
///
/// 목록에서 받은 내용으로 먼저 그리고, 상세 API(9.2)로 전사문 등을 채운다.
class EventDetailScreen extends StatefulWidget {
  const EventDetailScreen({super.key, required this.initial});

  final VisitEvent initial;

  @override
  State<EventDetailScreen> createState() => _EventDetailScreenState();
}

class _EventDetailScreenState extends State<EventDetailScreen> {
  late VisitEvent _event = widget.initial;
  bool _loading = false;
  ApiException? _error;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      // 열어 본 방문은 "새 방문" 표시를 지운다 (다음 프레임에 — 빌드 중 알림 방지)
      final store = AppScope.of(context).store;
      WidgetsBinding.instance.addPostFrameCallback((_) => store.markSeen(widget.initial.eventId));
      _loading = true; // 첫 빌드 전이라 setState 없이 표시만 켠다
      _load(initial: true);
    }
  }

  Future<void> _load({bool initial = false}) async {
    final store = AppScope.of(context).store;
    if (!initial) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final fresh = await store.api.fetchEvent(_event.eventId);
      if (!mounted) return;
      setState(() => _event = fresh);
      store.upsert(fresh);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final e = _event;
    final width = MediaQuery.sizeOf(context).width;

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _load,
        color: p.ink,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverAppBar(
              pinned: true,
              stretch: true,
              expandedHeight: (width * 0.82).clamp(260.0, 460.0),
              backgroundColor: p.paper,
              surfaceTintColor: Colors.transparent,
              automaticallyImplyLeading: false,
              leading: Padding(
                padding: const EdgeInsets.all(8),
                child: _RoundButton(
                  icon: Icons.arrow_back_rounded,
                  tooltip: '뒤로',
                  onTap: () => Navigator.of(context).maybePop(),
                ),
              ),
              actions: const [
                Padding(padding: EdgeInsets.only(right: 8), child: ThemeToggle(size: 40)),
              ],
              flexibleSpace: FlexibleSpaceBar(
                stretchModes: const [StretchMode.zoomBackground],
                background: SnapshotView(event: e),
              ),
            ),
            SliverToBoxAdapter(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                child: _loading
                    ? const LinearProgressIndicator(minHeight: 2)
                    : const SizedBox(height: 2),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(Gap.page, Gap.xl, Gap.page, 48),
              sliver: SliverList.list(
                children: [
                  _TitleBlock(event: e),
                  if (_error != null) ...[
                    const SizedBox(height: Gap.lg),
                    _Notice(
                      icon: Icons.cloud_off_rounded,
                      color: p.danger,
                      title: '최신 내용을 받아오지 못했어요',
                      body: _error!.message,
                    ),
                  ],
                  if (e.needsAttention) ...[
                    const SizedBox(height: Gap.lg),
                    _attentionNotice(e, p),
                  ],
                  const _Heading('방문객이 남긴 말'),
                  _TranscriptBlock(event: e),
                  const _Heading('어떻게 처리됐나요'),
                  _ProcessTimeline(event: e),
                  if ((e.reason ?? '').isNotEmpty && !e.needsAttention) ...[
                    const _Heading('판정 근거'),
                    Text(e.reason!, style: context.text.bodyLarge),
                  ],
                  const SizedBox(height: Gap.xxl),
                  const _PrivacyNote(),
                  const SizedBox(height: Gap.md),
                  _TechnicalInfo(event: e),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _attentionNotice(VisitEvent e, Palette p) {
    if (e.status == EventStatus.failed) {
      return _Notice(
        icon: Icons.report_gmailerrorred_rounded,
        color: p.danger,
        title: '처리 중 문제가 있었어요',
        body: e.reason ?? '현관 기기가 오류 안내를 한 번 하고 세션을 닫았어요. 이 방문의 용건은 기록되지 않았어요.',
      );
    }
    if (e.isUrgent) {
      return _Notice(
        icon: Icons.emergency_rounded,
        color: p.danger,
        title: '긴급으로 분류된 방문이에요',
        body: '${e.reason ?? '방문객이 긴급 상황을 언급했어요.'}\n'
            '현관문은 자동으로 열리지 않아요. 스냅샷과 기록을 직접 확인해 주세요.',
      );
    }
    return _Notice(
      icon: Icons.visibility_outlined,
      color: p.attention,
      title: '직접 확인해 주세요',
      body: e.reason ?? '자동 분류가 확실하지 않아요. 스냅샷과 남긴 말을 함께 확인해 주세요.',
    );
  }
}

class _TitleBlock extends StatelessWidget {
  const _TitleBlock({required this.event});

  final VisitEvent event;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final e = event;
    final meta = [
      '${KFormat.dayLabel(e.occurredAt)} ${KFormat.clock(e.occurredAt)}',
      e.trigger.label,
      if (e.stay != null && e.stay!.inSeconds > 0) '${KFormat.duration(e.stay!)} 머묾',
    ].join('  ·  ');

    final processing = e.processingStatus;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: Gap.sm,
          runSpacing: Gap.sm,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            CategoryBadge(category: e.category, detail: e.subCategory),
            if (e.isUrgent) StatusTag(label: '긴급', color: p.danger, icon: Icons.priority_high_rounded),
            if (e.needsReview) StatusTag(label: '확인 필요', color: p.attention),
            if (processing != null && processing != '정상')
              StatusTag(label: processing, color: p.inkSoft),
          ],
        ),
        const SizedBox(height: Gap.md),
        Semantics(
          header: true,
          child: Text(e.headline, style: context.text.headlineMedium),
        ),
        const SizedBox(height: Gap.sm),
        Text(meta, style: context.text.bodyMedium),
      ],
    );
  }
}

class _Heading extends StatelessWidget {
  const _Heading(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: Gap.xxl, bottom: Gap.md),
      child: Semantics(
        header: true,
        child: Text(
          text,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
            color: context.palette.inkSoft,
          ),
        ),
      ),
    );
  }
}

class _TranscriptBlock extends StatelessWidget {
  const _TranscriptBlock({required this.event});

  final VisitEvent event;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final e = event;

    if (!e.hasTranscript) {
      final why = switch (e) {
        _ when e.status == EventStatus.waitingAudio => '방문객이 말하기를 기다리는 중이에요.',
        _ when e.status == EventStatus.failed => '오류로 녹음 단계까지 가지 못했어요.',
        _ when e.category == VisitCategory.packageOnly =>
          '사람이 보이지 않아 안내 음성 없이 조용히 기록만 남겼어요.',
        _ when e.visitorLeftSilently => '안내 음성이 나간 뒤 아무 말 없이 떠났어요.',
        _ => '녹음된 말이 없어요.',
      };
      return Text(why, style: context.text.bodyLarge?.copyWith(color: p.inkSoft));
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(Gap.lg, Gap.lg, Gap.lg, Gap.lg),
      decoration: BoxDecoration(
        color: p.card,
        borderRadius: Corner.medium,
        border: Border(left: BorderSide(color: p.tone(e.category), width: 3)),
      ),
      child: SelectableText(
        '“${e.transcript!.trim()}”',
        style: context.text.bodyLarge?.copyWith(fontSize: 17),
      ),
    );
  }
}

/// 감지 → 판단 → 응대 → 종료. 서버 필드에서 확인되는 단계만 그린다.
class _ProcessTimeline extends StatelessWidget {
  const _ProcessTimeline({required this.event});

  final VisitEvent event;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final e = event;
    final steps = <_Step>[
      _Step(
        e.trigger == TriggerType.button ? '호출벨이 눌렸어요' : '현관 앞에서 움직임을 감지했어요',
        KFormat.clock(e.occurredAt),
      ),
    ];

    if (e.status == EventStatus.failed) {
      steps.add(_Step('서버가 응답하지 않아 오류 안내 후 종료했어요', null, color: p.danger));
    } else {
      switch (e.scene) {
        case DoorScene.package:
          steps.add(const _Step('사람 없이 물품만 확인 — 소리 없이 기록했어요', null));
        case DoorScene.empty:
          steps.add(const _Step('사람을 확인하고 안내 음성을 내보냈어요', null));
          steps.add(const _Step('말하기 전에 자리를 떠났어요', null));
        case DoorScene.person:
        case DoorScene.personWithPackage:
          steps.add(const _Step('사람을 확인하고 안내 음성을 내보냈어요', null));
          if (e.hasTranscript) {
            steps.add(const _Step('말씀을 받아 적고 용건을 정리했어요', null));
          } else if (e.status == EventStatus.waitingAudio) {
            steps.add(_Step('말씀을 기다리는 중', null, color: p.live));
          }
      }
    }

    if (e.endedAt != null) {
      steps.add(_Step('응대를 마쳤어요', KFormat.clock(e.endedAt!)));
    }

    return Column(
      children: [
        for (var i = 0; i < steps.length; i++)
          _TimelineRow(step: steps[i], isFirst: i == 0, isLast: i == steps.length - 1),
      ],
    );
  }
}

class _Step {
  const _Step(this.text, this.time, {this.color});

  final String text;
  final String? time;
  final Color? color;
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.step, required this.isFirst, required this.isLast});

  final _Step step;
  final bool isFirst;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final dotColor = step.color ?? p.ink;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 20,
            child: Column(
              children: [
                Container(width: 1.5, height: 7, color: isFirst ? Colors.transparent : p.line),
                Container(
                  width: 9,
                  height: 9,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isLast || isFirst ? dotColor : p.card,
                    border: Border.all(color: dotColor, width: 1.5),
                  ),
                ),
                Expanded(
                  child: Container(width: 1.5, color: isLast ? Colors.transparent : p.line),
                ),
              ],
            ),
          ),
          const SizedBox(width: Gap.md),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : Gap.lg),
              child: Text(
                step.text,
                style: TextStyle(
                  fontSize: 15,
                  height: 1.4,
                  color: step.color ?? p.ink,
                ),
              ),
            ),
          ),
          if (step.time != null)
            Padding(
              padding: const EdgeInsets.only(left: Gap.sm),
              child: Text(
                step.time!,
                style: TextStyle(
                  fontSize: 13,
                  color: p.inkFaint,
                  height: 1.55,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.color, required this.title, required this.body});

  final IconData icon;
  final Color color;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      padding: const EdgeInsets.all(Gap.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: p.isDark ? 0.14 : 0.08),
        borderRadius: Corner.medium,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: Gap.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: p.ink),
                ),
                const SizedBox(height: 4),
                Text(body, style: TextStyle(fontSize: 14, height: 1.5, color: p.inkSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PrivacyNote extends StatelessWidget {
  const _PrivacyNote();

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(Icons.lock_outline_rounded, size: 16, color: p.inkFaint),
        const SizedBox(width: Gap.sm),
        Expanded(
          child: Text(
            '원본 음성은 글로 옮긴 직후 삭제돼요. 이 방문에서 남는 것은 스냅샷 한 장과 위의 글뿐이에요.',
            style: TextStyle(fontSize: 13, height: 1.5, color: p.inkFaint),
          ),
        ),
      ],
    );
  }
}

/// 팀 연동 확인용 원본 값. 평소에는 접혀 있다.
class _TechnicalInfo extends StatelessWidget {
  const _TechnicalInfo({required this.event});

  final VisitEvent event;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final e = event;
    final rows = <(String, String?)>[
      ('eventId', '${e.eventId}'),
      ('deviceId', e.deviceId),
      ('status', e.status.name),
      ('eventType', e.eventType),
      ('purpose', e.purpose),
      ('mainCategory', e.mainCategory),
      ('subCategory', e.subCategory),
      ('responsePolicy', e.responsePolicy),
      ('snapshotUrl', e.snapshotUrl),
    ];

    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: EdgeInsets.zero,
        shape: const Border(),
        collapsedShape: const Border(),
        childrenPadding: const EdgeInsets.only(bottom: Gap.md),
        title: Text('기술 정보', style: TextStyle(fontSize: 13, color: p.inkFaint)),
        iconColor: p.inkFaint,
        collapsedIconColor: p.inkFaint,
        children: [
          for (final (key, value) in rows)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 120,
                    child: Text(
                      key,
                      style: TextStyle(fontFamily: 'monospace', fontSize: 12, color: p.inkFaint),
                    ),
                  ),
                  Expanded(
                    child: SelectableText(
                      value ?? '—',
                      style: TextStyle(fontFamily: 'monospace', fontSize: 12, color: p.inkSoft),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _RoundButton extends StatelessWidget {
  const _RoundButton({required this.icon, required this.tooltip, required this.onTap});

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Tooltip(
      message: tooltip,
      child: Material(
        color: p.card.withValues(alpha: 0.92),
        shape: CircleBorder(side: BorderSide(color: p.line)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Icon(icon, size: 22, color: p.ink),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../state/app_scope.dart';
import '../state/policy.dart';
import 'widgets/theme_toggle.dart';

/// 알림·응대 정책 (기획서 1.2 "사용자가 정한 정책 범위 안에서 접수").
///
/// 서버에 정책 API가 아직 없어서 이 기기에만 저장한다.
/// 알림 설정은 앱 안의 "새 방문" 알림 띠에 바로 반영된다.
class PolicyScreen extends StatelessWidget {
  const PolicyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final policy = AppScope.of(context).policy;
    final p = context.palette;

    return Scaffold(
      appBar: AppBar(
        title: const Text('알림·응대 정책'),
        backgroundColor: p.paper,
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        actions: const [
          Padding(padding: EdgeInsets.only(right: Gap.page - 4), child: ThemeToggle()),
        ],
      ),
      body: ListenableBuilder(
        listenable: policy,
        builder: (context, _) => ListView(
          padding: const EdgeInsets.only(bottom: Gap.xxl),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(Gap.page, Gap.sm, Gap.page, 0),
              child: _Notice(
                text: '서버에 정책 저장 기능이 준비되기 전이라, 지금은 이 기기에만 저장돼요. '
                    '알림 설정은 앱 안의 "새 방문" 알림에 바로 반영돼요.',
              ),
            ),

            // ── 응대 방식 ──
            const _Title('부재 중 현관 응대'),
            _Card(
              children: [
                for (final m in ReceptionMode.values)
                  _Choice(
                    title: m.label,
                    subtitle: m.description,
                    selected: policy.reception == m,
                    onTap: () => policy.update(() => policy.reception = m),
                  ),
              ],
            ),
            const _Foot('어느 쪽이든 원본 영상·음성은 남기지 않고, 문은 열리지 않아요.'),

            // ── 알림 ──
            const _Title('알림 받을 방문'),
            _Card(
              children: [
                _Toggle(
                  icon: Icons.inventory_2_outlined,
                  title: '물품 도착',
                  subtitle: '사람 없이 물건만 놓였을 때',
                  value: policy.notifyPackages,
                  onChanged: (v) => policy.update(() => policy.notifyPackages = v),
                ),
                _Toggle(
                  icon: Icons.local_shipping_outlined,
                  title: '배송·수거',
                  subtitle: '택배, 음식 배달, 반품 회수',
                  value: policy.notifyDeliveries,
                  onChanged: (v) => policy.update(() => policy.notifyDeliveries = v),
                ),
                _Toggle(
                  icon: Icons.waving_hand_outlined,
                  title: '방문객',
                  subtitle: '지인, 이웃, 점검·수리, 공공기관',
                  value: policy.notifyVisitors,
                  onChanged: (v) => policy.update(() => policy.notifyVisitors = v),
                ),
                _Toggle(
                  icon: Icons.campaign_outlined,
                  title: '영업·홍보, 잘못 찾아온 방문',
                  subtitle: '판매 권유, 전단지, 주소 착오',
                  value: policy.notifySales,
                  onChanged: (v) => policy.update(() => policy.notifySales = v),
                ),
                const _Toggle(
                  icon: Icons.emergency_outlined,
                  title: '긴급·안전 확인',
                  subtitle: '항상 알려요 (끌 수 없음)',
                  value: true,
                  onChanged: null,
                ),
              ],
            ),

            // ── 방해 금지 ──
            const _Title('방해 금지 시간'),
            _Card(
              children: [
                _Toggle(
                  icon: Icons.bedtime_outlined,
                  title: '방해 금지 사용',
                  subtitle: '이 시간에는 긴급·안전 확인만 알려요',
                  value: policy.quietHoursEnabled,
                  onChanged: (v) => policy.update(() => policy.quietHoursEnabled = v),
                ),
                AnimatedSize(
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOut,
                  child: policy.quietHoursEnabled
                      ? Padding(
                          padding: const EdgeInsets.fromLTRB(Gap.lg, 0, Gap.lg, Gap.md),
                          child: Row(
                            children: [
                              _HourPicker(
                                value: policy.quietStart,
                                onChanged: (h) => policy.update(() => policy.quietStart = h),
                              ),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: Gap.md),
                                child: Text('부터', style: TextStyle(color: p.inkSoft)),
                              ),
                              _HourPicker(
                                value: policy.quietEnd,
                                onChanged: (h) => policy.update(() => policy.quietEnd = h),
                              ),
                              Padding(
                                padding: const EdgeInsets.only(left: Gap.md),
                                child: Text('까지', style: TextStyle(color: p.inkSoft)),
                              ),
                            ],
                          ),
                        )
                      : const SizedBox(width: double.infinity),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Title extends StatelessWidget {
  const _Title(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(Gap.page + 4, Gap.xxl, Gap.page, Gap.sm),
        child: Semantics(
          header: true,
          child: Text(
            text,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: context.palette.inkSoft),
          ),
        ),
      );
}

class _Foot extends StatelessWidget {
  const _Foot(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(Gap.page + 4, Gap.sm, Gap.page, 0),
        child: Text(text, style: TextStyle(fontSize: 12.5, height: 1.5, color: context.palette.inkFaint)),
      );
}

class _Card extends StatelessWidget {
  const _Card({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Gap.lg),
      child: Material(
        color: p.card,
        shape: RoundedRectangleBorder(borderRadius: Corner.medium, side: BorderSide(color: p.line)),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < children.length; i++) ...[
              if (i > 0 && children[i] is! AnimatedSize) Divider(indent: Gap.lg, endIndent: Gap.lg, color: p.line),
              children[i],
            ],
          ],
        ),
      ),
    );
  }
}

class _Toggle extends StatelessWidget {
  const _Toggle({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return SwitchListTile(
      value: value,
      onChanged: onChanged,
      secondary: Icon(icon, color: onChanged == null ? p.danger : p.ink),
      title: Text(title),
      subtitle: Text(subtitle),
      contentPadding: const EdgeInsets.symmetric(horizontal: Gap.lg),
    );
  }
}

class _Choice extends StatelessWidget {
  const _Choice({required this.title, required this.subtitle, required this.selected, required this.onTap});

  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Semantics(
      selected: selected,
      button: true,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(Gap.lg, 14, Gap.lg, 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: 20,
                height: 20,
                margin: const EdgeInsets.only(top: 1),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: selected ? p.accent : p.inkFaint, width: selected ? 6 : 1.6),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: p.ink)),
                    const SizedBox(height: 3),
                    Text(subtitle, style: TextStyle(fontSize: 13.5, height: 1.45, color: p.inkSoft)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HourPicker extends StatelessWidget {
  const _HourPicker({required this.value, required this.onChanged});

  final int value;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: p.paper,
        borderRadius: Corner.small,
        border: Border.all(color: p.line),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<int>(
          value: value,
          dropdownColor: p.card,
          borderRadius: Corner.small,
          items: [
            for (var h = 0; h < 24; h++)
              DropdownMenuItem(
                value: h,
                child: Text('${h < 12 ? '오전' : '오후'} ${h % 12 == 0 ? 12 : h % 12}시'),
              ),
          ],
          onChanged: (h) {
            if (h != null) onChanged(h);
          },
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      padding: const EdgeInsets.all(Gap.md),
      decoration: BoxDecoration(
        color: p.accent.withValues(alpha: p.isDark ? 0.14 : 0.08),
        borderRadius: Corner.medium,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline_rounded, size: 18, color: p.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: TextStyle(fontSize: 13, height: 1.5, color: p.ink)),
          ),
        ],
      ),
    );
  }
}

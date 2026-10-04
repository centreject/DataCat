import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../data/api.dart';
import '../data/demo_api.dart';
import '../data/models.dart';
import '../state/app_scope.dart';
import '../state/policy.dart';
import 'policy_screen.dart';
import 'widgets/theme_toggle.dart';

/// 서버 연결, 현관 안내 문구, 개인정보 원칙.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

enum _TestState { idle, running, ok, failed }

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _url;
  _TestState _test = _TestState.idle;
  String _testMessage = '';

  DataCatApi? _presetsFor;
  Future<List<Preset>>? _presets;

  @override
  void initState() {
    super.initState();
    _url = TextEditingController();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_url.text.isEmpty) _url.text = AppScope.of(context).settings.baseUrl;
  }

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _test = _TestState.running;
      _testMessage = '';
    });
    try {
      final api = HttpDataCatApi(_url.text, timeout: const Duration(seconds: 5));
      final page = await api.fetchEvents(size: 1);
      if (!mounted) return;
      final total = page.totalElements;
      setState(() {
        _test = _TestState.ok;
        _testMessage = total == null ? '연결됐어요' : '연결됐어요 · 저장된 기록 $total건';
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _test = _TestState.failed;
        _testMessage = e.message;
      });
    } on FormatException {
      if (!mounted) return;
      setState(() {
        _test = _TestState.failed;
        _testMessage = '주소 형식이 올바르지 않아요.';
      });
    }
  }

  Future<void> _save() async {
    FocusScope.of(context).unfocus();
    final settings = AppScope.of(context).settings;
    final messenger = ScaffoldMessenger.of(context);
    final String normalized;
    try {
      normalized = HttpDataCatApi.normalizeBaseUrl(_url.text).toString();
    } on FormatException {
      messenger.showSnackBar(const SnackBar(content: Text('주소 형식이 올바르지 않아요.')));
      return;
    }
    _url.text = normalized;
    await settings.setBaseUrl(normalized);
    if (settings.demoMode) {
      messenger.showSnackBar(
        const SnackBar(content: Text('저장했어요. 데모 모드를 끄면 이 서버에 연결돼요.')),
      );
    } else {
      messenger.showSnackBar(const SnackBar(content: Text('저장했어요. 새 주소로 기록을 불러와요.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final scope = AppScope.of(context);
    final settings = scope.settings;
    final p = context.palette;

    return ListenableBuilder(
      listenable: Listenable.merge([settings, scope.store]),
      builder: (context, _) {
        final api = scope.store.api;
        if (!identical(api, _presetsFor)) {
          _presetsFor = api;
          _presets = api.fetchPresets();
        }

        return ListView(
          padding: EdgeInsets.fromLTRB(
            0,
            MediaQuery.paddingOf(context).top + Gap.lg,
            0,
            Gap.xxl,
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(Gap.page, 0, Gap.page, Gap.sm),
              child: Row(
                children: [
                  Expanded(
                    child: Semantics(
                      header: true,
                      child: Text('설정', style: context.text.headlineMedium),
                    ),
                  ),
                  const ThemeToggle(),
                ],
              ),
            ),

            // ── 화면 ──
            const _GroupTitle('화면 테마'),
            _Group(
              children: [
                Padding(
                  padding: const EdgeInsets.all(Gap.md),
                  child: SegmentedButton<ThemeMode>(
                    showSelectedIcon: false,
                    segments: const [
                      ButtonSegment(value: ThemeMode.system, icon: Icon(Icons.brightness_auto_outlined, size: 18), label: Text('시스템')),
                      ButtonSegment(value: ThemeMode.light, icon: Icon(Icons.light_mode_outlined, size: 18), label: Text('라이트')),
                      ButtonSegment(value: ThemeMode.dark, icon: Icon(Icons.dark_mode_outlined, size: 18), label: Text('다크')),
                    ],
                    selected: {settings.themeMode},
                    onSelectionChanged: (s) => settings.setThemeMode(s.first),
                  ),
                ),
              ],
            ),

            // ── 정책 ──
            const _GroupTitle('알림·응대 정책'),
            _Group(
              children: [
                ListenableBuilder(
                  listenable: scope.policy,
                  builder: (context, _) => ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: Gap.lg, vertical: 4),
                    leading: Icon(Icons.rule_rounded, color: p.ink),
                    title: const Text('부재 중 응대와 알림 받을 방문'),
                    subtitle: Text(_policySummary(scope.policy)),
                    trailing: Icon(Icons.chevron_right_rounded, color: p.inkFaint),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => const PolicyScreen()),
                    ),
                  ),
                ),
              ],
            ),

            // ── 연결 ──
            const _GroupTitle('서버 연결'),
            _Group(
              children: [
                SwitchListTile(
                  value: settings.demoMode,
                  onChanged: settings.setDemoMode,
                  title: const Text('데모 모드'),
                  subtitle: const Text('서버 없이 예시 기록으로 화면을 둘러봐요'),
                  contentPadding: const EdgeInsets.symmetric(horizontal: Gap.lg),
                ),
                if (api is DemoDataCatApi)
                  ListTile(
                    contentPadding: const EdgeInsets.fromLTRB(Gap.lg, 0, Gap.md, 0),
                    title: const Text('새 방문 시뮬레이션'),
                    subtitle: const Text('시연용 — 방금 누가 다녀간 것처럼 기록을 하나 추가해요'),
                    trailing: OutlinedButton(
                      onPressed: () {
                        api.simulateVisit();
                        scope.store.checkForNew();
                      },
                      child: const Text('추가'),
                    ),
                  ),
                Divider(indent: Gap.lg, endIndent: Gap.lg, color: p.line),
                Padding(
                  padding: const EdgeInsets.fromLTRB(Gap.lg, Gap.md, Gap.lg, Gap.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Spring 서버 주소', style: context.text.labelLarge),
                      const SizedBox(height: Gap.sm),
                      TextField(
                        controller: _url,
                        keyboardType: TextInputType.url,
                        autocorrect: false,
                        textInputAction: TextInputAction.done,
                        onSubmitted: (_) => _save(),
                        style: const TextStyle(fontSize: 15),
                        decoration: InputDecoration(
                          hintText: 'http://192.168.0.12:8080',
                          isDense: true,
                          filled: true,
                          fillColor: p.paper,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                          border: OutlineInputBorder(
                            borderRadius: Corner.small,
                            borderSide: BorderSide(color: p.line),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: Corner.small,
                            borderSide: BorderSide(color: p.line),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: Corner.small,
                            borderSide: BorderSide(color: p.accent, width: 1.5),
                          ),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '/api/v1 은 앱이 알아서 붙여요. 휴대폰과 서버가 같은 와이파이에 있어야 해요.',
                        style: context.text.bodySmall,
                      ),
                      const SizedBox(height: Gap.md),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: _test == _TestState.running ? null : _testConnection,
                              child: _test == _TestState.running
                                  ? const SizedBox.square(
                                      dimension: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Text('연결 확인'),
                            ),
                          ),
                          const SizedBox(width: Gap.sm),
                          Expanded(
                            child: FilledButton(onPressed: _save, child: const Text('저장')),
                          ),
                        ],
                      ),
                      if (_test == _TestState.ok || _test == _TestState.failed) ...[
                        const SizedBox(height: Gap.md),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              _test == _TestState.ok
                                  ? Icons.check_circle_rounded
                                  : Icons.error_outline_rounded,
                              size: 18,
                              color: _test == _TestState.ok ? p.live : p.danger,
                            ),
                            const SizedBox(width: Gap.sm),
                            Expanded(
                              child: Text(
                                _testMessage,
                                style: TextStyle(fontSize: 14, color: p.ink, height: 1.4),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),

            // ── 프리셋 ──
            const _GroupTitle('현관 안내 문구'),
            _Group(
              children: [
                FutureBuilder<List<Preset>>(
                  future: _presets,
                  builder: (context, snap) {
                    if (snap.connectionState != ConnectionState.done) {
                      return const Padding(
                        padding: EdgeInsets.all(Gap.xl),
                        child: Center(
                          child: SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        ),
                      );
                    }
                    final presets = snap.data ?? const <Preset>[];
                    if (snap.hasError || presets.isEmpty) {
                      return Padding(
                        padding: const EdgeInsets.all(Gap.lg),
                        child: Text(
                          snap.hasError ? '서버에서 안내 문구를 받아오지 못했어요.' : '등록된 안내 문구가 없어요.',
                          style: context.text.bodyMedium,
                        ),
                      );
                    }
                    return Column(
                      children: [
                        for (var i = 0; i < presets.length; i++) ...[
                          if (i > 0) Divider(indent: Gap.lg, endIndent: Gap.lg, color: p.line),
                          _PresetRow(preset: presets[i]),
                        ],
                      ],
                    );
                  },
                ),
              ],
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(Gap.page + 4, Gap.sm, Gap.page, 0),
              child: _Footnote(
                '현관 기기에는 고정 음원이 들어 있어 문구 수정은 아직 지원하지 않아요. '
                '음성 합성이 도입되는 3단계에서 열릴 예정이에요.',
              ),
            ),

            // ── 원칙 ──
            const _GroupTitle('이 기기가 지키는 것'),
            const _Group(
              children: [
                _Principle(
                  icon: Icons.videocam_off_outlined,
                  title: '상시 녹화하지 않아요',
                  body: '거리 센서가 방문을 감지했을 때만 사진을 찍고, 영상은 남기지 않아요.',
                ),
                _Principle(
                  icon: Icons.mic_off_outlined,
                  title: '예고 없이 듣지 않아요',
                  body: '안내 음성이 먼저 나간 뒤에만 마이크가 켜지고, 원본 음성은 글로 옮긴 즉시 지워져요.',
                ),
                _Principle(
                  icon: Icons.no_meeting_room_outlined,
                  title: '문을 대신 열지 않아요',
                  body: '분류 결과는 알림과 기록에만 쓰여요. 최종 판단은 언제나 사용자가 해요.',
                ),
              ],
            ),

            const SizedBox(height: Gap.xxl),
            Center(
              child: Text(
                'DataCat 무인현관 · 앱 0.2.0 · API v1.4',
                style: TextStyle(fontSize: 12, color: p.inkFaint),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _GroupTitle extends StatelessWidget {
  const _GroupTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.page + 4, Gap.xxl, Gap.page, Gap.sm),
      child: Semantics(
        header: true,
        child: Text(
          text,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: context.palette.inkSoft,
          ),
        ),
      ),
    );
  }
}

class _Group extends StatelessWidget {
  const _Group({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Gap.lg),
      child: Material(
        color: p.card,
        shape: RoundedRectangleBorder(
          borderRadius: Corner.medium,
          side: BorderSide(color: p.line),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
      ),
    );
  }
}

class _PresetRow extends StatelessWidget {
  const _PresetRow({required this.preset});

  final Preset preset;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Gap.lg, vertical: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              preset.typeLabel,
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: p.inkSoft, height: 1.5),
            ),
          ),
          Expanded(
            child: Text(
              preset.text,
              style: TextStyle(fontSize: 15, color: p.ink, height: 1.45),
            ),
          ),
        ],
      ),
    );
  }
}

class _Principle extends StatelessWidget {
  const _Principle({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.lg, 14, Gap.lg, 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 22, color: p.ink),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: p.ink)),
                const SizedBox(height: 3),
                Text(body, style: TextStyle(fontSize: 13.5, height: 1.5, color: p.inkSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Footnote extends StatelessWidget {
  const _Footnote(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text, style: TextStyle(fontSize: 12.5, height: 1.5, color: context.palette.inkFaint));
  }
}


String _policySummary(VisitPolicy p) {
  final parts = <String>[p.reception.label];
  final off = [
    if (!p.notifyPackages) '물품',
    if (!p.notifyDeliveries) '배송',
    if (!p.notifyVisitors) '방문',
    if (!p.notifySales) '영업',
  ];
  parts.add(off.isEmpty ? '모든 방문 알림' : '${off.join('·')} 알림 끔');
  if (p.quietHoursEnabled) parts.add('방해 금지 ${p.quietStart}시~${p.quietEnd}시');
  return parts.join('  ·  ');
}

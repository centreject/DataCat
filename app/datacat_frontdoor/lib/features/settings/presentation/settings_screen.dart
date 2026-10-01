import 'package:flutter/material.dart';

import '../../../shared/widgets/placeholder_view.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PlaceholderView(
      icon: Icons.settings_outlined,
      title: '설정',
      description: '응답 정책·프리셋·알림 설정을 이곳에 추가할 예정입니다.',
    );
  }
}

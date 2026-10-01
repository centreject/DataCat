import 'package:flutter/material.dart';

import 'app/app.dart';
import 'features/events/data/mock_event_repository.dart';

void main() {
  runApp(MunapApp(eventRepository: MockEventRepository()));
}

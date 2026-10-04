import 'package:flutter/material.dart';

import 'app.dart';
import 'state/event_store.dart';
import 'state/policy.dart';
import 'state/settings.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settings = AppSettings();
  final policy = VisitPolicy();
  await Future.wait([settings.load(), policy.load()]);

  runApp(DataCatApp(
    settings: settings,
    store: EventStore(settings.createApi()),
    policy: policy,
  ));
}

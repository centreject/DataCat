import 'package:flutter/material.dart';

import 'app.dart';
import 'state/event_store.dart';
import 'state/settings.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settings = AppSettings();
  await settings.load();

  runApp(DataCatApp(
    settings: settings,
    store: EventStore(settings.createApi()),
  ));
}

/// EvidencIA — Test de widget básico
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:evidencia/app.dart';

void main() {
  testWidgets('App smoke test', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: EvidencIAApp()),
    );
    expect(find.text('EvidencIA'), findsWidgets);
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:book_scanner/main.dart';

void main() {
  testWidgets('App launches successfully', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: BiShengApp()),
    );
    await tester.pumpAndSettle();
    expect(find.text('毕昇微光'), findsWidgets);
  });
}

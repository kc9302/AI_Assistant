import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:client/main.dart';
import 'package:client/domain/repositories/hybrid_router.dart';
import 'package:client/presentation/providers/chat_provider.dart';
import 'package:client/presentation/providers/settings_provider.dart'; // Import SettingsProvider
import '../test/mocks/mock_hybrid_router.dart';

void main() {
  testWidgets('ChatPage loads and displays initial elements', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => SettingsProvider()), // Provide SettingsProvider
          Provider<HybridRouter>(
            create: (_) => MockHybridRouter(),
          ),
          ChangeNotifierProvider<ChatProvider>(
            create: (context) => ChatProvider(router: context.read<HybridRouter>()),
          ),
        ],
        child: const MyApp(),
      ),
    );

    // Verify that the AppBar title is present
    expect(find.text('Agent Chat'), findsOneWidget);

    // Verify that the message input field is present
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Type a message...'), findsOneWidget);

    // Verify that the send button is present
    expect(find.byIcon(Icons.send), findsOneWidget);
  });

  testWidgets('ChatPage sends and displays remote messages', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => SettingsProvider()), // Provide SettingsProvider
          Provider<HybridRouter>(
            create: (_) => MockHybridRouter(),
          ),
          ChangeNotifierProvider<ChatProvider>(
            create: (context) => ChatProvider(router: context.read<HybridRouter>()),
          ),
        ],
        child: const MyApp(),
      ),
    );

    final chatInputFinder = find.byType(TextField);
    expect(chatInputFinder, findsOneWidget);

    // Enter text into the input field
    await tester.enterText(chatInputFinder, 'Hello, agent!');
    await tester.pump(); // Rebuild the widget after entering text

    // Tap the send button
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle(); // Wait for all animations and rebuilds to complete

    // Verify that the user's message is displayed
    expect(find.text('Hello, agent!'), findsOneWidget);

    // Verify that the mock remote response is displayed
    expect(find.text('Remote mock response to: "Hello, agent!"'), findsOneWidget);
  });

  testWidgets('ChatPage sends and displays local messages', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => SettingsProvider()), // Provide SettingsProvider
          Provider<HybridRouter>(
            create: (_) => MockHybridRouter(),
          ),
          ChangeNotifierProvider<ChatProvider>(
            create: (context) => ChatProvider(router: context.read<HybridRouter>()),
          ),
        ],
        child: const MyApp(),
      ),
    );

    final chatInputFinder = find.byType(TextField);
    expect(chatInputFinder, findsOneWidget);

    // Enter text into the input field
    await tester.enterText(chatInputFinder, 'local message');
    await tester.pump(); // Rebuild the widget after entering text

    // Tap the send button
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle(); // Wait for all animations and rebuilds to complete

    // Verify that the user's message is displayed
    expect(find.text('local message'), findsOneWidget);

    // Verify that the mock local response is displayed
    expect(find.text('Local mock response to: "local message"'), findsOneWidget);
  });

  testWidgets('Navigation to SettingsPage works', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => SettingsProvider()), // Provide SettingsProvider
          Provider<HybridRouter>(
            create: (_) => MockHybridRouter(),
          ),
          ChangeNotifierProvider<ChatProvider>(
            create: (context) => ChatProvider(router: context.read<HybridRouter>()),
          ),
        ],
        child: const MyApp(),
      ),
    );

    // Verify that ChatPage is displayed initially
    expect(find.text('Agent Chat'), findsOneWidget);
    expect(find.text('Settings'), findsNothing); // Settings page should not be visible

    // Tap the settings icon
    await tester.tap(find.byIcon(Icons.settings));
    await tester.pumpAndSettle(); // Wait for the navigation animation to complete

    // Verify that SettingsPage is displayed
    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('Agent Chat'), findsNothing); // Chat page should not be visible
  });
}
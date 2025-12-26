import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:client/data/repositories/chat_repository_impl.dart';
import 'package:client/data/repositories/local_llm_repository.dart';
import 'package:client/domain/repositories/chat_repository.dart';
import 'package:client/domain/repositories/hybrid_router.dart';
import 'package:client/presentation/providers/chat_provider.dart';
import 'package:client/presentation/pages/chat_page.dart';
import 'package:client/presentation/providers/settings_provider.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => SettingsProvider()),
        Provider<LocalLlmRepository>(create: (_) => LocalLlmRepositoryImpl()),
        ProxyProvider<SettingsProvider, ChatRepository>(
          update: (context, settings, previous) =>
              ChatRepositoryImpl(baseUrl: settings.baseUrl),
        ),
        ProxyProvider3<
          SettingsProvider,
          ChatRepository,
          LocalLlmRepository,
          HybridRouter
        >(
          update: (context, settings, remote, local, previous) => HybridRouter(
            remoteRepository: remote,
            localRepository: local,
            preferLocal: settings.useLocalLlm,
          ),
        ),
        ChangeNotifierProxyProvider<HybridRouter, ChatProvider>(
          create: (context) =>
              ChatProvider(router: context.read<HybridRouter>()),
          update: (context, router, previous) => ChatProvider(router: router),
        ),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<SettingsProvider>(
      builder: (context, settings, child) {
        return MaterialApp(
          title: 'FunctionGemma Agent',
          themeMode: settings.themeMode,
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.deepPurple,
              brightness: Brightness.light,
            ),
            useMaterial3: true,
          ),
          darkTheme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.deepPurple,
              brightness: Brightness.dark,
            ),
            useMaterial3: true,
          ),
          home: const ChatPage(),
        );
      },
    );
  }
}

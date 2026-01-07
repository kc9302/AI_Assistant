import 'dart:io';

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
        Provider<ChatRepository>(
          create: (_) {
            String baseUrl;
            try {
              if (Platform.isAndroid) {
                baseUrl = 'http://10.0.2.2:8000';
              } else {
                baseUrl = 'http://localhost:8000';
              }
            } catch (e) {
              baseUrl = 'http://localhost:8000';
            }
            return ChatRepositoryImpl(baseUrl: baseUrl);
          },
        ),
        ProxyProvider2<
          ChatRepository,
          LocalLlmRepository,
          HybridRouter
        >(
          update: (context, remote, local, previous) => HybridRouter(
            remoteRepository: remote,
            localRepository: local,
            preferLocal: false,
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
    return MaterialApp(
      title: 'FunctionGemma Agent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const ChatPage(),
    );
  }
}

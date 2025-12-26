import 'package:flutter/material.dart';
import 'package:client/domain/entities/chat_message.dart';
import 'package:client/domain/repositories/hybrid_router.dart'; // Import HybridRouter
import 'package:uuid/uuid.dart';

class ChatProvider extends ChangeNotifier {
  final HybridRouter router; // Use HybridRouter

  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _error;

  // Session ID for conversation memory
  final String _sessionId = const Uuid().v4();

  ChatProvider({required this.router}); // Update constructor

  List<ChatMessage> get messages => _messages;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> sendMessage(String content) async {
    _isLoading = true;
    _error = null;

    // Add user message immediately
    _messages.add(
      ChatMessage(content: content, isUser: true, threadId: _sessionId),
    );
    notifyListeners();

    try {
      final response = await router.sendMessage(
        content,
        threadId: _sessionId,
      ); // Use router
      _messages.add(response);
    } catch (e) {
      _error = e.toString();
      _messages.add(ChatMessage(content: "Error: $_error", isUser: false));
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

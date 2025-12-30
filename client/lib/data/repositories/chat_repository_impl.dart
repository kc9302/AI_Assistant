import 'package:flutter/foundation.dart';
import 'dart:convert';

import 'package:client/domain/entities/chat_message.dart';
import 'package:client/domain/repositories/chat_repository.dart';
import 'package:http/http.dart' as http;

class ChatRepositoryImpl implements ChatRepository {
  final String baseUrl;

  ChatRepositoryImpl({
    this.baseUrl = 'http://10.0.2.2:8000',
  }); // Android Emulator default

  @override
  Future<ChatMessage> sendMessage(String message, {String? threadId}) async {
    try {
      // Use configured host or localhost
      // Note: In real device, use PC IP.
      final uri = Uri.parse('$baseUrl/api/chat');

      final body = <String, dynamic>{'message': message};

      if (threadId != null) {
        body['thread_id'] = threadId;
      }

      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      debugPrint('--> HTTP POST $uri');
      debugPrint('Request Body: ${jsonEncode(body)}');

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        debugPrint('<-- HTTP 200 Response: ${utf8.decode(response.bodyBytes)}');
        return ChatMessage(
          content: data['response'] ?? '',
          isUser: false,
          mode: data['mode'] ?? 'plan',
          threadId: data['thread_id'],
        );
      } else {
        debugPrint('<-- HTTP ${response.statusCode} Error: ${response.body}');
        throw Exception('Failed to load response: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('HTTP Error: $e');
      throw Exception('Network error: $e');
    }
  }
}

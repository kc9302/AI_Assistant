import 'package:client/domain/entities/chat_message.dart';
import 'package:client/domain/repositories/chat_repository.dart';

class MockChatRepository implements ChatRepository {
  @override
  Future<ChatMessage> sendMessage(String message, {String? threadId}) async {
    // Simulate a delayed response
    await Future.delayed(const Duration(milliseconds: 100));
    return ChatMessage(
      content: 'Mock response to: "$message"',
      isUser: false,
      mode: 'mock',
      threadId: threadId,
    );
  }
}

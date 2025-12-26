import 'package:client/domain/entities/chat_message.dart';
import 'package:client/data/repositories/local_llm_repository.dart';

class MockLocalLlmRepository implements LocalLlmRepository {
  @override
  Future<ChatMessage> sendMessage(String message, {String? threadId}) async {
    await Future.delayed(const Duration(milliseconds: 10));
    return ChatMessage(
      content: 'Local mock response to: "$message"',
      isUser: false,
      mode: 'local_mock',
      threadId: threadId,
    );
  }
}

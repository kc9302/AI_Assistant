import 'package:client/domain/entities/chat_message.dart';

abstract class LocalLlmRepository {
  Future<ChatMessage> sendMessage(String message, {String? threadId});
}

class LocalLlmRepositoryImpl implements LocalLlmRepository {
  // In a real implementation, this would use mediapipe_genai to run the local model.
  // For now, it returns a mock response.
  @override
  Future<ChatMessage> sendMessage(String message, {String? threadId}) async {
    await Future.delayed(const Duration(milliseconds: 200));
    return ChatMessage(
      content: '안녕하세요! 저는 온디바이스 AI입니다. (Local)',
      isUser: false,
      mode: 'local_mock',
    );
  }
}

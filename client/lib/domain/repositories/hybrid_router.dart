import 'package:client/domain/entities/chat_message.dart';
import 'package:client/domain/repositories/chat_repository.dart';
import 'package:client/data/repositories/local_llm_repository.dart';

class HybridRouter {
  final ChatRepository remoteRepository;
  final LocalLlmRepository localRepository;
  final bool preferLocal;

  HybridRouter({
    required this.remoteRepository,
    required this.localRepository,
    this.preferLocal = false,
  });

  Future<ChatMessage> sendMessage(String message, {String? threadId}) {
    if (preferLocal || message.toLowerCase().contains('local')) {
      return localRepository.sendMessage(message, threadId: threadId);
    } else {
      return remoteRepository.sendMessage(message, threadId: threadId);
    }
  }
}

import 'package:client/domain/entities/chat_message.dart';
import 'package:client/domain/repositories/hybrid_router.dart';
import 'package:client/data/repositories/chat_repository_impl.dart';
import 'package:client/data/repositories/local_llm_repository.dart';

class MockHybridRouter extends HybridRouter {
  MockHybridRouter()
    : super(
        remoteRepository: ChatRepositoryImpl(),
        localRepository: LocalLlmRepositoryImpl(),
      );

  @override
  Future<ChatMessage> sendMessage(String message, {String? threadId}) {
    if (message.toLowerCase().contains('local')) {
      return Future.value(
        ChatMessage(
          content: 'Local mock response to: "$message"',
          isUser: false,
          mode: 'local_mock',
          threadId: threadId,
        ),
      );
    } else {
      return Future.value(
        ChatMessage(
          content: 'Remote mock response to: "$message"',
          isUser: false,
          mode: 'remote_mock',
          threadId: threadId,
        ),
      );
    }
  }
}

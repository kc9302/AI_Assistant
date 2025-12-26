import 'package:flutter_test/flutter_test.dart';
import 'package:client/domain/repositories/hybrid_router.dart';
import 'mocks/mock_chat_repository.dart';
import 'mocks/mock_local_llm_repository.dart';

void main() {
  group('HybridRouter', () {
    late MockChatRepository mockRemoteRepository;
    late MockLocalLlmRepository mockLocalRepository;
    late HybridRouter hybridRouter;

    setUp(() {
      mockRemoteRepository = MockChatRepository();
      mockLocalRepository = MockLocalLlmRepository();
      hybridRouter = HybridRouter(
        remoteRepository: mockRemoteRepository,
        localRepository: mockLocalRepository,
      );
    });

    test('routes to remote repository for general messages', () async {
      final message = 'Hello, server!';
      final response = await hybridRouter.sendMessage(message);
      
      expect(response.content, 'Mock response to: "$message"');
      expect(response.mode, 'mock');
    });

    test('routes to local repository for messages containing "local"', () async {
      final message = 'This is a local message';
      final response = await hybridRouter.sendMessage(message);

      expect(response.content, 'Local mock response to: "$message"');
      expect(response.mode, 'local_mock');
    });
  });
}

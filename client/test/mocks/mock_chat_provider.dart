import 'package:client/presentation/providers/chat_provider.dart';

class MockChatProvider extends ChatProvider {
  // Simply call the super constructor.
  // The mock behavior for sendMessage will come from the injected MockHybridRouter.
  MockChatProvider({required super.router});

  // No need to override messages, isLoading, error, or sendMessage if the
  // goal is to test ChatProvider's logic with a mocked router.
  // The base ChatProvider's logic for these will be used, and the router
  // will provide mock responses.

  // The clearMessages method might still be useful for test setup/teardown
  // if you want to reset the messages list of the *actual* ChatProvider's state.
  // However, for unit testing, it might be better to manage state external to the mock.
  // For now, let's keep it if it's intended to clear the *real* ChatProvider's messages list.
  // If the intent was to clear _mockMessages, it's no longer needed.
  // Let's remove it for now, assuming the base ChatProvider state is reset with each test.

  // If you need to manipulate the messages list directly in tests,
  // consider making a getter for it in ChatProvider that returns a modifiable list.
  // For now, we'll assume we test ChatProvider's public API.
}

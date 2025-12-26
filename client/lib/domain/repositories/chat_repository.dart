import 'package:client/domain/entities/chat_message.dart';

abstract class ChatRepository {
  Future<ChatMessage> sendMessage(String message, {String? threadId});
}

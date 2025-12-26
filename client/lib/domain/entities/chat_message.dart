class ChatMessage {
  final String content;
  final bool isUser;
  final String mode; // 'plan' or 'execute'
  final String? threadId;

  ChatMessage({
    required this.content,
    required this.isUser,
    this.mode = 'plan',
    this.threadId,
  });
}

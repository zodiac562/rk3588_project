class Logger {
  static final List<String> _logs = [];

  static void info(String message) {
    final entry = '[INFO] ${DateTime.now().toIso8601String()} $message';
    _logs.add(entry);
  }

  static void debug(String message) {
    final entry = '[DEBUG] ${DateTime.now().toIso8601String()} $message';
    _logs.add(entry);
  }

  static void warn(String message) {
    final entry = '[WARN] ${DateTime.now().toIso8601String()} $message';
    _logs.add(entry);
  }

  static void error(String message) {
    final entry = '[ERROR] ${DateTime.now().toIso8601String()} $message';
    _logs.add(entry);
  }

  static List<String> getAllLogs() => List.unmodifiable(_logs);

  static void clear() => _logs.clear();

  static String export() => _logs.join('\n');
}

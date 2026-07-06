import 'dart:convert';

// ─── APP → Hardware 命令 ────────────────────────
class CmdStartPrint {
  static const String type = 'CMD_START_PRINT';
  final Map<String, dynamic> payload;
  const CmdStartPrint({this.payload = const {}});
  Map<String, dynamic> toJson() => {'type': type, 'payload': payload};
}

class CmdPausePrint {
  static const String type = 'CMD_PAUSE_PRINT';
  final Map<String, dynamic> payload;
  const CmdPausePrint({this.payload = const {}});
  Map<String, dynamic> toJson() => {'type': type, 'payload': payload};
}

class CmdStopPrint {
  static const String type = 'CMD_STOP_PRINT';
  final Map<String, dynamic> payload;
  const CmdStopPrint({this.payload = const {}});
  Map<String, dynamic> toJson() => {'type': type, 'payload': payload};
}

class CmdEmergencyStop {
  static const String type = 'CMD_EMERGENCY_STOP';
  final Map<String, dynamic> payload;
  const CmdEmergencyStop({this.payload = const {}});
  Map<String, dynamic> toJson() => {'type': type, 'payload': payload};
}

// ─── Hardware → APP 状态 ────────────────────────
class StatusProgress {
  static const String type = 'STATUS_PROGRESS';
  final int current;
  final int total;
  final double percentage;

  const StatusProgress({required this.current, required this.total, required this.percentage});

  factory StatusProgress.fromPayload(Map<String, dynamic> payload) {
    return StatusProgress(
      current: payload['current'] ?? 0,
      total: payload['total'] ?? 0,
      percentage: (payload['percentage'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {'type': type, 'payload': {'current': current, 'total': total, 'percentage': percentage}};
}

class StatusError {
  static const String type = 'STATUS_ERROR';
  final String code;
  final String msg;

  const StatusError({required this.code, required this.msg});

  factory StatusError.fromPayload(Map<String, dynamic> payload) {
    return StatusError(code: payload['code'] ?? 'UNKNOWN', msg: payload['msg'] ?? '未知错误');
  }

  Map<String, dynamic> toJson() => {'type': type, 'payload': {'code': code, 'msg': msg}};
}

// ─── 通用消息解析 ────────────────────────────────
class HardwareMessage {
  final String type;
  final Map<String, dynamic> payload;

  const HardwareMessage({required this.type, required this.payload});

  factory HardwareMessage.fromJson(Map<String, dynamic> json) {
    return HardwareMessage(type: json['type'] ?? '', payload: Map<String, dynamic>.from(json['payload'] ?? {}));
  }

  factory HardwareMessage.fromJsonString(String raw) {
    try {
      final map = jsonDecode(raw) as Map<String, dynamic>;
      return HardwareMessage.fromJson(map);
    } catch (_) {
      return HardwareMessage(type: 'UNKNOWN', payload: {'raw': raw});
    }
  }

  Map<String, dynamic> toJson() => {'type': type, 'payload': payload};
  String toJsonString() => jsonEncode(toJson());
}

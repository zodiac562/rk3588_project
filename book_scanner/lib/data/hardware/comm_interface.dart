import 'dart:async';
import 'comm_protocol.dart';

abstract class IHardwareComm {
  Future<bool> connect(String deviceIdOrAddress);
  Future<void> disconnect();

  Future<bool> initialize();
  Future<void> startPrint();
  Future<void> pausePrint();
  Future<void> stopPrint();
  Future<void> emergencyStop();

  Stream<HardwareMessage> get deviceStatusStream;
}

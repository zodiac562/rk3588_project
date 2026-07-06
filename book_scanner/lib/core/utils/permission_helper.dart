import 'package:permission_handler/permission_handler.dart';

class PermissionHelper {
  static Future<bool> requestBluetooth() async {
    final status = await Permission.bluetooth.request();
    final scanStatus = await Permission.bluetoothScan.request();
    final connectStatus = await Permission.bluetoothConnect.request();
    return status.isGranted && scanStatus.isGranted && connectStatus.isGranted;
  }

  static Future<bool> requestLocation() async {
    final status = await Permission.location.request();
    return status.isGranted;
  }

  static Future<bool> requestStorage() async {
    final status = await Permission.storage.request();
    return status.isGranted;
  }

  static Future<bool> requestCamera() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  static Future<bool> requestAllForHardware() async {
    final results = await [
      Permission.bluetooth,
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.location,
      Permission.camera,
      Permission.storage,
    ].request();
    return results.values.every((s) => s.isGranted);
  }
}

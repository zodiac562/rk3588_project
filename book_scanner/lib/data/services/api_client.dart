import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String baseUrl = 'http://119.91.119.89:9000';

  static final ApiClient _instance = ApiClient._();
  factory ApiClient() => _instance;
  ApiClient._() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(_authInterceptor());
  }

  late final Dio _dio;
  String? _token;

  InterceptorsWrapper _authInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        handler.next(error);
      },
    );
  }

  Future<void> loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('access_token');
  }

  Future<void> saveToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }

  Future<void> clearToken() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
  }

  bool get hasToken => _token != null && _token!.isNotEmpty;

  // ─── Auth ────────────────────────────────────────

  Future<Map<String, dynamic>> login(String username, String password) async {
    final res = await _dio.post('/api/auth/login', data: {
      'username': username,
      'password': password,
    });
    final token = res.data['access_token'] as String;
    await saveToken(token);
    return res.data;
  }

  Future<Map<String, dynamic>> register(String username, String email, String password) async {
    final res = await _dio.post('/api/auth/register', data: {
      'username': username,
      'email': email,
      'password': password,
    });
    final token = res.data['access_token'] as String;
    await saveToken(token);
    return res.data;
  }

  Future<Map<String, dynamic>> getProfile() async {
    final res = await _dio.get('/api/auth/profile');
    return res.data;
  }

  Future<Map<String, dynamic>> updateProfile({String? username, String? avatar, String? bio}) async {
    final res = await _dio.put('/api/auth/profile', data: {
      if (username != null) 'username': username,
      if (avatar != null) 'avatar': avatar,
      if (bio != null) 'bio': bio,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> uploadAvatar(String filePath, {List<int>? bytes}) async {
    final formData = FormData.fromMap({
      'file': bytes != null
          ? MultipartFile.fromBytes(bytes, filename: 'avatar.png')
          : await MultipartFile.fromFile(filePath),
    });
    final res = await _dio.post('/api/auth/avatar', data: formData);
    return res.data;
  }

  // ─── Records ─────────────────────────────────────

  Future<Map<String, dynamic>> getRecords({String search = '', int page = 1, int pageSize = 20}) async {
    final res = await _dio.get('/api/records', queryParameters: {
      'search': search,
      'page': page,
      'page_size': pageSize,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> getRecord(String id) async {
    final res = await _dio.get('/api/records/$id');
    return res.data;
  }

  Future<Map<String, dynamic>> createRecord(Map<String, dynamic> data) async {
    final res = await _dio.post('/api/records', data: data);
    return res.data;
  }

  Future<Map<String, dynamic>> renameRecord(String id, String title) async {
    final res = await _dio.put('/api/records/$id', data: {'title': title});
    return res.data;
  }

  Future<void> deleteRecord(String id) async {
    await _dio.delete('/api/records/$id');
  }

  // ─── Device ──────────────────────────────────────

  Future<Map<String, dynamic>> getDeviceStatus() async {
    final res = await _dio.get('/api/device/status');
    return res.data;
  }

  Future<Map<String, dynamic>> connectDevice(String deviceId, {bool useWifi = false}) async {
    final res = await _dio.post('/api/device/connect', data: {
      'device_id': deviceId,
      'use_wifi': useWifi,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> disconnectDevice() async {
    final res = await _dio.post('/api/device/connect', data: {
      'device_id': '',
      'use_wifi': false,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> initializeDevice() async {
    final res = await _dio.post('/api/device/initialize');
    return res.data;
  }

  Future<Map<String, dynamic>> startPrint() async {
    final res = await _dio.post('/api/device/start');
    return res.data;
  }

  Future<Map<String, dynamic>> stopPrint() async {
    final res = await _dio.post('/api/device/stop');
    return res.data;
  }

  Future<Map<String, dynamic>> paperReady() async {
    final res = await _dio.post('/api/device/paper-ready');
    return res.data;
  }

  // ─── Logs ────────────────────────────────────────

  Future<Map<String, dynamic>> getLogs({String? deviceId, int limit = 50}) async {
    final res = await _dio.get('/api/logs', queryParameters: {
      if (deviceId != null) 'device_id': deviceId,
      'limit': limit,
    });
    return res.data;
  }

  Future<Map<String, dynamic>> uploadLogs(List<String> logs) async {
    final res = await _dio.post('/api/logs/upload', data: {'logs': logs});
    return res.data;
  }
}

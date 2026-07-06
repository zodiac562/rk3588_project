import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../data/models/user_model.dart';
import '../../../../data/services/api_client.dart';

enum AuthStatus { unauthenticated, authenticated, loading }

class AuthState {
  final AuthStatus status;
  final UserModel? user;
  final String? error;

  const AuthState({this.status = AuthStatus.unauthenticated, this.user, this.error});

  AuthState copyWith({AuthStatus? status, UserModel? user, String? error, bool clearError = false}) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiClient _api = ApiClient();

  AuthNotifier() : super(const AuthState()) {
    _tryAutoLogin();
  }

  Future<void> _tryAutoLogin() async {
    await _api.loadToken();
    if (_api.hasToken) {
      try {
        final profile = await _api.getProfile();
        state = state.copyWith(
          status: AuthStatus.authenticated,
          user: UserModel.fromJson(profile),
        );
      } catch (_) {
        _api.clearToken();
      }
    }
  }

  Future<void> login(String username, String password) async {
    state = state.copyWith(status: AuthStatus.loading, clearError: true);

    if (username.isEmpty || password.isEmpty) {
      state = state.copyWith(status: AuthStatus.unauthenticated, error: '请填写所有字段');
      return;
    }

    try {
      final data = await _api.login(username, password);
      state = state.copyWith(
        status: AuthStatus.authenticated,
        user: UserModel.fromJson(data['user']),
      );
    } catch (e) {
      final msg = _extractError(e);
      state = state.copyWith(status: AuthStatus.unauthenticated, error: msg);
    }
  }

  Future<void> register(String username, String email, String password, String confirm) async {
    state = state.copyWith(status: AuthStatus.loading, clearError: true);

    if (username.isEmpty || email.isEmpty || password.isEmpty) {
      state = state.copyWith(status: AuthStatus.unauthenticated, error: '请填写所有字段');
      return;
    }
    if (password != confirm) {
      state = state.copyWith(status: AuthStatus.unauthenticated, error: '两次密码不一致');
      return;
    }
    if (password.length < 6) {
      state = state.copyWith(status: AuthStatus.unauthenticated, error: '密码至少6位');
      return;
    }

    try {
      final data = await _api.register(username, email, password);
      state = state.copyWith(
        status: AuthStatus.authenticated,
        user: UserModel.fromJson(data['user']),
      );
    } catch (e) {
      final msg = _extractError(e);
      state = state.copyWith(status: AuthStatus.unauthenticated, error: msg);
    }
  }

  void logout() {
    _api.clearToken();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  void clearError() {
    state = state.copyWith(clearError: true);
  }

  void updateUser(UserModel user) {
    state = state.copyWith(user: user);
  }

  String _extractError(dynamic e) {
    if (e is Exception) {
      final s = e.toString();
      if (s.contains('401')) return '账号或密码错误';
      if (s.contains('409')) return '用户名或邮箱已被占用';
      if (s.contains('SocketException') || s.contains('timeout')) return '无法连接服务器，请检查网络';
      return '网络错误，请稍后重试';
    }
    return '未知错误';
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) => AuthNotifier());

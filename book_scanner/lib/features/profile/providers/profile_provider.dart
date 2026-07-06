import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/user_model.dart';
import '../../../data/services/api_client.dart';
import '../../../core/utils/logger.dart';

class ProfileState {
  final UserModel? user;
  final bool isLogUploading;
  final bool isSaving;
  final String? error;

  const ProfileState({this.user, this.isLogUploading = false, this.isSaving = false, this.error});

  ProfileState copyWith({UserModel? user, bool? isLogUploading, bool? isSaving, String? error, bool clearError = false}) {
    return ProfileState(
      user: user ?? this.user,
      isLogUploading: isLogUploading ?? this.isLogUploading,
      isSaving: isSaving ?? this.isSaving,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class ProfileNotifier extends StateNotifier<ProfileState> {
  final ApiClient _api = ApiClient();

  ProfileNotifier() : super(const ProfileState());

  Future<void> loadUser() async {
    try {
      final data = await _api.getProfile();
      state = state.copyWith(user: UserModel.fromJson(data));
    } catch (_) {}
  }

  Future<void> updateUsername(String username) async {
    state = state.copyWith(isSaving: true, clearError: true);
    try {
      final data = await _api.updateProfile(username: username);
      state = state.copyWith(user: UserModel.fromJson(data), isSaving: false);
    } catch (e) {
      state = state.copyWith(isSaving: false, error: '更新用户名失败');
    }
  }

  Future<void> updateBio(String bio) async {
    state = state.copyWith(isSaving: true, clearError: true);
    try {
      final data = await _api.updateProfile(bio: bio);
      state = state.copyWith(user: UserModel.fromJson(data), isSaving: false);
    } catch (e) {
      state = state.copyWith(isSaving: false, error: '更新签名失败');
    }
  }

  Future<void> uploadAvatar(String filePath, {List<int>? bytes}) async {
    state = state.copyWith(isSaving: true, clearError: true);
    try {
      final data = await _api.uploadAvatar(filePath, bytes: bytes);
      state = state.copyWith(user: UserModel.fromJson(data), isSaving: false);
    } catch (e) {
      state = state.copyWith(isSaving: false, error: '上传头像失败');
    }
  }

  Future<void> uploadLogs() async {
    state = state.copyWith(isLogUploading: true, clearError: true);
    try {
      final logs = Logger.getAllLogs();
      if (logs.isNotEmpty) {
        await _api.uploadLogs(logs);
      }
      state = state.copyWith(isLogUploading: false);
    } catch (e) {
      state = state.copyWith(isLogUploading: false, error: '上传失败，请检查网络连接');
    }
  }

  List<String> getLogs() => Logger.getAllLogs();
}

final profileProvider = StateNotifierProvider<ProfileNotifier, ProfileState>((ref) => ProfileNotifier());

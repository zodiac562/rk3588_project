import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/services/api_client.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/profile_provider.dart';

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  final _picker = ImagePicker();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);
    final profileState = ref.watch(profileProvider);
    final user = profileState.user ?? authState.user;

    return Scaffold(
      appBar: AppBar(title: const Text('我的'), centerTitle: true),
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.all(24),
          child: Column(children: [
            _profileHeader(theme, user),
            const SizedBox(height: 28),
            _sectionTitle(theme, '设备'),
            const SizedBox(height: 10),
            _menuTile(theme, Icons.bluetooth_rounded, '设备管理', '配对与管理硬件', () => context.go('/device-manage')),
            const SizedBox(height: 20),
            _sectionTitle(theme, '系统'),
            const SizedBox(height: 10),
            _menuTile(theme, Icons.bug_report_rounded, '上传错误日志', '将本地日志打包发送', () => _handleLogUpload(context, ref)),
            const SizedBox(height: 10),
            _menuTile(theme, Icons.settings_rounded, '退出登录', '退出当前账号', () => _showLogout(context, ref)),
            const SizedBox(height: 32),
          ]),
        ),
      ),
    );
  }

  Widget _profileHeader(ThemeData theme, dynamic user) {
    final avatarUrl = user?.avatar;
    final hasRemoteAvatar = avatarUrl != null && avatarUrl is String && avatarUrl.isNotEmpty;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.primary, Color(0xFFFF6B35)], begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(children: [
        GestureDetector(
          onTap: () => _pickAvatar(),
          child: Semantics(
            label: '点击更换头像',
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 72, height: 72,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.25),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white.withValues(alpha: 0.5), width: 3),
                image: hasRemoteAvatar
                    ? DecorationImage(
                        image: NetworkImage(avatarUrl.startsWith('http') ? avatarUrl : '${ApiClient.baseUrl}$avatarUrl'),
                        fit: BoxFit.cover,
                        onError: (exception, stackTrace) {
                          debugPrint('Avatar load failed: $exception');
                        },
                      )
                    : null,
              ),
              child: hasRemoteAvatar
                  ? null
                  : const Icon(Icons.camera_alt_rounded, color: Colors.white, size: 30),
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          GestureDetector(
            onTap: () => _editName(context, user),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Flexible(child: Text(user?.username ?? '用户', style: theme.textTheme.titleLarge?.copyWith(color: Colors.white, fontWeight: FontWeight.w800), overflow: TextOverflow.ellipsis)),
              const SizedBox(width: 6),
              const Icon(Icons.edit_rounded, color: Colors.white70, size: 18),
            ]),
          ),
          const SizedBox(height: 6),
          GestureDetector(
            onTap: () => _editBio(context, user),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Flexible(child: Text(user?.bio ?? '点击设置个性签名', style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 13))),
              const SizedBox(width: 6),
              const Icon(Icons.edit_rounded, color: Colors.white54, size: 16),
            ]),
          ),
        ])),
      ]),
    );
  }

  Future<void> _pickAvatar() async {
    try {
      final picked = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 512, maxHeight: 512, imageQuality: 85);
      if (picked == null) return;

      if (!mounted) return;
      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      await ref.read(profileProvider.notifier).uploadAvatar(picked.path, bytes: bytes);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('请授予相册访问权限'), behavior: SnackBarBehavior.floating),
        );
      }
    }
  }

  void _editName(BuildContext context, dynamic user) {
    final ctrl = TextEditingController(text: user?.username ?? '');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: const Text('修改用户名'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          maxLength: 20,
          decoration: const InputDecoration(hintText: '请输入新的用户名'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          FilledButton(
            onPressed: () async {
              final name = ctrl.text.trim();
              if (name.isEmpty) return;
              Navigator.pop(ctx);
              await ref.read(profileProvider.notifier).updateUsername(name);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('用户名已更新'), behavior: SnackBarBehavior.floating));
              }
            },
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  void _editBio(BuildContext context, dynamic user) {
    final ctrl = TextEditingController(text: user?.bio ?? '');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: const Text('修改个性签名'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          maxLength: 50,
          maxLines: 2,
          decoration: const InputDecoration(hintText: '请输入个性签名'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          FilledButton(
            onPressed: () async {
              final bio = ctrl.text.trim();
              Navigator.pop(ctx);
              await ref.read(profileProvider.notifier).updateBio(bio);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('签名已更新'), behavior: SnackBarBehavior.floating));
              }
            },
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(ThemeData theme, String text) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(text, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: theme.colorScheme.primary, letterSpacing: 0.5)),
    );
  }

  Widget _menuTile(ThemeData theme, IconData icon, String title, String subtitle, VoidCallback onTap) {
    return Material(
      color: theme.colorScheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(children: [
            Container(
              width: 44, height: 44,
              decoration: BoxDecoration(color: theme.colorScheme.primary.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
              child: Icon(icon, color: theme.colorScheme.primary, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              Text(subtitle, style: theme.textTheme.bodySmall),
            ])),
            Icon(Icons.chevron_right_rounded, color: theme.colorScheme.onSurface.withValues(alpha: 0.3)),
          ]),
        ),
      ),
    );
  }

  void _handleLogUpload(BuildContext context, WidgetRef ref) async {
    final state = ref.read(profileProvider.notifier);
    await state.uploadLogs();

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: const Text('日志已上传'), behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
      );
    }
  }

  void _showLogout(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final theme = Theme.of(context);
        return Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          ),
          padding: const EdgeInsets.all(24),
          child: SafeArea(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Container(width: 36, height: 4, decoration: BoxDecoration(color: theme.colorScheme.onSurface.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(2))),
              const SizedBox(height: 20),
              Semantics(button: true, label: '退出登录', child: SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () {
                    ref.read(authProvider.notifier).logout();
                    Navigator.pop(ctx);
                  },
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('退出登录'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.error,
                    side: const BorderSide(color: AppColors.error),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                ),
              )),
            ]),
          ),
        );
      },
    );
  }
}

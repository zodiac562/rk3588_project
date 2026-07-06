import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_theme.dart';
import '../providers/auth_provider.dart';

class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> with SingleTickerProviderStateMixin {
  final _usernameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _pwdCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _obscure = true;
  bool _obscureConfirm = true;
  late AnimationController _anim;
  late Animation<double> _fade;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));
    _fade = CurvedAnimation(parent: _anim, curve: Curves.easeOut);
    _anim.forward();
  }

  @override
  void dispose() {
    _usernameCtrl.dispose(); _emailCtrl.dispose(); _pwdCtrl.dispose(); _confirmCtrl.dispose();
    _anim.dispose();
    super.dispose();
  }

  void _register() {
    if (_formKey.currentState!.validate()) {
      ref.read(authProvider.notifier).register(
        _usernameCtrl.text.trim(), _emailCtrl.text.trim(), _pwdCtrl.text, _confirmCtrl.text,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final authState = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (prev, next) {
      if (next.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Row(children: [const Icon(Icons.error_outline, color: Colors.white, size: 20), const SizedBox(width: 10), Expanded(child: Text(next.error!))]),
          backgroundColor: AppColors.error, behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)), margin: const EdgeInsets.all(16),
        ));
        ref.read(authProvider.notifier).clearError();
      }
    });

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDark ? [const Color(0xFF1C1B1A), const Color(0xFF2A2928)] : [const Color(0xFFFFF8F0), const Color(0xFFFFF0E0)],
            begin: Alignment.topCenter, end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: FadeTransition(
                opacity: _fade,
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  const SizedBox(height: 24),
                  _logo(theme),
                  const SizedBox(height: 12),
                  _title(theme),
                  const SizedBox(height: 4),
                  _subtitle(theme),
                  const SizedBox(height: 32),
                  _card(theme, isDark, authState),
                  const SizedBox(height: 20),
                  _loginLink(theme),
                  const SizedBox(height: 24),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _logo(ThemeData theme) => Semantics(label: '注册', child: Container(
    width: 76, height: 76,
    decoration: BoxDecoration(
      gradient: const LinearGradient(colors: [AppColors.secondary, Color(0xFF81C784)], begin: Alignment.topLeft, end: Alignment.bottomRight),
      borderRadius: BorderRadius.circular(22),
      boxShadow: [BoxShadow(color: AppColors.secondary.withValues(alpha: 0.3), blurRadius: 20, offset: const Offset(0, 8))],
    ),
    child: const Icon(Icons.person_add_rounded, color: Colors.white, size: 36),
  ));

  Widget _title(ThemeData theme) => Text('创建账号', style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, color: AppColors.secondary));

  Widget _subtitle(ThemeData theme) => Text('加入毕昇微光，开启阅读之旅', style: theme.textTheme.bodyLarge?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.5)));

  Widget _card(ThemeData theme, bool isDark, AuthState authState) {
    return Container(
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [BoxShadow(color: AppColors.secondary.withValues(alpha: isDark ? 0.08 : 0.06), blurRadius: 30, offset: const Offset(0, 12))],
      ),
      child: Form(key: _formKey, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _label(theme, '用户名'), const SizedBox(height: 8),
        _input(ctrl: _usernameCtrl, hint: '您的昵称', icon: Icons.person_outline_rounded, v: (v) => v == null || v.isEmpty ? '请输入用户名' : null),
        const SizedBox(height: 14),
        _label(theme, '邮箱'), const SizedBox(height: 8),
        _input(ctrl: _emailCtrl, hint: 'your@email.com', icon: Icons.email_outlined, v: (v) => v == null || v.isEmpty ? '请输入邮箱' : null),
        const SizedBox(height: 14),
        _label(theme, '密码'), const SizedBox(height: 8),
        _input(ctrl: _pwdCtrl, hint: '至少6位', icon: Icons.lock_outlined, obscure: _obscure,
          suffix: IconButton(onPressed: () => setState(() => _obscure = !_obscure), icon: Icon(_obscure ? Icons.visibility_off_rounded : Icons.visibility_rounded, size: 20, color: theme.colorScheme.onSurface.withValues(alpha: 0.4))),
          v: (v) => v == null || v.isEmpty ? '请输入密码' : (v.length < 6 ? '至少6位' : null)),
        const SizedBox(height: 14),
        _label(theme, '确认密码'), const SizedBox(height: 8),
        _input(ctrl: _confirmCtrl, hint: '再次输入密码', icon: Icons.lock_outlined, obscure: _obscureConfirm,
          suffix: IconButton(onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm), icon: Icon(_obscureConfirm ? Icons.visibility_off_rounded : Icons.visibility_rounded, size: 20, color: theme.colorScheme.onSurface.withValues(alpha: 0.4))),
          v: (v) => v == null || v.isEmpty ? '请确认密码' : (v != _pwdCtrl.text ? '两次密码不一致' : null)),
        const SizedBox(height: 24),
        _btn(theme, isDark, authState),
      ])),
    );
  }

  Widget _label(ThemeData theme, String t) => Text(t, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700));

  Widget _input({required TextEditingController ctrl, required String hint, required IconData icon, bool obscure = false, Widget? suffix, String? Function(String?)? v}) {
    final theme = Theme.of(context);
    return Semantics(label: hint, child: TextFormField(
      controller: ctrl, obscureText: obscure, validator: v, style: theme.textTheme.bodyLarge,
      decoration: InputDecoration(
        hintText: hint, hintStyle: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: 0.3), fontSize: 14),
        prefixIcon: Icon(icon, size: 20, color: theme.colorScheme.onSurface.withValues(alpha: 0.4)), suffixIcon: suffix,
        filled: true, fillColor: theme.colorScheme.surface.withValues(alpha: 0.5),
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: theme.colorScheme.outline.withValues(alpha: 0.15))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: theme.colorScheme.outline.withValues(alpha: 0.15))),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: AppColors.secondary, width: 2)),
        errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: AppColors.error, width: 1.5)),
      ),
    ));
  }

  Widget _btn(ThemeData theme, bool isDark, AuthState authState) {
    final loading = authState.status == AuthStatus.loading;
    return SizedBox(width: double.infinity, child: Semantics(button: true, label: '注册', child: Material(
      borderRadius: BorderRadius.circular(16), elevation: isDark ? 0 : 2, shadowColor: AppColors.secondary.withValues(alpha: 0.3),
      child: InkWell(
        onTap: loading ? null : _register, borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(duration: const Duration(milliseconds: 300), height: 54,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), gradient: const LinearGradient(colors: [AppColors.secondary, Color(0xFF81C784)], begin: Alignment.topLeft, end: Alignment.bottomRight)),
          child: Center(child: loading
            ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2.5, valueColor: AlwaysStoppedAnimation<Color>(Colors.white)))
            : const Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.person_add_rounded, color: Colors.white, size: 20), SizedBox(width: 10), Text('注册', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16))])),
        ),
      ),
    )));
  }

  Widget _loginLink(ThemeData theme) {
    return Row(mainAxisAlignment: MainAxisAlignment.center, children: [
      Text('已有账号？', style: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: 0.5), fontSize: 14)),
      GestureDetector(onTap: () => context.go('/login'), child: Text(' 立即登录', style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.w700, fontSize: 14))),
    ]);
  }
}

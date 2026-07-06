import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_theme.dart';
import '../providers/auth_provider.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> with SingleTickerProviderStateMixin {
  final _emailCtrl = TextEditingController(text: 'test_admin');
  final _pwdCtrl = TextEditingController(text: '123456');
  final _formKey = GlobalKey<FormState>();
  bool _obscure = true;
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
    _emailCtrl.dispose();
    _pwdCtrl.dispose();
    _anim.dispose();
    super.dispose();
  }

  void _login() {
    ref.read(authProvider.notifier).login(_emailCtrl.text.trim(), _pwdCtrl.text.trim());
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
          backgroundColor: AppColors.error,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          margin: const EdgeInsets.all(16),
        ));
        ref.read(authProvider.notifier).clearError();
      }
    });

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDark ? [const Color(0xFF1C1B1A), const Color(0xFF2A2928)] : [const Color(0xFFFFF8F0), const Color(0xFFFFF0E0)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: FadeTransition(
                opacity: _fade,
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  const SizedBox(height: 40),
                  _logo(theme),
                  const SizedBox(height: 16),
                  _title(theme),
                  const SizedBox(height: 6),
                  _subtitle(theme),
                  const SizedBox(height: 42),
                  _card(theme, isDark, authState),
                  const SizedBox(height: 24),
                  _registerLink(theme),
                  const SizedBox(height: 40),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _logo(ThemeData theme) {
    return Semantics(label: '毕昇微光', child: Container(
      width: 88, height: 88,
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.primary, Color(0xFFFF6B35)], begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [BoxShadow(color: AppColors.primary.withValues(alpha: 0.3), blurRadius: 24, offset: const Offset(0, 8))],
      ),
      child: const Icon(Icons.auto_stories_rounded, color: Colors.white, size: 44),
    ));
  }

  Widget _title(ThemeData theme) {
    return Text('毕昇微光', style: theme.textTheme.headlineLarge?.copyWith(fontWeight: FontWeight.w900, color: AppColors.primary));
  }

  Widget _subtitle(ThemeData theme) {
    return Text('让阅读之光照亮每一个人', style: theme.textTheme.bodyLarge?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.5)));
  }

  Widget _card(ThemeData theme, bool isDark, AuthState authState) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(28),
        boxShadow: [BoxShadow(color: AppColors.primary.withValues(alpha: isDark ? 0.08 : 0.06), blurRadius: 30, offset: const Offset(0, 12))],
      ),
      child: Form(key: _formKey, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _fieldLabel(theme, '账号'),
        const SizedBox(height: 8),
        _input(controller: _emailCtrl, hint: '请输入账号', icon: Icons.person_outline_rounded, validator: (v) => v == null || v.isEmpty ? '请输入账号' : null),
        const SizedBox(height: 20),
        _fieldLabel(theme, '密码'),
        const SizedBox(height: 8),
        _input(
          controller: _pwdCtrl, hint: '请输入密码', icon: Icons.lock_outlined, obscure: _obscure,
          suffix: IconButton(onPressed: () => setState(() => _obscure = !_obscure), icon: Icon(_obscure ? Icons.visibility_off_rounded : Icons.visibility_rounded, size: 20, color: theme.colorScheme.onSurface.withValues(alpha: 0.4))),
          validator: (v) => v == null || v.isEmpty ? '请输入密码' : null,
        ),
        const SizedBox(height: 28),
        _loginBtn(theme, isDark, authState),
      ])),
    );
  }

  Widget _fieldLabel(ThemeData theme, String text) => Text(text, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700));

  Widget _input({required TextEditingController controller, required String hint, required IconData icon, bool obscure = false, Widget? suffix, String? Function(String?)? validator}) {
    final theme = Theme.of(context);
    return Semantics(
      label: hint,
      child: TextFormField(
        controller: controller, obscureText: obscure, validator: validator, style: theme.textTheme.bodyLarge,
        decoration: InputDecoration(
          hintText: hint, hintStyle: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: 0.3), fontSize: 14),
          prefixIcon: Icon(icon, size: 20, color: theme.colorScheme.onSurface.withValues(alpha: 0.4)),
          suffixIcon: suffix,
          filled: true, fillColor: theme.colorScheme.surface.withValues(alpha: 0.5),
          contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: theme.colorScheme.outline.withValues(alpha: 0.15))),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: theme.colorScheme.outline.withValues(alpha: 0.15))),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: theme.colorScheme.primary, width: 2)),
          errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: AppColors.error, width: 1.5)),
        ),
      ),
    );
  }

  Widget _loginBtn(ThemeData theme, bool isDark, AuthState authState) {
    final loading = authState.status == AuthStatus.loading;
    return Semantics(
      button: true, label: '登录',
      child: GestureDetector(
        onTap: loading ? null : _login,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          height: 56,
          width: double.infinity,
          decoration: BoxDecoration(
            color: loading ? theme.colorScheme.primary.withValues(alpha: 0.7) : theme.colorScheme.primary,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: theme.colorScheme.primary.withValues(alpha: 0.4), width: 1),
            boxShadow: [
              BoxShadow(color: theme.colorScheme.primary.withValues(alpha: 0.25), blurRadius: 16, offset: const Offset(0, 6)),
              BoxShadow(color: theme.colorScheme.primary.withValues(alpha: 0.08), blurRadius: 4, offset: const Offset(0, 2)),
            ],
          ),
          child: Center(
            child: loading
                ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.2, valueColor: AlwaysStoppedAnimation<Color>(Colors.white)))
                : const Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text('登录系统', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 15, letterSpacing: 0.8)),
                  ]),
          ),
        ),
      ),
    );
  }

  Widget _registerLink(ThemeData theme) {
    return Row(mainAxisAlignment: MainAxisAlignment.center, children: [
      Text('还没有账号？', style: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: 0.5), fontSize: 14)),
      GestureDetector(
        onTap: () => context.go('/register'),
        child: Text(' 立即注册', style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.w700, fontSize: 14)),
      ),
    ]);
  }
}

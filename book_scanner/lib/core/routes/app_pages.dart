import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants/route_names.dart';
import '../../features/auth/view/login_page.dart';
import '../../features/auth/view/register_page.dart';
import '../../features/home/view/home_page.dart';
import '../../features/repository/view/repo_list_page.dart';
import '../../features/repository/view/preview_page.dart';
import '../../features/profile/view/profile_page.dart';
import '../../features/profile/view/device_manage_page.dart';

final authRedirectNotifier = ValueNotifier<bool>(false);

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    refreshListenable: authRedirectNotifier,
    initialLocation: RouteNames.login,
    redirect: (context, state) {
      final isAuth = authRedirectNotifier.value;
      final loc = state.uri.toString();
      final isAuthRoute = loc == RouteNames.login || loc == RouteNames.register;

      if (!isAuth && !isAuthRoute) return RouteNames.login;
      if (isAuth && isAuthRoute) return RouteNames.home;
      return null;
    },
    routes: [
      GoRoute(
        path: RouteNames.login,
        pageBuilder: (_, s) => CustomTransitionPage(
          child: const LoginPage(),
          transitionsBuilder: (ctx, animation, secondary, child) => FadeTransition(opacity: animation, child: child),
        ),
      ),
      GoRoute(
        path: RouteNames.register,
        pageBuilder: (_, s) => CustomTransitionPage(
          child: const RegisterPage(),
          transitionsBuilder: (ctx, animation, secondary, child) => FadeTransition(opacity: animation, child: child),
        ),
      ),
      ShellRoute(
        builder: (_, s, child) => _AppShell(child: child),
        routes: [
          GoRoute(
            path: RouteNames.home,
            pageBuilder: (_, s) => const NoTransitionPage(child: HomePage()),
          ),
          GoRoute(
            path: RouteNames.repository,
            pageBuilder: (_, s) => const NoTransitionPage(child: RepoListPage()),
          ),
          GoRoute(
            path: RouteNames.profile,
            pageBuilder: (_, s) => const NoTransitionPage(child: ProfilePage()),
          ),
          GoRoute(
            path: '/preview',
            pageBuilder: (_, state) {
              final recordId = state.uri.queryParameters['id'] ?? '';
              return CustomTransitionPage(
                child: PreviewPage(recordId: recordId),
                transitionsBuilder: (ctx, animation, secondary, child) => FadeTransition(opacity: animation, child: child),
              );
            },
          ),
          GoRoute(
            path: RouteNames.deviceManage,
            pageBuilder: (_, s) => CustomTransitionPage(
              child: const DeviceManagePage(),
              transitionsBuilder: (ctx, animation, secondary, child) => FadeTransition(opacity: animation, child: child),
            ),
          ),
        ],
      ),
    ],
  );
});

class _AppShell extends StatelessWidget {
  final Widget child;
  const _AppShell({required this.child});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final loc = GoRouterState.of(context).uri.toString();

    return Scaffold(
      body: child,
      bottomNavigationBar: SafeArea(
        child: Container(
          height: 72,
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            boxShadow: [BoxShadow(color: theme.colorScheme.shadow.withValues(alpha: 0.06), blurRadius: 16, offset: const Offset(0, -4))],
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
            _navItem(Icons.home_rounded, Icons.home_outlined, '首页', RouteNames.home, loc, context),
            _navItem(Icons.storage_rounded, Icons.storage_outlined, '存储库', RouteNames.repository, loc, context),
            _navItem(Icons.person_rounded, Icons.person_outlined, '我的', RouteNames.profile, loc, context),
          ]),
        ),
      ),
    );
  }

  Widget _navItem(IconData filled, IconData outlined, String label, String route, String currentLoc, BuildContext context) {
    final isActive = currentLoc == route;
    final color = isActive ? Theme.of(context).colorScheme.primary : Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.45);
    return Semantics(
      button: true, label: label,
      child: InkWell(
        onTap: isActive ? null : () => context.go(route),
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Semantics(label: label, child: Icon(isActive ? filled : outlined, size: 26, color: color)),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: EdgeInsets.only(top: isActive ? 4 : 6),
              child: Text(label, style: TextStyle(fontSize: 10, fontWeight: isActive ? FontWeight.w700 : FontWeight.w500, color: color)),
            ),
          ]),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/router.dart';
import 'package:bountyloop_app/core/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: BountyLoopApp(),
    ),
  );
}

class BountyLoopApp extends ConsumerWidget {
  const BountyLoopApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: router,
      builder: (context, child) {
        // Provide centered mobile frame on desktop/web viewports (>500px)
        return LayoutBuilder(
          builder: (context, constraints) {
            if (constraints.maxWidth > 500) {
              return Scaffold(
                backgroundColor: const Color(0xFFF0EAD8),
                body: Center(
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 440),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.08),
                          blurRadius: 36,
                          offset: const Offset(0, 14),
                        ),
                      ],
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: child ?? const SizedBox.shrink(),
                  ),
                ),
              );
            }
            return child ?? const SizedBox.shrink();
          },
        );
      },
    );
  }
}

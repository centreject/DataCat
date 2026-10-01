import 'package:flutter/material.dart';

import 'app_dimensions.dart';

class ResponsiveContent extends StatelessWidget {
  const ResponsiveContent({
    required this.builder,
    super.key,
  });

  final Widget Function(
    BuildContext context,
    EdgeInsets pagePadding,
  ) builder;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          maxWidth: AppDimensions.contentMaxWidth,
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final horizontalPadding =
                constraints.maxWidth <
                    AppDimensions.compactBreakpoint
                ? AppDimensions.compactPagePadding
                : AppDimensions.regularPagePadding;

            final pagePadding = EdgeInsets.symmetric(
              horizontal: horizontalPadding,
              vertical: AppDimensions.spaceLarge,
            );

            return builder(context, pagePadding);
          },
        ),
      ),
    );
  }
}
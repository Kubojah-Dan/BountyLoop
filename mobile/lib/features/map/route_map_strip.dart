import 'package:flutter/material.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/route_model.dart';

class RouteMapStrip extends StatelessWidget {
  final RouteInfoModel route;
  final String? donorName;
  final String? donorAddress;
  final String? recipientName;
  final String? recipientAddress;
  final VoidCallback? onNavigate;

  const RouteMapStrip({
    super.key,
    required this.route,
    this.donorName,
    this.donorAddress,
    this.recipientName,
    this.recipientAddress,
    this.onNavigate,
  });

  @override
  Widget build(BuildContext context) {
    final isOsrm = route.isOsrm;
    final badgeColor = isOsrm ? AppTheme.successGreen : AppTheme.brandAmber;
    final badgeLabel = isOsrm ? 'OSRM Live Route' : 'Road Estimate';
    final badgeIcon = isOsrm ? Icons.check_circle_outline : Icons.info_outline;

    return Card(
      elevation: 2,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppTheme.cardBorder, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Bar: Distance, Duration, Source Chip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: AppTheme.surfaceLight,
              borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: Row(
              children: [
                const Icon(Icons.directions_car_rounded, color: AppTheme.brandGreen, size: 20),
                const SizedBox(width: 8),
                Text(
                  route.formattedDistance,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                    color: AppTheme.textDark,
                  ),
                ),
                const SizedBox(width: 6),
                const Text('•', style: TextStyle(color: AppTheme.textMuted)),
                const SizedBox(width: 6),
                Text(
                  route.formattedDuration,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                    color: AppTheme.textMuted,
                  ),
                ),
                const Spacer(),
                // Honest Source Indicator Chip
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: badgeColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: badgeColor.withOpacity(0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(badgeIcon, size: 14, color: badgeColor),
                      const SizedBox(width: 4),
                      Text(
                        badgeLabel,
                        style: TextStyle(
                          color: badgeColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Mini Route Polyline Canvas Strip
          SizedBox(
            height: 90,
            child: Container(
              color: const Color(0xFF1B2320),
              child: CustomPaint(
                painter: _RouteTrackPainter(
                  coordinates: route.coordinates,
                  trackColor: isOsrm ? AppTheme.brandGreen : AppTheme.brandAmber,
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Start Marker (Donor)
                      _buildWaypointBadge(
                        label: 'Pickup',
                        name: donorName ?? 'Donor Location',
                        color: AppTheme.brandGreen,
                        icon: Icons.storefront,
                      ),
                      // Arrow indicator
                      Icon(
                        Icons.arrow_forward_rounded,
                        color: Colors.white.withOpacity(0.6),
                        size: 20,
                      ),
                      // Destination Marker (Recipient)
                      _buildWaypointBadge(
                        label: 'Drop-off',
                        name: recipientName ?? 'Recipient Pantry',
                        color: AppTheme.brandAmber,
                        icon: Icons.local_shipping_outlined,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Stop Addresses & Route Details
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (donorAddress != null) ...[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.circle, size: 10, color: AppTheme.brandGreen),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          donorAddress!,
                          style: const TextStyle(fontSize: 13, color: AppTheme.textDark),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                ],
                if (recipientAddress != null) ...[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.location_on, size: 12, color: AppTheme.brandAmber),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          recipientAddress!,
                          style: const TextStyle(fontSize: 13, color: AppTheme.textDark),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                ],

                // Legal OSM Attribution & Navigation Action
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      '© OpenStreetMap contributors',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppTheme.textMuted,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                    if (onNavigate != null)
                      ElevatedButton.icon(
                        onPressed: onNavigate,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.brandGreen,
                          foregroundColor: Colors.white,
                          minimumSize: const Size(110, 36),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                        icon: const Icon(Icons.navigation, size: 14),
                        label: const Text('Start Route'),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWaypointBadge({
    required String label,
    required String name,
    required Color color,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.neutralWhite.withOpacity(0.92),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label.toUpperCase(),
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: color,
                  letterSpacing: 0.5,
                ),
              ),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 100),
                child: Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RouteTrackPainter extends CustomPainter {
  final List<List<double>> coordinates;
  final Color trackColor;

  _RouteTrackPainter({
    required this.coordinates,
    required this.trackColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = trackColor.withOpacity(0.35)
      ..strokeWidth = 3.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final path = Path();
    final startY = size.height * 0.5;
    path.moveTo(30, startY);

    if (coordinates.length >= 2) {
      final stepX = (size.width - 60) / (coordinates.length - 1);
      for (int i = 1; i < coordinates.length; i++) {
        final wave = ((i % 2 == 1) ? 1.0 : -1.0) * 8.0;
        final x = 30 + i * stepX;
        final y = startY + wave;
        path.lineTo(x, y);
      }
    } else {
      path.quadraticBezierTo(size.width * 0.5, startY - 14, size.width - 30, startY);
    }

    canvas.drawPath(path, paint);

    // Start point dot
    final dotPaint = Paint()..color = trackColor;
    canvas.drawCircle(Offset(30, startY), 4, dotPaint);
    // End point dot
    canvas.drawCircle(Offset(size.width - 30, startY), 4, dotPaint);
  }

  @override
  bool shouldRepaint(covariant _RouteTrackPainter oldDelegate) {
    return oldDelegate.trackColor != trackColor ||
        oldDelegate.coordinates.length != coordinates.length;
  }
}

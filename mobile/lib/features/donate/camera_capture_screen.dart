import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/services/donation_service.dart';
import 'package:bountyloop_app/services/location_service.dart';

class CameraCaptureScreen extends ConsumerStatefulWidget {
  const CameraCaptureScreen({super.key});

  @override
  ConsumerState<CameraCaptureScreen> createState() => _CameraCaptureScreenState();
}

class _CameraCaptureScreenState extends ConsumerState<CameraCaptureScreen> {
  final _picker = ImagePicker();
  Uint8List? _customPhotoBytes;
  bool _safetyChecked = false;
  bool _isSubmitting = false;

  // Editable AI details
  String _itemCategory = 'Bakery • mixed pastries';
  double _estWeightKg = 3.0;
  int _freshnessGrade = 2; // 0 to 3
  String _freshnessLabel = '2 / 3 • Good';

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: source,
        maxWidth: 1600,
        imageQuality: 85,
      );
      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _customPhotoBytes = bytes;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not access camera/photo: $e')),
      );
    }
  }

  void _showRetakeModal() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Update food photo',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.camera_alt_outlined, color: AppTheme.brandGreen),
                title: const Text('Take new photo with camera'),
                onTap: () {
                  Navigator.pop(ctx);
                  _pickImage(ImageSource.camera);
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined, color: AppTheme.brandGreen),
                title: const Text('Choose from gallery'),
                onTap: () {
                  Navigator.pop(ctx);
                  _pickImage(ImageSource.gallery);
                },
              ),
              ListTile(
                leading: const Icon(Icons.refresh, color: AppTheme.textMuted),
                title: const Text('Reset to demo pastries'),
                onTap: () {
                  Navigator.pop(ctx);
                  setState(() => _customPhotoBytes = null);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openCorrectionSheet() {
    String tempCategory = _itemCategory;
    double tempWeight = _estWeightKg;
    int tempGrade = _freshnessGrade;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (sheetContext, setSheetState) => Padding(
          padding: EdgeInsets.only(
            left: 24,
            right: 24,
            top: 24,
            bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Correct AI details',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textDark,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: AppTheme.textMuted),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Text(
                'Category',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
              ),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                value: tempCategory,
                decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12)),
                items: const [
                  DropdownMenuItem(value: 'Bakery • mixed pastries', child: Text('Bakery • mixed pastries')),
                  DropdownMenuItem(value: 'Bakery • sourdough loaves', child: Text('Bakery • sourdough loaves')),
                  DropdownMenuItem(value: 'Produce • seasonal vegetables', child: Text('Produce • seasonal vegetables')),
                  DropdownMenuItem(value: 'Prepared • ready meals', child: Text('Prepared • ready meals')),
                ],
                onChanged: (val) {
                  if (val != null) setSheetState(() => tempCategory = val);
                },
              ),
              const SizedBox(height: 16),
              const Text(
                'Freshness Grade',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
              ),
              const SizedBox(height: 6),
              DropdownButtonFormField<int>(
                value: tempGrade,
                decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12)),
                items: const [
                  DropdownMenuItem(value: 3, child: Text('3 / 3 • Fresh (same-day baked)')),
                  DropdownMenuItem(value: 2, child: Text('2 / 3 • Good (fit to share)')),
                  DropdownMenuItem(value: 1, child: Text('1 / 3 • Fair (must consume soon)')),
                  DropdownMenuItem(value: 0, child: Text('0 / 3 • Reject (spoilage detected)')),
                ],
                onChanged: (val) {
                  if (val != null) setSheetState(() => tempGrade = val);
                },
              ),
              const SizedBox(height: 16),
              Text(
                'Estimated weight (${tempWeight.toStringAsFixed(1)} kg)',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
              ),
              Slider(
                value: tempWeight,
                min: 0.5,
                max: 30.0,
                divisions: 59,
                activeColor: AppTheme.brandGreen,
                onChanged: (val) => setSheetState(() => tempWeight = val),
              ),
              const SizedBox(height: 18),
              ElevatedButton(
                onPressed: () {
                  setState(() {
                    _itemCategory = tempCategory;
                    _estWeightKg = tempWeight;
                    _freshnessGrade = tempGrade;
                    _freshnessLabel = tempGrade == 3
                        ? '3 / 3 • Fresh'
                        : tempGrade == 2
                            ? '2 / 3 • Good'
                            : tempGrade == 1
                                ? '1 / 3 • Fair'
                                : '0 / 3 • Reject';
                  });
                  Navigator.pop(ctx);
                },
                child: const Text('Save Changes'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _handleConfirm() async {
    if (!_safetyChecked) return;

    setState(() => _isSubmitting = true);

    try {
      final location = ref.read(locationProvider);
      // Attempt backend donation creation if server active
      final donation = await ref.read(donationServiceProvider).createDonation(
            imageBytesList: _customPhotoBytes != null ? [_customPhotoBytes!] : [],
            fileNames: ['pastries.jpg'],
            estWeightKg: _estWeightKg,
            latitude: location.latitude,
            longitude: location.longitude,
            address: 'Hearth Bakery, 42 Dalston Lane',
          );

      if (!mounted) return;
      context.go('/donate/timeline/${donation.id}');
    } catch (_) {
      // In offline/mock mode, proceed seamlessly with demo BL-2048
      if (!mounted) return;
      context.go('/donate/timeline/BL-2048');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppTheme.textDark),
          onPressed: () => context.go('/donate'),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              'Photo to rescue',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
              ),
            ),
            SizedBox(height: 2),
            Text(
              'NEW DONATION • DRAFT',
              style: TextStyle(
                fontSize: 10,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w600,
                color: AppTheme.textMuted,
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: AppTheme.brandGreenDark,
              child: const Text(
                'HB',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 3-step Stepper Pills
            Row(
              children: [
                _buildStepPill('1 Photo', false, true),
                const SizedBox(width: 8),
                _buildStepPill('2 Review AI', true, false),
                const SizedBox(width: 8),
                _buildStepPill('3 Publish', false, false),
              ],
            ),
            const SizedBox(height: 16),

            // Photo Preview Card
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              clipBehavior: Clip.antiAlias,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  AspectRatio(
                    aspectRatio: 16 / 9,
                    child: _customPhotoBytes != null
                        ? Image.memory(_customPhotoBytes!, fit: BoxFit.cover)
                        : Image.asset(
                            'assets/images/mixed_pastries.jpg',
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              color: const Color(0xFFF0EFEA),
                              child: const Center(
                                child: Icon(Icons.bakery_dining_outlined, size: 48, color: AppTheme.brandGreen),
                              ),
                            ),
                          ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.check_circle, size: 14, color: AppTheme.brandGreen),
                            SizedBox(width: 6),
                            Text(
                              'Photo added • Just now',
                              style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                        InkWell(
                          onTap: _showRetakeModal,
                          child: const Text(
                            'Retake / upload',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.brandGreen,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // AI Assessment Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.auto_awesome, color: AppTheme.brandGreen, size: 18),
                          SizedBox(width: 6),
                          Text(
                            'AI assessment',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.textDark,
                            ),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.brandAmberLight,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFFDE68A)),
                        ),
                        child: const Text(
                          '• Confirm first',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.brandAmber,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),

                  const Text(
                    'ITEM CATEGORY',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                      color: AppTheme.textMuted,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _itemCategory,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textDark,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Suggested quantity: 24 items • about ${_estWeightKg.toStringAsFixed(1)} kg',
                    style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                  ),
                  const SizedBox(height: 16),

                  // Freshness grade & 4-step meter
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Freshness grade',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textDark),
                      ),
                      Text(
                        _freshnessLabel,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.brandGreen,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // 4 segments meter
                  Row(
                    children: [
                      for (int i = 0; i < 4; i++) ...[
                        Expanded(
                          child: Container(
                            height: 6,
                            decoration: BoxDecoration(
                              color: i <= _freshnessGrade ? AppTheme.brandGreen : const Color(0xFFE2E8F0),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                        ),
                        if (i < 3) const SizedBox(width: 4),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('0 - Reject', style: TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                      Text('3 - Fresh', style: TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Hazard Gate Warning Callout
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.brandAmberLight,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFFDE68A)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Row(
                          children: [
                            Icon(Icons.warning_amber_rounded, size: 16, color: Color(0xFFC2410C)),
                            SizedBox(width: 6),
                            Text(
                              'HAZARD GATE - DONOR CHECK REQUIRED',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.5,
                                color: Color(0xFFC2410C),
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 4),
                        Text(
                          'No visible hazard detected. A photo cannot verify storage, allergens or food safety.',
                          style: TextStyle(
                            fontSize: 12,
                            height: 1.4,
                            color: Color(0xFF78350F),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Safety Checkbox
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 24,
                  height: 24,
                  child: Checkbox(
                    value: _safetyChecked,
                    activeColor: AppTheme.brandGreen,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                    onChanged: (val) => setState(() => _safetyChecked = val ?? false),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => _safetyChecked = !_safetyChecked),
                    child: const Text(
                      'I\'ve checked freshness, safe storage and allergen information. This food is fit to share.',
                      style: TextStyle(
                        fontSize: 13,
                        height: 1.4,
                        color: AppTheme.textDark,
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Primary Button: Confirm assessment
            ElevatedButton(
              onPressed: (_safetyChecked && !_isSubmitting) ? _handleConfirm : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.brandGreen,
                disabledBackgroundColor: AppTheme.brandGreen.withOpacity(0.35),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: _isSubmitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.lock_outline, size: 18),
                        SizedBox(width: 8),
                        Text('Confirm assessment'),
                      ],
                    ),
            ),
            const SizedBox(height: 10),

            // Secondary Button: Correct AI details
            OutlinedButton(
              onPressed: _openCorrectionSheet,
              style: OutlinedButton.styleFrom(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.edit_outlined, size: 18),
                  SizedBox(width: 8),
                  Text('Correct AI details'),
                ],
              ),
            ),
            const SizedBox(height: 12),

            const Text(
              'Tick the safety check to enable confirmation. Nothing is published yet. Unsafe food must not be listed.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.4),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 1,
        selectedItemColor: AppTheme.brandGreen,
        unselectedItemColor: AppTheme.textMuted,
        backgroundColor: Colors.white,
        onTap: (idx) {
          if (idx == 0) context.go('/donate');
          if (idx == 1) context.go('/donate/camera');
          if (idx == 2) context.go('/profile');
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_outlined), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.camera_alt_outlined), label: 'Donate'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }

  Widget _buildStepPill(String label, bool isActive, bool isDone) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 7),
        decoration: BoxDecoration(
          color: isActive
              ? AppTheme.brandGreenDark
              : isDone
                  ? AppTheme.brandGreenLight
                  : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isActive
                ? AppTheme.brandGreenDark
                : isDone
                    ? AppTheme.brandGreenLight
                    : AppTheme.cardBorder,
          ),
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: isActive
                ? Colors.white
                : isDone
                    ? AppTheme.brandGreen
                    : AppTheme.textMuted,
          ),
        ),
      ),
    );
  }
}

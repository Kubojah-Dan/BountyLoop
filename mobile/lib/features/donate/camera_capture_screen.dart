import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/donate/donation_confirm_screen.dart';
import 'package:bountyloop_app/services/donation_service.dart';
import 'package:bountyloop_app/services/location_service.dart';

class CameraCaptureScreen extends ConsumerStatefulWidget {
  const CameraCaptureScreen({super.key});

  @override
  ConsumerState<CameraCaptureScreen> createState() => _CameraCaptureScreenState();
}

class _CameraCaptureScreenState extends ConsumerState<CameraCaptureScreen> {
  final _picker = ImagePicker();
  final _weightController = TextEditingController(text: '3.5');
  final _addressController = TextEditingController(text: '200 E 6th St, Austin, TX');

  Uint8List? _selectedImageBytes;
  String _fileName = 'donation_photo.jpg';
  bool _isUploading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _weightController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: source,
        maxWidth: 1600, // Respect bandwidth constraint (§Master Plan)
        imageQuality: 85,
      );
      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _selectedImageBytes = bytes;
          _fileName = file.name;
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = 'Failed to capture photo: $e');
    }
  }

  void _useSamplePhoto() {
    // Generate valid 100x100 dummy JPEG bytes for tests or desktop emulator
    final sampleBytes = _createSampleJpegBytes();
    setState(() {
      _selectedImageBytes = sampleBytes;
      _fileName = 'sample_apples.jpg';
      _errorMessage = null;
    });
  }

  Uint8List _createSampleJpegBytes() {
    // Minimal valid JPEG header bytes for quick mock/test photo
    return Uint8List.fromList([
      0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
      0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
      0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
      0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
      0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
      0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
      0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
      0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x0A,
      0x00, 0x0A, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
      0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
      0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
      0x00, 0x3F, 0xFF, 0xD9,
    ]);
  }

  Future<void> _handleUpload() async {
    if (_selectedImageBytes == null) {
      setState(() => _errorMessage = 'Please take or pick a photo of the food surplus.');
      return;
    }

    final weight = double.tryParse(_weightController.text.trim()) ?? 2.5;
    final address = _addressController.text.trim();
    final location = ref.read(locationProvider);

    setState(() {
      _isUploading = true;
      _errorMessage = null;
    });

    try {
      final donation = await ref.read(donationServiceProvider).createDonation(
            imageBytesList: [_selectedImageBytes!],
            fileNames: [_fileName],
            estWeightKg: weight,
            latitude: location.latitude,
            longitude: location.longitude,
            address: address.isNotEmpty ? address : location.label,
          );

      if (!mounted) return;
      setState(() => _isUploading = false);

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => DonationConfirmScreen(initialDonation: donation),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isUploading = false;
        _errorMessage = 'Upload failed: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Donate Surplus Food'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Photo viewfinder / preview card
            Container(
              height: 220,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.cardBorder, width: 2),
              ),
              child: _selectedImageBytes != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          Image.memory(_selectedImageBytes!, fit: BoxFit.cover),
                          Positioned(
                            top: 8,
                            right: 8,
                            child: IconButton(
                              icon: const Icon(Icons.refresh, color: Colors.white),
                              style: IconButton.styleFrom(backgroundColor: Colors.black54),
                              onPressed: () => setState(() => _selectedImageBytes = null),
                            ),
                          ),
                        ],
                      ),
                    )
                  : Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.add_a_photo_outlined,
                            size: 48,
                            color: AppTheme.brandGreen.withOpacity(0.6),
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'Take or Upload Food Photo',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textDark,
                            ),
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'AI will automatically identify item & freshness',
                            style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                    ),
            ),
            const SizedBox(height: 14),

            // Capture / Gallery action buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isUploading ? null : () => _pickImage(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt, size: 20),
                    label: const Text('Camera'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isUploading ? null : () => _pickImage(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library_outlined, size: 20),
                    label: const Text('Gallery'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Center(
              child: TextButton.icon(
                onPressed: _isUploading ? null : _useSamplePhoto,
                icon: const Icon(Icons.auto_fix_high, size: 16),
                label: const Text('Or use demo sample photo'),
                style: TextButton.styleFrom(foregroundColor: AppTheme.brandAmber),
              ),
            ),
            const SizedBox(height: 16),

            // Weight input
            TextField(
              controller: _weightController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Estimated Weight (kg)',
                prefixIcon: Icon(Icons.scale_outlined, color: AppTheme.textMuted),
                suffixText: 'kg',
              ),
            ),
            const SizedBox(height: 14),

            // Pickup Address
            TextField(
              controller: _addressController,
              decoration: const InputDecoration(
                labelText: 'Pickup Address / Location',
                prefixIcon: Icon(Icons.location_on_outlined, color: AppTheme.textMuted),
              ),
            ),

            if (_errorMessage != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.dangerRed.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(color: AppTheme.dangerRed, fontSize: 13),
                ),
              ),
            ],
            const SizedBox(height: 24),

            // Upload & Analyze CTA
            ElevatedButton(
              onPressed: _isUploading ? null : _handleUpload,
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.brandGreen),
              child: _isUploading
                  ? const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                        ),
                        SizedBox(width: 12),
                        Text('Analyzing with Computer Vision...'),
                      ],
                    )
                  : const Text('Analyze with AI & Review'),
            ),
          ],
        ),
      ),
    );
  }
}

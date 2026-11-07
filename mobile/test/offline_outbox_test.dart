import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/core/offline/outbox_manager.dart';

void main() {
  group('Offline Outbox & Synchronization Tests (Phase 12)', () {
    late OutboxManager outbox;

    setUp(() {
      outbox = OutboxManager();
    });

    test('Airplane mode: enqueue offline donation creates pending item with idempotency key', () {
      final item = outbox.enqueueDonation(
        photoPath: '/cache/local_photo_1.jpg',
        fileName: 'local_photo_1.jpg',
        estWeightKg: 14.5,
        latitude: 30.2672,
        longitude: -97.7431,
        address: '100 Congress Ave, Austin, TX',
      );

      expect(item.idempotencyKey, isNotEmpty);
      expect(item.status, equals(OutboxStatus.pendingUpload));
      expect(item.estWeightKg, equals(14.5));
      expect(outbox.pendingCount, equals(1));
    });

    test('Idempotency key prevents duplicate enqueueing', () {
      const fixedKey = 'idemp_key_unique_123';

      final item1 = outbox.enqueueDonation(
        photoPath: '/cache/p1.jpg',
        fileName: 'p1.jpg',
        idempotencyKey: fixedKey,
        estWeightKg: 10.0,
      );

      final item2 = outbox.enqueueDonation(
        photoPath: '/cache/p1.jpg',
        fileName: 'p1.jpg',
        idempotencyKey: fixedKey,
        estWeightKg: 10.0,
      );

      expect(outbox.pendingCount, equals(1));
      expect(item1.idempotencyKey, equals(item2.idempotencyKey));
    });

    test('Reconnect flush successfully transitions pending items to synced', () async {
      outbox.enqueueDonation(
        photoPath: '/cache/p1.jpg',
        fileName: 'p1.jpg',
        estWeightKg: 8.0,
      );
      outbox.enqueueDonation(
        photoPath: '/cache/p2.jpg',
        fileName: 'p2.jpg',
        estWeightKg: 12.0,
      );

      expect(outbox.pendingCount, equals(2));

      // Simulate network reconnect and successful upload
      final summary = await outbox.flushPending(
        uploadCallback: (item) async {
          expect(item.idempotencyKey, isNotEmpty);
          return true; // Server responds 201 Created
        },
      );

      expect(summary.synced, equals(2));
      expect(summary.failed, equals(0));
      expect(summary.remaining, equals(0));
      expect(outbox.pendingCount, equals(0));
    });

    test('Exponential backoff retry increments on server error', () async {
      final item = outbox.enqueueDonation(
        photoPath: '/cache/p1.jpg',
        fileName: 'p1.jpg',
        estWeightKg: 5.0,
      );

      expect(item.retryCount, equals(0));

      // First failed attempt
      await outbox.flushPending(uploadCallback: (it) async => false);
      expect(item.retryCount, equals(1));
      expect(item.status, equals(OutboxStatus.pendingUpload));
      expect(outbox.pendingCount, equals(1));

      // Second attempt succeeds
      await outbox.flushPending(uploadCallback: (it) async => true);
      expect(item.status, equals(OutboxStatus.synced));
      expect(outbox.pendingCount, equals(0));
    });

    test('Serialization and deserialization across app lifecycle', () {
      outbox.enqueueDonation(
        photoPath: '/cache/stored.jpg',
        fileName: 'stored.jpg',
        idempotencyKey: 'persist_token_456',
        estWeightKg: 20.0,
      );

      final jsonString = outbox.serialize();
      expect(jsonString, contains('persist_token_456'));

      final restoredOutbox = OutboxManager();
      restoredOutbox.deserialize(jsonString);

      expect(restoredOutbox.pendingCount, equals(1));
      expect(restoredOutbox.pendingItems.first.idempotencyKey, equals('persist_token_456'));
      expect(restoredOutbox.pendingItems.first.estWeightKg, equals(20.0));
    });
  });
}


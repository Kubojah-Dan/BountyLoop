class UserModel {
  final String id;
  final String email;
  final String displayName;
  final String role; // 'donor', 'recipient', 'volunteer', 'admin'
  final String? orgName;
  final String? phone;

  const UserModel({
    required this.id,
    required this.email,
    required this.displayName,
    required this.role,
    this.orgName,
    this.phone,
  });

  bool get isDonor => role == 'donor';
  bool get isRecipient => role == 'recipient';
  bool get isVolunteer => role == 'volunteer';
  bool get isAdmin => role == 'admin';

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      displayName: json['display_name']?.toString() ?? json['email']?.toString() ?? 'User',
      role: json['role']?.toString() ?? 'donor',
      orgName: json['org_name']?.toString(),
      phone: json['phone_e164']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'display_name': displayName,
      'role': role,
      'org_name': orgName,
      'phone_e164': phone,
    };
  }
}

class EditableDeviceInfo {
  const EditableDeviceInfo({
    required this.heightCm,
    required this.weightKg,
    required this.address,
    required this.phoneNumber,
  });

  final int heightCm;
  final int weightKg;
  final String address;
  final String phoneNumber;

  EditableDeviceInfo copyWith({
    int? heightCm,
    int? weightKg,
    String? address,
    String? phoneNumber,
  }) {
    return EditableDeviceInfo(
      heightCm: heightCm ?? this.heightCm,
      weightKg: weightKg ?? this.weightKg,
      address: address ?? this.address,
      phoneNumber: phoneNumber ?? this.phoneNumber,
    );
  }
}

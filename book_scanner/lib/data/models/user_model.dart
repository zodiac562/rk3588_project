class UserModel {
  final String id;
  final String username;
  final String email;
  final String? avatar;
  final String? bio;

  const UserModel({
    required this.id,
    required this.username,
    required this.email,
    this.avatar,
    this.bio,
  });

  UserModel copyWith({
    String? id,
    String? username,
    String? email,
    String? avatar,
    String? bio,
  }) {
    return UserModel(
      id: id ?? this.id,
      username: username ?? this.username,
      email: email ?? this.email,
      avatar: avatar ?? this.avatar,
      bio: bio ?? this.bio,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'email': email,
        'avatar': avatar,
        'bio': bio,
      };

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] ?? '',
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      avatar: json['avatar'],
      bio: json['bio'],
    );
  }
}

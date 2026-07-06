class BrailleRecord {
  final String id;
  final String title;
  final String sourceType;
  final int dotMatrixWidth;
  final int dotMatrixHeight;
  final List<List<int>> dotMatrixData;
  final String? textContent;
  final DateTime createdAt;
  final int pageCount;

  const BrailleRecord({
    required this.id,
    required this.title,
    required this.sourceType,
    required this.dotMatrixWidth,
    required this.dotMatrixHeight,
    required this.dotMatrixData,
    required this.createdAt,
    this.textContent,
    this.pageCount = 1,
  });

  BrailleRecord copyWith({
    String? id,
    String? title,
    String? sourceType,
    int? dotMatrixWidth,
    int? dotMatrixHeight,
    List<List<int>>? dotMatrixData,
    String? textContent,
    DateTime? createdAt,
    int? pageCount,
  }) {
    return BrailleRecord(
      id: id ?? this.id,
      title: title ?? this.title,
      sourceType: sourceType ?? this.sourceType,
      dotMatrixWidth: dotMatrixWidth ?? this.dotMatrixWidth,
      dotMatrixHeight: dotMatrixHeight ?? this.dotMatrixHeight,
      dotMatrixData: dotMatrixData ?? this.dotMatrixData,
      textContent: textContent ?? this.textContent,
      createdAt: createdAt ?? this.createdAt,
      pageCount: pageCount ?? this.pageCount,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'source_type': sourceType,
        'dot_matrix_width': dotMatrixWidth,
        'dot_matrix_height': dotMatrixHeight,
        'dot_matrix_data': dotMatrixData,
        'text_content': textContent,
        'created_at': createdAt.toIso8601String(),
        'page_count': pageCount,
      };

  factory BrailleRecord.fromJson(Map<String, dynamic> json) {
    return BrailleRecord(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      sourceType: json['source_type'] ?? '',
      dotMatrixWidth: json['dot_matrix_width'] ?? 0,
      dotMatrixHeight: json['dot_matrix_height'] ?? 0,
      dotMatrixData: (json['dot_matrix_data'] as List?)?.map((r) => List<int>.from(r)).toList() ?? [],
      textContent: json['text_content'],
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      pageCount: json['page_count'] ?? 1,
    );
  }
}

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/braille_record.dart';
import '../../../data/local_db/database_helper.dart';

class RepoState {
  final List<BrailleRecord> records;
  final String searchQuery;

  const RepoState({this.records = const [], this.searchQuery = ''});

  RepoState copyWith({List<BrailleRecord>? records, String? searchQuery}) {
    return RepoState(
      records: records ?? this.records,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class RepoNotifier extends StateNotifier<RepoState> {
  final DatabaseHelper _db = DatabaseHelper();

  RepoNotifier() : super(const RepoState()) {
    _seedIfEmpty();
    loadRecords();
    _db.addListener(() => loadRecords());
  }

  void _seedIfEmpty() {
    if (_db.getRecords().isNotEmpty) return;

    final now = DateTime.now();
    _db.addRecord(BrailleRecord(
      id: 'seed_001',
      title: '第四章 黎族船形屋文化源流与建筑特色',
      sourceType: '现场扫描',
      dotMatrixWidth: 40,
      dotMatrixHeight: 30,
      dotMatrixData: List.generate(30, (_) => List.filled(40, 0)),
      createdAt: now,
      pageCount: 4,
      textContent: '第四章 黎族船形屋文化源流与建筑特色'
          '海南岛的地形特点是中高四周低，形成了山地丘陵、台地和沿海平原等梯级。'
          '黎族主要聚居在海南岛的中南部，这里纬度低，雨量丰，阳光足，长夏而无冬，'
          '秋春相连，四季不分明。黎族村落就散落在海南岛中南部的丘陵、盆地、峡谷和一些滨海平原上。'
          '几千年的历史发展，孕育出了黎族丰富多彩的民族文化。'
          '黎族传统建筑的船形屋则是极具特色之一。',
    ));
  }

  Future<void> loadRecords({String? search}) async {
    final records = _db.getRecords(search: search);
    state = state.copyWith(records: records, searchQuery: search);
  }

  Future<void> refreshRecords() async {
    final records = _db.getRecords(search: state.searchQuery);
    state = state.copyWith(records: records);
  }

  Future<void> deleteRecord(String id) async {
    _db.deleteRecord(id);
    loadRecords(search: state.searchQuery);
  }

  Future<void> renameRecord(String id, String newTitle) async {
    _db.renameRecord(id, newTitle);
    loadRecords(search: state.searchQuery);
  }

  Future<BrailleRecord?> getRecord(String id) async {
    return _db.getRecordById(id);
  }
}

final repoProvider = StateNotifierProvider<RepoNotifier, RepoState>((ref) => RepoNotifier());

import '../models/braille_record.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._();
  factory DatabaseHelper() => _instance;
  DatabaseHelper._();

  final List<BrailleRecord> _records = [];
  final List<void Function()> _listeners = [];

  void addListener(void Function() cb) => _listeners.add(cb);
  void removeListener(void Function() cb) => _listeners.remove(cb);
  void _notify() { for (final l in _listeners) { l(); } }

  List<BrailleRecord> getRecords({String? search, bool orderByDate = true}) {
    var list = List<BrailleRecord>.from(_records);
    if (search != null && search.isNotEmpty) {
      list = list.where((r) => r.title.toLowerCase().contains(search.toLowerCase())).toList();
    }
    if (orderByDate) {
      list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    }
    return list;
  }

  void addRecord(BrailleRecord record) {
    _records.add(record);
    _notify();
  }

  void deleteRecord(String id) {
    _records.removeWhere((r) => r.id == id);
    _notify();
  }

  void renameRecord(String id, String newTitle) {
    final idx = _records.indexWhere((r) => r.id == id);
    if (idx != -1) {
      _records[idx] = _records[idx].copyWith(title: newTitle);
      _notify();
    }
  }

  BrailleRecord? getRecordById(String id) {
    try {
      return _records.firstWhere((r) => r.id == id);
    } catch (_) {
      return null;
    }
  }
}

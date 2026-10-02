import 'package:flutter/foundation.dart';

import '../data/api.dart';
import '../data/models.dart';

/// 방문 기록 목록. 홈과 기록 화면이 같은 목록을 함께 본다.
///
/// 서버 연결이 바뀌면 [replaceApi]로 처음부터 다시 불러온다.
/// 늦게 도착한 이전 연결의 응답은 [_generation]으로 걸러낸다.
class EventStore extends ChangeNotifier {
  EventStore(this._api);

  static const pageSize = 20;

  DataCatApi _api;
  final List<VisitEvent> _events = [];
  bool _loading = false;
  bool _loadingMore = false;
  bool _hasMore = true;
  int _nextPage = 0;
  int _generation = 0;
  ApiException? _error;
  ApiException? _moreError;
  DateTime? _lastSync;

  DataCatApi get api => _api;
  List<VisitEvent> get events => List.unmodifiable(_events);
  bool get loading => _loading;
  bool get loadingMore => _loadingMore;
  bool get hasMore => _hasMore;
  ApiException? get error => _error;
  ApiException? get moreError => _moreError;
  DateTime? get lastSync => _lastSync;

  /// 아직 한 번도 불러오지 못했고 지금 불러오는 중
  bool get isFirstLoad => _loading && _events.isEmpty;

  void replaceApi(DataCatApi api) {
    _api = api;
    _events.clear();
    _hasMore = true;
    _nextPage = 0;
    _error = null;
    _moreError = null;
    _lastSync = null;
    refresh();
  }

  Future<void> refresh() async {
    final gen = ++_generation;
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final page = await _api.fetchEvents(page: 0, size: pageSize);
      if (gen != _generation) return;
      _events
        ..clear()
        ..addAll(page.content);
      _sort();
      _hasMore = page.hasMore;
      _nextPage = 1;
      _moreError = null;
      _lastSync = DateTime.now();
    } on ApiException catch (e) {
      if (gen == _generation) _error = e;
    } catch (e) {
      if (gen == _generation) {
        _error = ApiException('기록을 불러오지 못했어요.', detail: '$e');
      }
    } finally {
      if (gen == _generation) {
        _loading = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadMore() async {
    if (_loading || _loadingMore || !_hasMore) return;
    final gen = _generation;
    _loadingMore = true;
    _moreError = null;
    notifyListeners();
    try {
      final page = await _api.fetchEvents(page: _nextPage, size: pageSize);
      if (gen != _generation) return;
      // 새 방문이 생기면 페이지가 밀려 같은 기록이 다시 올 수 있다.
      final known = {for (final e in _events) e.eventId};
      _events.addAll(page.content.where((e) => !known.contains(e.eventId)));
      _sort();
      _hasMore = page.hasMore;
      _nextPage++;
    } on ApiException catch (e) {
      if (gen == _generation) _moreError = e;
    } catch (e) {
      if (gen == _generation) {
        _moreError = ApiException('더 불러오지 못했어요.', detail: '$e');
      }
    } finally {
      if (gen == _generation) {
        _loadingMore = false;
        notifyListeners();
      }
    }
  }

  /// 상세 화면에서 받은 최신 내용으로 목록 항목을 바꾼다.
  void upsert(VisitEvent event) {
    final i = _events.indexWhere((e) => e.eventId == event.eventId);
    if (i == -1) {
      _events.add(event);
      _sort();
    } else if (_events[i] == event) {
      return;
    } else {
      _events[i] = event;
    }
    notifyListeners();
  }

  void _sort() => _events.sort((a, b) => b.occurredAt.compareTo(a.occurredAt));
}

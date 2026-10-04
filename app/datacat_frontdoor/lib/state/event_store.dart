import 'dart:async';

import 'package:flutter/foundation.dart';

import '../data/api.dart';
import '../data/models.dart';

/// 방문 기록 목록. 홈과 기록 화면이 같은 목록을 함께 본다.
///
/// - 서버 연결이 바뀌면 [replaceApi]로 처음부터 다시 불러온다.
/// - [startPolling] 중에는 일정 간격으로 첫 페이지를 조용히 다시 받아
///   새 방문을 목록 맨 위에 끼워 넣고 [unseenIds]에 표시한다.
/// - 늦게 도착한 이전 연결의 응답은 [_generation]으로 걸러낸다.
class EventStore extends ChangeNotifier {
  EventStore(this._api);

  static const pageSize = 20;
  static const pollInterval = Duration(seconds: 15);

  DataCatApi _api;
  final List<VisitEvent> _events = [];
  final Set<int> _unseen = {};
  bool _loading = false;
  bool _loadingMore = false;
  bool _checking = false;
  bool _hasMore = true;
  int _nextPage = 0;
  int _generation = 0;
  ApiException? _error;
  ApiException? _moreError;
  DateTime? _lastSync;
  Timer? _timer;
  bool _disposed = false;

  /// 새 방문이 들어왔을 때 알림 배너를 띄울지 판단하는 함수 (정책 반영)
  bool Function(VisitEvent)? arrivalFilter;

  DataCatApi get api => _api;
  List<VisitEvent> get events => List.unmodifiable(_events);
  bool get loading => _loading;
  bool get loadingMore => _loadingMore;
  bool get hasMore => _hasMore;
  ApiException? get error => _error;
  ApiException? get moreError => _moreError;
  DateTime? get lastSync => _lastSync;
  bool get isPolling => _timer != null;

  /// 아직 열어 보지 않은 새 방문
  Set<int> get unseenIds => Set.unmodifiable(_unseen);
  bool isUnseen(int eventId) => _unseen.contains(eventId);

  /// 배너에 띄울 새 방문 (정책에서 알림을 끈 분류는 뺀다)
  List<VisitEvent> get unseenAlerts => [
        for (final e in _events)
          if (_unseen.contains(e.eventId) && (arrivalFilter?.call(e) ?? true)) e,
      ];

  /// 아직 한 번도 불러오지 못했고 지금 불러오는 중
  bool get isFirstLoad => _loading && _events.isEmpty;

  void replaceApi(DataCatApi api) {
    _api = api;
    _events.clear();
    _unseen.clear();
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
    _notify();
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
        _notify();
      }
    }
  }

  Future<void> loadMore() async {
    if (_loading || _loadingMore || !_hasMore) return;
    final gen = _generation;
    _loadingMore = true;
    _moreError = null;
    _notify();
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
        _notify();
      }
    }
  }

  // ── 자동 새로고침 ──────────────────────────────────────────

  void startPolling([Duration interval = pollInterval]) {
    _timer?.cancel();
    _timer = Timer.periodic(interval, (_) => checkForNew());
  }

  void stopPolling() {
    _timer?.cancel();
    _timer = null;
  }

  /// 첫 페이지를 조용히 다시 받아 새 방문은 위에 넣고, 상태가 바뀐 방문은 갈아 끼운다.
  /// 로딩 표시는 하지 않는다.
  Future<void> checkForNew() async {
    if (_loading || _checking) return;
    if (_events.isEmpty) {
      await refresh(); // 아직 한 번도 못 불러왔으면 일반 새로고침
      return;
    }
    final gen = _generation;
    _checking = true;
    try {
      final page = await _api.fetchEvents(page: 0, size: pageSize);
      if (gen != _generation) return;
      final index = {for (var i = 0; i < _events.length; i++) _events[i].eventId: i};
      var added = false;
      for (final e in page.content) {
        final i = index[e.eventId];
        if (i == null) {
          _events.add(e);
          _unseen.add(e.eventId);
          added = true;
        } else if (_events[i].status != e.status || _events[i].summary != e.summary) {
          // 예: 음성 대기(WAITING_AUDIO) → 접수 완료로 바뀐 경우
          _events[i] = e;
        }
      }
      if (added) _sort();
      _error = null;
      _lastSync = DateTime.now();
      _notify();
    } on ApiException catch (e) {
      if (gen == _generation) {
        _error = e;
        _notify();
      }
    } catch (_) {
      // 일시적인 오류는 다음 주기에 다시 시도한다
    } finally {
      _checking = false;
    }
  }

  void markSeen(int eventId) {
    if (_unseen.remove(eventId)) _notify();
  }

  void markAllSeen() {
    if (_unseen.isEmpty) return;
    _unseen.clear();
    _notify();
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
    _notify();
  }

  void _sort() => _events.sort((a, b) => b.occurredAt.compareTo(a.occurredAt));

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    stopPolling();
    super.dispose();
  }
}

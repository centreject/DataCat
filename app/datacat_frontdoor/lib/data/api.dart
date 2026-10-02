import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

/// 앱이 서버에 기대하는 기능. 실제 서버([HttpDataCatApi])와
/// 데모 데이터([DemoDataCatApi])가 같은 계약을 따른다.
abstract interface class DataCatApi {
  /// 화면에 보여줄 연결 대상 이름 (예: 192.168.0.12:8080, 데모)
  String get label;
  bool get isDemo;

  Future<EventPage> fetchEvents({int page = 0, int size = 20});
  Future<VisitEvent> fetchEvent(int eventId);
  Future<List<Preset>> fetchPresets();

  /// 스냅샷 이미지 주소. null이면 앱이 현관 그림으로 대신 표시한다.
  Uri? snapshotUri(VisitEvent event);
}

class ApiException implements Exception {
  const ApiException(this.message, {this.code, this.statusCode, this.detail});

  /// 사용자에게 그대로 보여줄 수 있는 문장
  final String message;

  /// 서버 오류 코드 (API 12장) 또는 앱 내부 코드 (TIMEOUT, NETWORK …)
  final String? code;
  final int? statusCode;

  /// 디버깅용 원문
  final String? detail;

  bool get isOffline => code == 'TIMEOUT' || code == 'NETWORK';

  factory ApiException.fromResponse(int status, String body) {
    String? code;
    String? serverMessage;
    try {
      final json = jsonDecode(body);
      if (json is Map<String, dynamic>) {
        code = json['code']?.toString();
        serverMessage = json['message']?.toString();
      }
    } on FormatException {
      // HTML 오류 페이지 등. 아래 기본 문장을 쓴다.
    }
    final fallback = switch (status) {
      404 => '기록을 찾을 수 없어요.',
      409 => '지금 상태에서는 처리할 수 없는 요청이에요.',
      503 => '분석 서버를 지금 사용할 수 없어요.',
      >= 500 => '서버에서 오류가 났어요.',
      _ => '요청을 처리하지 못했어요.',
    };
    return ApiException(
      serverMessage ?? fallback,
      code: code,
      statusCode: status,
      detail: 'HTTP $status',
    );
  }

  @override
  String toString() => 'ApiException($code, $statusCode): $message';
}

class HttpDataCatApi implements DataCatApi {
  HttpDataCatApi(
    String baseUrl, {
    http.Client? client,
    this.timeout = const Duration(seconds: 8),
  })  : origin = normalizeBaseUrl(baseUrl),
        _client = client ?? http.Client();

  /// `/api/v1` 앞까지의 서버 주소 (예: http://192.168.0.12:8080)
  final Uri origin;
  final Duration timeout;
  final http.Client _client;

  /// 사용자가 `192.168.0.12:8080`, `http://host/`, `https://api.x.com/api/v1`
  /// 어느 형태로 입력해도 같은 서버 주소로 맞춘다.
  static Uri normalizeBaseUrl(String raw) {
    var s = raw.trim();
    if (!s.contains('://')) s = 'http://$s';
    s = s.replaceFirst(RegExp(r'/+$'), '');
    if (s.endsWith('/api/v1')) s = s.substring(0, s.length - '/api/v1'.length);
    return Uri.parse(s);
  }

  @override
  String get label =>
      origin.hasPort ? '${origin.host}:${origin.port}' : origin.host;

  @override
  bool get isDemo => false;

  @override
  Future<EventPage> fetchEvents({int page = 0, int size = 20}) async {
    final json = await _getJson(
      '/api/v1/events',
      query: {'page': '$page', 'size': '$size'},
    );
    return EventPage.fromJson(json, requestedSize: size);
  }

  @override
  Future<VisitEvent> fetchEvent(int eventId) async {
    final json = await _getJson('/api/v1/events/$eventId');
    if (json is! Map<String, dynamic>) {
      throw const ApiException('서버 응답 형식이 올바르지 않아요.', code: 'BAD_RESPONSE');
    }
    return VisitEvent.fromJson(json);
  }

  @override
  Future<List<Preset>> fetchPresets() async {
    final json = await _getJson('/api/v1/presets');
    return json is List
        ? json.whereType<Map<String, dynamic>>().map(Preset.fromJson).toList()
        : const [];
  }

  @override
  Uri? snapshotUri(VisitEvent event) {
    final raw = event.snapshotUrl;
    if (raw == null || raw.isEmpty) return null;
    final uri = Uri.tryParse(raw);
    if (uri == null) return null;
    return uri.hasScheme ? uri : origin.resolveUri(uri);
  }

  Future<Object?> _getJson(String path, {Map<String, String>? query}) async {
    final uri = origin.replace(
      path: '${origin.path}$path',
      queryParameters: query,
    );

    final http.Response res;
    try {
      res = await _client
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(timeout);
    } on TimeoutException {
      throw const ApiException(
        '서버 응답이 늦어요. 주소와 네트워크를 확인해 주세요.',
        code: 'TIMEOUT',
      );
    } on http.ClientException catch (e) {
      throw ApiException('서버에 연결할 수 없어요.', code: 'NETWORK', detail: e.message);
    } on Exception catch (e) {
      throw ApiException('서버에 연결할 수 없어요.', code: 'NETWORK', detail: '$e');
    }

    // 한글이 깨지지 않도록 바이트에서 직접 UTF-8로 읽는다.
    final body = utf8.decode(res.bodyBytes, allowMalformed: true);
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException.fromResponse(res.statusCode, body);
    }
    if (body.isEmpty) return null;
    try {
      return jsonDecode(body);
    } on FormatException {
      throw const ApiException('서버 응답을 읽을 수 없어요.', code: 'BAD_RESPONSE');
    }
  }
}

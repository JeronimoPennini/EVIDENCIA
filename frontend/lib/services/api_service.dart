/// EvidencIA — Servicio API
/// Centraliza todas las llamadas HTTP al backend FastAPI.
/// Las claves API nunca pasan por aquí; son manejadas exclusivamente por el backend.
library;

import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/article.dart';
import '../models/synthesis_result.dart';

class ApiService {
  final Dio _dio;

  ApiService()
      : _dio = Dio(
          BaseOptions(
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 60),
            headers: {'Content-Type': 'application/json'},
          ),
        );

  /// Busca artículos en PubMed vía el backend.
  Future<SearchResponse> buscarArticulos({
    required String query,
    int maxResults = 10,
    String? dateFrom,
    String? dateTo,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiConfig.searchEndpoint,
        data: {
          'query': query,
          'max_results': maxResults,
          if (dateFrom != null) 'date_from': dateFrom,
          if (dateTo != null) 'date_to': dateTo,
        },
      );
      return SearchResponse.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Busca artículos en PubMed a partir de una pregunta estructurada PICO.
  Future<SearchResponse> buscarArticulosPico({
    required String poblacion,
    required String intervencion,
    String? comparacion,
    required String outcome,
    String filtroEstudio = 'all',
    int maxResults = 10,
    String? dateFrom,
    String? dateTo,
    bool optimizarConIa = true,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiConfig.searchPicoEndpoint,
        data: {
          'poblacion': poblacion,
          'intervencion': intervencion,
          'comparacion': comparacion ?? '',
          'outcome': outcome,
          'filtro_estudio': filtroEstudio,
          'max_results': maxResults,
          if (dateFrom != null) 'date_from': dateFrom,
          if (dateTo != null) 'date_to': dateTo,
          'optimizar_con_ia': optimizarConIa,
        },
      );
      return SearchResponse.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Solicita síntesis de evidencia al motor IA via el backend.
  Future<SynthesisResult> sintetizarEvidencia({
    required List<String> pmids,
    required String preguntaClinica,
    String idiomaRespuesta = 'es',
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiConfig.synthesizeEndpoint,
        data: {
          'pmids': pmids,
          'pregunta_clinica': preguntaClinica,
          'idioma_respuesta': idiomaRespuesta,
        },
      );
      return SynthesisResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Convierte errores de Dio en mensajes legibles.
  Exception _handleError(DioException e) {
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.connectionError) {
      return Exception('No se pudo conectar al servidor. ¿Está corriendo el backend en localhost:8000?');
    }
    final detail = e.response?.data?['detail'] ?? e.message ?? 'Error desconocido';
    return Exception('Error del servidor: $detail');
  }
}

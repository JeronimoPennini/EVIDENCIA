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
            // En hosting gratuito (Render/Railway) el primer pedido puede
            // esperar el "cold start" del contenedor, y la síntesis por IA
            // tarda ~20-30 s: los tiempos muertos son generosos a propósito.
            connectTimeout: const Duration(seconds: 30),
            receiveTimeout: const Duration(seconds: 120),
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
  ///
  /// [priorizarCalidad] pide al backend que busque por niveles de evidencia
  /// (ETS > RS/MA > ECA > observacionales) en lugar de solo por relevancia.
  /// [usarVocabulario] resuelve P, I, C y O contra el vocabulario DeCS/MeSH.
  /// [niveles] permite restringir los niveles a consultar (ets, rs_ma, rct, obs).
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
    bool usarVocabulario = true,
    bool priorizarCalidad = true,
    List<String>? niveles,
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
          'usar_vocabulario_controlado': usarVocabulario,
          'priorizar_calidad': priorizarCalidad,
          if (niveles != null && niveles.isNotEmpty) 'niveles': niveles,
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
        e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      if (ApiConfig.esLocal) {
        return Exception(
          'No se pudo conectar al servidor. ¿Está corriendo el backend en ${ApiConfig.baseUrl}?',
        );
      }
      return Exception(
        'No se pudo hablar con el servidor (${ApiConfig.baseUrl}). '
        'Si el hosting está dormido, reintentá en ~30 s (arranque en frío).',
      );
    }
    final detail = e.response?.data?['detail'] ?? e.message ?? 'Error desconocido';
    return Exception('Error del servidor: $detail');
  }
}

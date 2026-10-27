/// EvidencIA — Providers de búsqueda (Riverpod)
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/article.dart';
import '../services/api_service.dart';

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

// Estado de la búsqueda
class SearchState {
  final bool isLoading;
  final SearchResponse? result;
  final String? error;
  final Set<String> selectedPmids;
  final String? preguntaClinica;

  const SearchState({
    this.isLoading = false,
    this.result,
    this.error,
    this.selectedPmids = const {},
    this.preguntaClinica,
  });

  SearchState copyWith({
    bool? isLoading,
    SearchResponse? result,
    String? error,
    Set<String>? selectedPmids,
    String? preguntaClinica,
  }) =>
      SearchState(
        isLoading: isLoading ?? this.isLoading,
        result: result ?? this.result,
        error: error,
        selectedPmids: selectedPmids ?? this.selectedPmids,
        preguntaClinica: preguntaClinica ?? this.preguntaClinica,
      );
}

class SearchNotifier extends StateNotifier<SearchState> {
  final ApiService _api;

  SearchNotifier(this._api) : super(const SearchState());

  Future<void> buscar({
    required String query,
    int maxResults = 10,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await _api.buscarArticulos(
        query: query,
        maxResults: maxResults,
      );
      state = state.copyWith(
        isLoading: false,
        result: result,
        selectedPmids: {},
        preguntaClinica: query,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> buscarPico({
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
    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await _api.buscarArticulosPico(
        poblacion: poblacion,
        intervencion: intervencion,
        comparacion: comparacion,
        outcome: outcome,
        filtroEstudio: filtroEstudio,
        maxResults: maxResults,
        dateFrom: dateFrom,
        dateTo: dateTo,
        optimizarConIa: optimizarConIa,
      );
      state = state.copyWith(
        isLoading: false,
        result: result,
        selectedPmids: {},
        preguntaClinica: result.preguntaClinica,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void setPreguntaClinica(String pregunta) {
    state = state.copyWith(preguntaClinica: pregunta);
  }

  void toggleSeleccion(String pmid) {
    final set = Set<String>.from(state.selectedPmids);
    if (set.contains(pmid)) {
      set.remove(pmid);
    } else {
      set.add(pmid);
    }
    state = state.copyWith(selectedPmids: set);
  }

  void seleccionarTodos() {
    if (state.result == null) return;
    final allPmids = state.result!.articulos.map((a) => a.pmid).toSet();
    state = state.copyWith(selectedPmids: allPmids);
  }

  void deseleccionarTodos() {
    state = state.copyWith(selectedPmids: {});
  }

  void limpiar() => state = const SearchState();
}

final searchProvider = StateNotifierProvider<SearchNotifier, SearchState>(
  (ref) => SearchNotifier(ref.watch(apiServiceProvider)),
);

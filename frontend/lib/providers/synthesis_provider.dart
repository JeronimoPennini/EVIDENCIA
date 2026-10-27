/// EvidencIA — Provider de síntesis (Riverpod)
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/synthesis_result.dart';
import '../services/api_service.dart';
import 'search_provider.dart';

class SynthesisState {
  final bool isLoading;
  final SynthesisResult? result;
  final String? error;

  const SynthesisState({
    this.isLoading = false,
    this.result,
    this.error,
  });

  SynthesisState copyWith({
    bool? isLoading,
    SynthesisResult? result,
    String? error,
  }) =>
      SynthesisState(
        isLoading: isLoading ?? this.isLoading,
        result: result ?? this.result,
        error: error,
      );
}

class SynthesisNotifier extends StateNotifier<SynthesisState> {
  final ApiService _api;

  SynthesisNotifier(this._api) : super(const SynthesisState());

  Future<void> sintetizar({
    required List<String> pmids,
    required String preguntaClinica,
    String idioma = 'es',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await _api.sintetizarEvidencia(
        pmids: pmids,
        preguntaClinica: preguntaClinica,
        idiomaRespuesta: idioma,
      );
      state = state.copyWith(isLoading: false, result: result);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void limpiar() => state = const SynthesisState();
}

final synthesisProvider = StateNotifierProvider<SynthesisNotifier, SynthesisState>(
  (ref) => SynthesisNotifier(ref.watch(apiServiceProvider)),
);

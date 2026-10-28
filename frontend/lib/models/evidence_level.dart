/// EvidencIA — Helpers de la jerarquía de evidencia.
/// Los códigos vienen del backend (app/services/evidence_service.py):
/// ets > rs_ma > rct > obs > otros.
library;

import 'package:flutter/material.dart';

class EvidenceLevel {
  EvidenceLevel._();

  /// Orden jerárquico por código (1 = máxima calidad).
  static const Map<String, int> orden = {
    'ets': 1,
    'rs_ma': 2,
    'rct': 3,
    'obs': 4,
    'otros': 5,
  };

  /// Etiqueta corta para chips y leyendas.
  static const Map<String, String> etiquetaCorta = {
    'ets': 'ETS / HTA',
    'rs_ma': 'RS / Metaanálisis',
    'rct': 'ECA',
    'obs': 'Observacional',
    'otros': 'Otro diseño',
  };

  /// Descripción extendida para el nivel N (1..5).
  static const Map<int, String> descripcion = {
    1: 'Informe de Evaluación de Tecnologías Sanitarias (HTA): la evidencia de mayor calidad para decisiones de política sanitaria.',
    2: 'Revisión sistemática o metaanálisis: síntesis explícita y reproducible de los estudios disponibles.',
    3: 'Ensayo clínico aleatorizado (ECA): estudio experimental con asignación aleatoria.',
    4: 'Estudio observacional: cohorte o casos y controles, sin asignación aleatoria.',
    5: 'Otro diseño: transversales, series de casos, editoriales, cartas.',
  };

  static int ordenDe(String codigo) => orden[codigo] ?? 5;

  static String etiquetaDe(String codigo, String? delBackend) {
    if (delBackend != null && delBackend.isNotEmpty) return delBackend;
    return etiquetaCorta[codigo] ?? 'Otro diseño';
  }

  static Color colorDe(String codigo, int nivelOrden) {
    final nivel = nivelOrden > 0 ? nivelOrden : (orden[codigo] ?? 5);
    switch (nivel) {
      case 1:
        return const Color(0xFF1B5E20); // verde oscuro
      case 2:
        return const Color(0xFF2E7D32);
      case 3:
        return const Color(0xFF1565C0); // azul
      case 4:
        return const Color(0xFFEF6C00); // naranja
      default:
        return Colors.blueGrey;
    }
  }

  static IconData iconoDe(String codigo) {
    switch (codigo) {
      case 'ets':
        return Icons.policy;
      case 'rs_ma':
        return Icons.library_books;
      case 'rct':
        return Icons.shuffle;
      case 'obs':
        return Icons.remove_red_eye;
      default:
        return Icons.description;
    }
  }

  /// Leyenda de la jerarquía, en orden, con el conteo de artículos devueltos.
  static List<String> get codigosEnOrden => const ['ets', 'rs_ma', 'rct', 'obs', 'otros'];
}

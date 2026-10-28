/// EvidencIA — Panel de vocabulario controlado y jerarquía de evidencia.
/// Muestra cómo la consulta PICO se resolvió contra DeCS/MeSH y cuánta
/// evidencia hay (y se devolvió) en cada nivel de la jerarquía metodológica.
library;

import 'package:flutter/material.dart';
import '../models/article.dart';
import '../models/evidence_level.dart';

class VocabularioYJerarquiaPanel extends StatelessWidget {
  final SearchResponse result;

  const VocabularioYJerarquiaPanel({super.key, required this.result});

  bool get _tieneContenido =>
      result.terminosClinicos.isNotEmpty ||
      result.correccionesVocabulario.isNotEmpty ||
      result.nivelesConsultados.isNotEmpty ||
      result.totalesPorNivel.isNotEmpty;

  @override
  Widget build(BuildContext context) {
    if (!_tieneContenido) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final tieneJerarquia =
        result.nivelesConsultados.isNotEmpty || result.totalesPorNivel.isNotEmpty;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (result.terminosClinicos.isNotEmpty) ...[
              _Titulo(
                icon: Icons.translate,
                texto: 'Vocabulario controlado DeCS / MeSH',
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: result.terminosClinicos.map(_terminoChip).toList(),
              ),
            ],
            if (result.correccionesVocabulario.isNotEmpty) ...[
              const SizedBox(height: 10),
              _bloqueCorrecciones(),
            ],
            if (tieneJerarquia) ...[
              const SizedBox(height: 12),
              _Titulo(
                icon: Icons.workspace_premium,
                texto: 'Jerarquía de evidencia',
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 2),
              Text(
                result.prioridadCalidad
                    ? 'La búsqueda se hizo nivel por nivel y el listado se ordenó por calidad metodológica, no solo por relevancia.'
                    : 'Cada artículo quedó clasificado por su diseño; la búsqueda por niveles está desactivada.',
                style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700),
              ),
              const SizedBox(height: 4),
              ..._niveles(),
            ],
          ],
        ),
      ),
    );
  }

  /// Chip por término PICO resuelto: entrada -> descriptor (MeSH UI).
  Widget _terminoChip(TerminoClinico t) {
    final resuelto = t.descriptor.isNotEmpty;
    final color = resuelto ? Colors.teal : Colors.orange;
    final entrada = t.entrada.length > 24 ? '${t.entrada.substring(0, 24)}…' : t.entrada;
    final destino = resuelto
        ? [
            if (t.decsNombre.isNotEmpty) t.decsNombre,
            t.descriptor,
            if (t.meshUi.isNotEmpty) t.meshUi,
          ].join(' · ')
        : 'No se encontró un descriptor oficial para este término.';

    return Tooltip(
      message: '$entrada -> $destino\nFuente: ${t.fuenteEtiqueta}'
          '${t.clausura.isNotEmpty ? '\nCláusula: ${t.clausura}' : ''}',
      waitDuration: const Duration(milliseconds: 300),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          border: Border.all(color: color.withValues(alpha: 0.40)),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              resuelto ? Icons.verified_outlined : Icons.help_outline,
              size: 13,
              color: color,
            ),
            const SizedBox(width: 5),
            Text(
              entrada,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade800,
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 5),
              child: Icon(Icons.arrow_forward, size: 11, color: Color(0xFF78909C)),
            ),
            Text(
              resuelto ? t.descriptor : 'sin descriptor',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color),
            ),
            if (t.meshUi.isNotEmpty) ...[
              const SizedBox(width: 5),
              Text(t.meshUi, style: TextStyle(fontSize: 9.5, color: Colors.grey.shade600)),
            ],
            const SizedBox(width: 5),
            Text(
              t.fuenteEtiqueta,
              style: const TextStyle(
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF78909C),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Bloque ámbar con los descriptores MeSH inválidos que el backend reparó.
  Widget _bloqueCorrecciones() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        border: Border.all(color: Colors.amber.shade200),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_fix_high, size: 15, color: Colors.amber.shade800),
              const SizedBox(width: 6),
              Text(
                'Descriptores corregidos automáticamente',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.amber.shade900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ...result.correccionesVocabulario.map(
            (c) => Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text(
                '• $c',
                style: TextStyle(fontSize: 11, color: Colors.grey.shade800),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Filas de la jerarquía: niveles consultados primero, luego el resto.
  Iterable<Widget> _niveles() sync* {
    const codigoNivel = {'ets', 'rs_ma', 'rct', 'obs', 'otros'};
    final consultados = result.nivelesConsultados;
    final niveles = <String>[
      ...consultados.where(codigoNivel.contains),
      ...EvidenceLevel.codigosEnOrden.where((c) => !consultados.contains(c)),
    ];

    for (final codigo in niveles) {
      if (!consultados.contains(codigo) &&
          !result.totalesPorNivel.containsKey(codigo) &&
          !result.distribucionDevueltos.containsKey(codigo)) {
        continue;
      }
      yield _FilaNivel(
        codigo: codigo,
        devueltos: result.distribucionDevueltos[codigo] ?? 0,
        total: result.totalesPorNivel[codigo] ?? 0,
      );
    }

    // Códigos que el backend llegara a exponer y no estén en la tabla local.
    for (final extra in consultados.where((c) => !codigoNivel.contains(c))) {
      yield _FilaNivel(
        codigo: extra,
        devueltos: result.distribucionDevueltos[extra] ?? 0,
        total: result.totalesPorNivel[extra] ?? 0,
      );
    }
  }
}

/// Una fila de la jerarquía: etiqueta, barra de cobertura y conteo.
class _FilaNivel extends StatelessWidget {
  final String codigo;
  final int devueltos;
  final int total;

  const _FilaNivel({
    required this.codigo,
    required this.devueltos,
    required this.total,
  });

  @override
  Widget build(BuildContext context) {
    final orden = EvidenceLevel.orden[codigo] ?? 5;
    final color = EvidenceLevel.colorDe(codigo, orden);
    final disponible = total > 0;
    final etiqueta = EvidenceLevel.etiquetaCorta[codigo] ?? codigo;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.5),
      child: Tooltip(
        message: EvidenceLevel.descripcion[orden] ?? '',
        child: Row(
          children: [
            Icon(
              EvidenceLevel.iconoDe(codigo),
              size: 14,
              color: disponible ? color : Colors.grey.shade400,
            ),
            const SizedBox(width: 6),
            SizedBox(
              width: 190,
              child: Text(
                'N$orden · $etiqueta',
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  color: disponible ? color : Colors.grey.shade500,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: total == 0 ? 0 : (devueltos / total).clamp(0.0, 1.0),
                  minHeight: 6,
                  color: color,
                  backgroundColor: color.withValues(alpha: 0.12),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '$devueltos de $total',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
            ),
          ],
        ),
      ),
    );
  }
}

class _Titulo extends StatelessWidget {
  final IconData icon;
  final String texto;
  final Color color;

  const _Titulo({required this.icon, required this.texto, required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 6),
        Text(
          texto,
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}

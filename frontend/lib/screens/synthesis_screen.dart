import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/synthesis_result.dart';
import '../providers/synthesis_provider.dart';
import '../models/evidence_level.dart';

class SynthesisScreen extends ConsumerWidget {
  const SynthesisScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(synthesisProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sintesis de Evidencia'),
        actions: [
          if (state.result != null)
            IconButton(
              icon: const Icon(Icons.copy),
              tooltip: 'Copiar sintesis',
              onPressed: () {
                Clipboard.setData(ClipboardData(text: state.result!.sintesis));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Sintesis copiada al portapapeles')),
                );
              },
            ),
        ],
      ),
      body: _buildBody(context, state),
    );
  }

  Widget _buildBody(BuildContext context, SynthesisState state) {
    if (state.isLoading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 24),
            Text('Analizando evidencia con IA...'),
            SizedBox(height: 8),
            Text(
              'Esto puede tardar entre 10 y 30 segundos',
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ],
        ),
      );
    }

    if (state.error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Theme.of(context).colorScheme.error),
              const SizedBox(height: 16),
              Text(state.error!, textAlign: TextAlign.center),
              const SizedBox(height: 24),
              OutlinedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Volver a la busqueda'),
              ),
            ],
          ),
        ),
      );
    }

    if (state.result == null) {
      return const Center(child: Text('No hay sintesis disponible.'));
    }

    final result = state.result!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (result.advertencia != null)
            Card(
              color: Theme.of(context).colorScheme.tertiaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.warning_amber_outlined, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        result.advertencia!,
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 12),
          Text('Pregunta clinica', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(result.pregunta, style: Theme.of(context).textTheme.bodyMedium),
            ),
          ),
          const SizedBox(height: 16),
          Text('Sintesis generada por IA', style: Theme.of(context).textTheme.labelLarge),
          Text(
            'Modelo: ${result.modeloIa}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
          ),
          const SizedBox(height: 8),
          if (result.distribucionNiveles.isNotEmpty) ...[
            _DistribucionPorNivel(distribucion: result.distribucionNiveles),
            const SizedBox(height: 12),
          ],
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: MarkdownBody(
                data: result.sintesis,
                selectable: true,
                onTapLink: (text, href, title) {
                  if (href != null) {
                    launchUrl(Uri.parse(href), mode: LaunchMode.externalApplication);
                  }
                },
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (result.referencias.isNotEmpty) ...[
            Text('Referencias (${result.referencias.length})',
                style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            ...result.referencias.map(
              (ref) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: _ReferenciaCard(ref: ref),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Resumen de cuántos artículos sintetizados aporta cada nivel de evidencia.
class _DistribucionPorNivel extends StatelessWidget {
  final Map<String, int> distribucion;

  const _DistribucionPorNivel({required this.distribucion});

  @override
  Widget build(BuildContext context) {
    final niveles = [
      for (final codigo in EvidenceLevel.codigosEnOrden)
        if ((distribucion[codigo] ?? 0) > 0) codigo,
    ];
    if (niveles.isEmpty) return const SizedBox.shrink();

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.workspace_premium,
                    size: 16, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 6),
                Text(
                  'Base metodologica de esta sintesis',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final codigo in niveles)
                  Tooltip(
                    message: EvidenceLevel
                        .descripcion[EvidenceLevel.orden[codigo] ?? 5],
                    child: _chipNivel(codigo),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Prioridad: ETS/HTA y revisiones sistematicas por encima de ECA y estudios observacionales.',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chipNivel(String codigo) {
    final orden = EvidenceLevel.orden[codigo] ?? 5;
    final color = EvidenceLevel.colorDe(codigo, orden);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color.withValues(alpha: 0.40)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(EvidenceLevel.iconoDe(codigo), size: 13, color: color),
          const SizedBox(width: 5),
          Text(
            '${EvidenceLevel.etiquetaCorta[codigo]} · ${distribucion[codigo]}',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

/// Tarjeta de referencia con el nivel de evidencia destacado.
class _ReferenciaCard extends StatelessWidget {
  final Referencia ref;

  const _ReferenciaCard({required this.ref});

  @override
  Widget build(BuildContext context) {
    final orden = EvidenceLevel.ordenDe(ref.nivelEvidencia);
    final color = EvidenceLevel.colorDe(ref.nivelEvidencia, orden);
    final etiqueta = EvidenceLevel.etiquetaDe(ref.nivelEvidencia, ref.nivelEtiqueta);

    return Card(
      child: ListTile(
        dense: true,
        leading: Icon(Icons.article_outlined, color: color),
        title: Text(ref.titulo, maxLines: 2, overflow: TextOverflow.ellipsis),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 2),
            Text(
              '${ref.autores} — ${ref.anio ?? "s.f."} · PMID: ${ref.pmid}',
              style: const TextStyle(fontSize: 11.5),
            ),
            if (ref.tiposPublicacion.isNotEmpty)
              Text(
                ref.tiposPublicacion.take(3).join('; '),
                style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600),
              ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.10),
                border: Border.all(color: color.withValues(alpha: 0.45)),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                'N$orden · $etiqueta',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.open_in_new, size: 18),
              tooltip: 'Abrir en PubMed',
              onPressed: () {
                final uri = Uri.parse('https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/');
                launchUrl(uri, mode: LaunchMode.externalApplication);
              },
            ),
          ],
        ),
      ),
    );
  }
}

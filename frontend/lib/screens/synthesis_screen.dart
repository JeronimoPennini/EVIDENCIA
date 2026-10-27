import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/synthesis_provider.dart';

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
                child: Card(
                  child: ListTile(
                    dense: true,
                    leading: const Icon(Icons.article_outlined),
                    title: Text(ref.titulo, maxLines: 2, overflow: TextOverflow.ellipsis),
                    subtitle: Text('${ref.autores} — ${ref.anio ?? "s.f."} · PMID: ${ref.pmid}'),
                    trailing: IconButton(
                      icon: const Icon(Icons.open_in_new, size: 18),
                      tooltip: 'Abrir en PubMed',
                      onPressed: () {
                        final uri = Uri.parse('https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/');
                        launchUrl(uri, mode: LaunchMode.externalApplication);
                      },
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/article.dart';
import '../models/evidence_level.dart';

class ArticleCard extends StatelessWidget {
  final Article article;
  final bool isSelected;
  final VoidCallback onToggle;

  const ArticleCard({
    super.key,
    required this.article,
    required this.isSelected,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isSelected
            ? BorderSide(color: Theme.of(context).colorScheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Checkbox(
                value: isSelected,
                onChanged: (_) => onToggle(),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _NivelBadge(article: article),
                    const SizedBox(height: 6),
                    Text(
                      article.titulo,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${article.autoresCortados} — ${article.anio ?? "s.f."}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    if (article.revista != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        article.revista!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              fontStyle: FontStyle.italic,
                              color: Colors.grey,
                            ),
                      ),
                    ],
                    if (article.abstract != null && article.abstract!.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      _AbstractExpandable(abstract: article.abstract!),
                    ],
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        ActionChip(
                          avatar: const Icon(Icons.open_in_new, size: 13),
                          label: Text('PMID: ${article.pmid}'),
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          labelStyle: const TextStyle(fontSize: 11),
                          tooltip: 'Abrir artículo en PubMed',
                          onPressed: () async {
                            final uri = Uri.parse(article.urlPubmed);
                            if (await canLaunchUrl(uri)) {
                              await launchUrl(uri, mode: LaunchMode.externalApplication);
                            }
                          },
                        ),
                        if (article.doi != null)
                          ActionChip(
                            avatar: const Icon(Icons.link, size: 13),
                            label: Text(
                              'DOI: ${article.doi!.length > 25 ? '${article.doi!.substring(0, 25)}...' : article.doi!}',
                            ),
                            padding: const EdgeInsets.symmetric(horizontal: 4),
                            labelStyle: const TextStyle(fontSize: 11),
                            tooltip: 'Abrir DOI',
                            onPressed: () async {
                              final uri = Uri.parse('https://doi.org/${article.doi!}');
                              if (await canLaunchUrl(uri)) {
                                await launchUrl(uri, mode: LaunchMode.externalApplication);
                              }
                            },
                          ),
                      ],
                    ),
                    if (article.tiposPublicacion.isNotEmpty ||
                        article.meshDescriptores.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      _MetadatosTecnicos(article: article),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Badge con el nivel de evidencia y la señal que justificó la clasificación.
class _NivelBadge extends StatelessWidget {
  final Article article;

  const _NivelBadge({required this.article});

  @override
  Widget build(BuildContext context) {
    final codigo = article.nivelEvidencia;
    final orden = article.nivelOrden > 0 ? article.nivelOrden : EvidenceLevel.ordenDe(codigo);
    final color = EvidenceLevel.colorDe(codigo, orden);
    final etiqueta = EvidenceLevel.etiquetaDe(codigo, article.nivelEtiqueta);
    final tooltip = [
      'Nivel $orden de 5 en la jerarquía de evidencia.',
      EvidenceLevel.descripcion[orden],
      if (article.senalNivel.isNotEmpty) 'Señal detectada: ${article.senalNivel}.',
    ].join(' ');

    return Tooltip(
      message: tooltip,
      waitDuration: const Duration(milliseconds: 300),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.10),
          border: Border.all(color: color.withValues(alpha: 0.45)),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(EvidenceLevel.iconoDe(codigo), size: 13, color: color),
            const SizedBox(width: 5),
            Text(
              '$etiqueta · N$orden',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Línea compacta con tipos de publicación y descriptores MeSH del registro.
class _MetadatosTecnicos extends StatelessWidget {
  final Article article;

  const _MetadatosTecnicos({required this.article});

  @override
  Widget build(BuildContext context) {
    final tipos = article.tiposPublicacion.take(3).join('; ');
    final mesh = article.meshDescriptores.take(4).join('; ');
    final estilo = TextStyle(fontSize: 10.5, color: Colors.grey[600]);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (article.tiposPublicacion.isNotEmpty)
          Text('Tipo de publicación: $tipos', style: estilo),
        if (article.meshDescriptores.isNotEmpty)
          Text(
            'MeSH: $mesh${article.meshDescriptores.length > 4 ? '…' : ''}',
            style: estilo,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
      ],
    );
  }
}

class _AbstractExpandable extends StatefulWidget {
  final String abstract;
  const _AbstractExpandable({required this.abstract});

  @override
  State<_AbstractExpandable> createState() => _AbstractExpandableState();
}

class _AbstractExpandableState extends State<_AbstractExpandable> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final text = widget.abstract;
    final corto = text.length > 200;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _expanded || !corto ? text : '${text.substring(0, 200)}...',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[700]),
        ),
        if (corto)
          GestureDetector(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Text(
              _expanded ? 'Ver menos' : 'Ver mas',
              style: TextStyle(
                color: Theme.of(context).colorScheme.primary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
      ],
    );
  }
}

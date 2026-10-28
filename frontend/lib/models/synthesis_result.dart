class Referencia {
  final String pmid;
  final String titulo;
  final String autores;
  final int? anio;
  final String nivelEvidencia;
  final String nivelEtiqueta;
  final List<String> tiposPublicacion;

  const Referencia({
    required this.pmid,
    required this.titulo,
    required this.autores,
    this.anio,
    this.nivelEvidencia = 'otros',
    this.nivelEtiqueta = 'Otro tipo de estudio',
    this.tiposPublicacion = const [],
  });

  factory Referencia.fromJson(Map<String, dynamic> json) => Referencia(
        pmid: json['pmid'] as String,
        titulo: json['titulo'] as String,
        autores: json['autores'] as String,
        anio: json['año'] as int? ?? json['anio'] as int?,
        nivelEvidencia: json['nivel_evidencia'] as String? ?? 'otros',
        nivelEtiqueta:
            json['nivel_etiqueta'] as String? ?? 'Otro tipo de estudio',
        tiposPublicacion: (json['tipos_publicacion'] as List<dynamic>? ?? [])
            .map((e) => e.toString())
            .where((e) => e.isNotEmpty)
            .toList(),
      );
}

class SynthesisResult {
  final String pregunta;
  final String sintesis;
  final List<Referencia> referencias;
  final String modeloIa;
  final String? advertencia;
  final Map<String, int> distribucionNiveles;

  const SynthesisResult({
    required this.pregunta,
    required this.sintesis,
    required this.referencias,
    required this.modeloIa,
    this.advertencia,
    this.distribucionNiveles = const {},
  });

  factory SynthesisResult.fromJson(Map<String, dynamic> json) => SynthesisResult(
        pregunta: json['pregunta'] as String,
        sintesis: json['sintesis'] as String,
        referencias: (json['referencias'] as List<dynamic>)
            .map((r) => Referencia.fromJson(r as Map<String, dynamic>))
            .toList(),
        modeloIa: json['modelo_ia'] as String,
        advertencia: json['advertencia'] as String?,
        distribucionNiveles: <String, int>{
          for (final e
              in (json['distribucion_niveles'] as Map<String, dynamic>? ?? {})
                  .entries)
            e.key: (e.value as num?)?.toInt() ?? 0,
        },
      );
}

class Referencia {
  final String pmid;
  final String titulo;
  final String autores;
  final int? anio;

  const Referencia({
    required this.pmid,
    required this.titulo,
    required this.autores,
    this.anio,
  });

  factory Referencia.fromJson(Map<String, dynamic> json) => Referencia(
        pmid: json['pmid'] as String,
        titulo: json['titulo'] as String,
        autores: json['autores'] as String,
        anio: json['año'] as int? ?? json['anio'] as int?,
      );
}

class SynthesisResult {
  final String pregunta;
  final String sintesis;
  final List<Referencia> referencias;
  final String modeloIa;
  final String? advertencia;

  const SynthesisResult({
    required this.pregunta,
    required this.sintesis,
    required this.referencias,
    required this.modeloIa,
    this.advertencia,
  });

  factory SynthesisResult.fromJson(Map<String, dynamic> json) => SynthesisResult(
        pregunta: json['pregunta'] as String,
        sintesis: json['sintesis'] as String,
        referencias: (json['referencias'] as List<dynamic>)
            .map((r) => Referencia.fromJson(r as Map<String, dynamic>))
            .toList(),
        modeloIa: json['modelo_ia'] as String,
        advertencia: json['advertencia'] as String?,
      );
}
